from typing import Optional
from btcp.btcp_socket import BTCPSocket
from btcp.classes import BadState, WrongFlag, Segment
from btcp.constants import SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT, FIN_TIMEOUT, TWO_BYTES
from btcp.enums import State, Flag
from btcp.lossy_layer import LossyLayer


class BTCPServerSocket(BTCPSocket):
    """ The bTCP server socket
    A server application makes use of the services provided by bTCP by calling accept, recv, and close
    """

    def __init__(self, window: int, timeout: int, show_prints: bool = False):
        super().__init__(window, timeout, 'Server', show_prints)
        self._lossy_layer = LossyLayer(self, SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT)
        self.data_sequent = 0

    def lossy_layer_input(self, segment: bytes, address) -> None:
        """ Called by the lossy layer from another thread whenever a segment arrives """
        self.buffer.put((address, segment), block=True, timeout=25)

    def accept(self) -> None:
        """ Wait for the client to initiate a three-way handshake """
        if self.state is not State.OPEN:
            raise BadState('Only non-connected server can accept a connection')
        conn_attempt = False
        # Wait for connection attempt while the state is unchanged
        while True:
            # Handle the incoming traffic
            segment = self.handle_flow(expected=[Flag.SYN, Flag.ACK, Flag.NONE])
            # Send SYNACK if the SYN request was received
            if segment and segment.flag is Flag.SYN:
                conn_attempt = True
                self.send_synack(segment)
            # Establish the connection if the acknowledgement was received
            elif segment and segment.flag is Flag.ACK:
                if self.valid_ack(segment):
                    self.set_seq_and_state(segment)
                    break
            # In case ACK was lost but the next segment of data was received
            elif conn_attempt and segment and segment.flag is Flag.NONE:
                self.set_seq_and_state(segment)
                self.acknowledge_post(segment, Flag.ACK)
                self.data_buffer[segment.seq_nr] = segment
                break
        # Set the expected next data sequent using acknowledgement number
        self.data_sequent = self.ack_nr
        if self.show_prints:
            print(f'-- Server established connection --', flush=True)

    def recv(self) -> Optional[bytes]:
        """ Send any incoming data to the application layer """
        if self.state is not State.CONN_EST:
            raise BadState('Receive is only allowed if a connection is established')
        # Check if there is next data in the buffer received prior
        if self.data_sequent in self.data_buffer:
            self.return_data()
        # Wait until a segment is received
        while True:
            segment = self.handle_flow(expected=[Flag.NONE, Flag.FIN])
            # If requested - accept the disconnect request
            if not segment:
                continue
            if segment.flag is Flag.FIN:
                return self._accept_disconnect(segment)
            self.acknowledge_post(segment, Flag.ACK)
            # If the segment is out of order - buffer it and continue
            if self.data_sequent != segment.seq_nr:
                # Check if it was not yet buffered and not an already received segment
                if segment.seq_nr not in self.data_buffer and segment.seq_nr > self.data_sequent:
                    self.data_buffer[segment.seq_nr] = segment
                continue
            self.data_sequent = self.safe_incr(self.data_sequent)
            return segment.data[:segment.dlen]

    def _accept_disconnect(self, segment: Segment) -> None:
        """ Internal function which handles the disconnect attempt """
        if self.state is not State.CONN_EST:
            raise BadState('Only connected server can accept disconnect request')
        if segment.flag is not Flag.FIN:
            raise WrongFlag('The received message\'s flag must be Flag.FIN')
        # Send the initial FINACK
        self.acknowledge_post(segment, Flag.FINACK)
        # Initialize timer
        timer = 0
        start_time = self.time()
        # Attempt to disconnect until the state is changed or timer is exceeded
        while True:
            segment = self.handle_flow(expected=[Flag.FIN, Flag.ACK])
            # Send FINACK if repeated FIN request was received or if it was not yet sent
            if segment and segment.flag is Flag.FIN:
                self.acknowledge_post(segment, Flag.FINACK)
                start_time = self.time()
            # Terminate the connection if the acknowledgement was received
            elif segment and segment.flag is Flag.ACK and self.valid_ack(segment) or timer > FIN_TIMEOUT:
                self.state = State.OPEN
                if self.show_prints:
                    print(f'-- Server terminated connection --', flush=True)
                break
            timer = self.time() - start_time

    def send_synack(self, segment: Segment) -> None:
        """ Sends a SYNACK and sets the new state """
        self.acknowledge_post(segment, Flag.SYNACK)
        self.ack_nr = self.safe_incr(segment.seq_nr)

    def set_seq_and_state(self, segment: Segment) -> None:
        """ Increases the sequence number by one and sets the state to connection established """
        self.seq_nr = self.safe_incr(self.seq_nr)
        self.state = State.CONN_EST
        self.connectedAddress = segment.address

    def return_data(self) -> list:
        """ Returns the next segments data without padding bytes """
        segment = self.data_buffer.pop(self.data_sequent)
        self.data_sequent = self.safe_incr(self.data_sequent)
        return segment.data[:segment.dlen]

    def close(self) -> None:
        """ Clean up any state """
        self._lossy_layer.destroy()
