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

    def lossy_layer_input(self, segment: bytes, address) -> None:
        """ Called by the lossy layer from another thread whenever a segment arrives """
        self.buffer.put((address, segment), block=True, timeout=25)

    def accept(self) -> None:
        """ Waits for the client to initiate a three-way handshake """
        if self.state is not State.OPEN:
            raise BadState('Only non-connected server can accept a connection')
        conn_attempt = False
        while True:
            segment = self.handle_flow(expected=[Flag.SYN, Flag.ACK, Flag.NONE])
            if segment and segment.flag is Flag.SYN:
                conn_attempt = True
                self._send_synack(segment)
            elif conn_attempt and segment and segment.flag is Flag.ACK:
                if self.valid_ack(segment):
                    self._set_seq_and_state(segment)
                    break
            # In case ACK was lost but the next segment of data was received
            elif conn_attempt and segment and segment.flag is Flag.NONE:
                self._set_seq_and_state(segment)
                self.acknowledge_post(segment, Flag.ACK)
                self.data_buffer[segment.seq_nr] = segment
                break
        if self.show_prints:
            print(f'-- Server established connection --', flush=True)

    def recv(self) -> Optional[bytes]:
        """ Receives the data from the client and send it to the application layer """
        if self.state is not State.CONN_EST:
            raise BadState('Receive is only allowed if a connection is established')
        if self.recv_seq in self.data_buffer:
            return self._return_data_from_buffer()
        while True:
            segment = self.handle_flow(expected=[Flag.NONE, Flag.FIN])
            if not segment:
                continue
            if segment.flag is Flag.FIN:
                return self._accept_disconnect(segment)
            self.acknowledge_post(segment, Flag.ACK)
            if self.recv_seq != segment.seq_nr:
                if segment.seq_nr not in self.data_buffer and segment.seq_nr > self.recv_seq:
                    self.data_buffer[segment.seq_nr] = segment
                continue
            self.recv_seq = self.safe_incr(self.recv_seq)
            return segment.data[:segment.dlen]
    
    def close(self) -> None:
        """ Clean up any state """
        self._lossy_layer.destroy()

    def _accept_disconnect(self, segment: Segment) -> None:
        """ Internal function which handles the disconnect request from the client """
        if self.state is not State.CONN_EST:
            raise BadState('Only connected server can accept disconnect request')
        if segment.flag is not Flag.FIN:
            raise WrongFlag('The received message\'s flag must be Flag.FIN')
        self.acknowledge_post(segment, Flag.FINACK)
        timer = 0
        start_time = self.time()
        while True:
            segment = self.handle_flow(expected=[Flag.FIN, Flag.ACK])
            if segment and segment.flag is Flag.FIN:
                self.acknowledge_post(segment, Flag.FINACK)
                start_time = self.time()
            elif segment and segment.flag is Flag.ACK and self.valid_ack(segment) or timer > FIN_TIMEOUT:
                self.state = State.OPEN
                if self.show_prints:
                    print(f'-- Server terminated connection --', flush=True)
                break
            timer = self.time() - start_time

    def _send_synack(self, segment: Segment) -> None:
        """ Sends a SYNACK and updates the acknowledgement number """
        self.acknowledge_post(segment, Flag.SYNACK)
        self.recv_seq = self.safe_incr(segment.seq_nr)

    def _set_seq_and_state(self, segment: Segment) -> None:
        """ Increases the sequence number by one and sets the state to connection established """
        self.seq_nr = self.safe_incr(self.seq_nr)
        self.state = State.CONN_EST
        self.connectedAddress = segment.address

    def _return_data_from_buffer(self) -> list:
        """ Removes the expected segment from the buffer and returns the data without padding bytes """
        segment = self.data_buffer.pop(self.recv_seq)
        self.recv_seq = self.safe_incr(self.recv_seq)
        return segment.data[:segment.dlen]
