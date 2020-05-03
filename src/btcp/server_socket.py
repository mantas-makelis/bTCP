from typing import Optional
from btcp.btcp_socket import BTCPSocket
from btcp.constants import SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT, FIN_TIMEOUT, TWO_BYTES
from btcp.enums import State, Flag
from btcp.lossy_layer import LossyLayer


class BTCPServerSocket(BTCPSocket):
    """ The bTCP server socket
    A server application makes use of the services provided by bTCP by calling accept, recv, and close
    """

    def __init__(self, window: int, timeout: int, show_prints: bool):
        super().__init__(window, timeout, 'Server', show_prints)
        self._lossy_layer = LossyLayer(self, SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT)
        self.temp = {}
        self.wraparound = 0

    def lossy_layer_input(self, segment: bytes, address) -> None:
        """ Called by the lossy layer from another thread whenever a segment arrives """
        self.buffer.put(segment, block=True, timeout=50)

    def accept(self) -> None:
        """ Wait for the client to initiate a three-way handshake """
        # Only non-connected server can accept a connection
        if self.state is not State.OPEN:
            return
        # Wait for connection attempt while the state is unchanged
        while State.OPEN:
            # Handle the incoming traffic
            message = self.handle_flow(expected=[Flag.SYN, Flag.ACK, Flag.NONE])
            # Send SYNACK if the SYN request was received
            if message and message['flag'] is Flag.SYN:
                self.acknowledge_post(message, Flag.SYNACK)
                self.ack_nr = self.safe_incr(message['seq_nr'])
            # Establish the connection if the acknowledgement was received
            elif message and message['flag'] is Flag.ACK:
                if self.valid_ack(message):
                    self.seq_nr = self.safe_incr(self.seq_nr)
                    self.state = State.CONN_EST
                    if self.show_prints:
                        print(f'-- Server established connection --', flush=True)
            # In case ACK was lost but the next segment of data was received
            elif message and message['flag'] is Flag.NONE and message['dlen'] > 0:
                self.state = State.CONN_EST
                self.temp['ACK-lost'] = message
                break

    def recv(self) -> Optional[bytes]:
        """ Send any incoming data to the application layer """
        # We can only receive if a connection has been established
        if self.state is not State.CONN_EST:
            return None
        # Initialize local variables
        data = []
        acked = []
        if 'ACK-lost' in self.temp:
            self.send_recv_ack(self.temp['ACK-lost'], acked, data)
        # The server receives while the client does not disconnect
        while self.state is State.CONN_EST:
            message = self.handle_flow(expected=[Flag.NONE, Flag.FIN])
            if not message:
                continue
            if message['flag'] is Flag.NONE and message['dlen'] > 0:
                self.send_recv_ack(message, acked, data)
            # Accept the disconnect request
            elif message['flag'] is Flag.FIN:
                self.accept_disconnect(message)
            # Acknowledge the probe checking windows size
            else:
                self.acknowledge_post(message, Flag.ACK)
        # Sort the data according to the ACK numbers
        data.sort(key=lambda tup: tup[1])
        # Merge the data bytes into a single object
        return b''.join([d for (d, _) in data])

    def send_recv_ack(self, message: dict, acked: list, data: list) -> None:
        self.acknowledge_post(message, Flag.ACK)
        segment_id = self.calculate_id(message['seq_nr'], message['dlen'])
        ack_nr = self.safe_incr(message['seq_nr'], message['dlen'])
        # Only save the data if it was not yet acknowledged
        if ack_nr not in acked:
            # Append the data without the padding bytes and ACK number tuple
            data.append((message['data'][:message['dlen']], segment_id))
            acked.append(ack_nr)

    def calculate_id(self, number: int, addition: int = 1) -> int:
        """ Calculates the id for the segment """
        summed = number + addition
        if summed < TWO_BYTES:
            return summed + (self.wraparound * TWO_BYTES)
        else:
            self.wraparound += 1
            return summed % TWO_BYTES + (self.wraparound * TWO_BYTES)

    def accept_disconnect(self, message: dict) -> None:
        """ Internal function which handles the disconnect attempt """
        # Only connected server can begin disconnect request and if the FIN segment was received
        if self.state is not State.CONN_EST:
            return
        # Send the initial FINACK
        self.acknowledge_post(message, Flag.FINACK)
        # Initialize timer
        timer = 0
        start_time = self.time()
        # Attempt to disconnect until the state is changed or timer is exceeded
        while self.state is State.CONN_EST:
            message = self.handle_flow(expected=[Flag.FIN, Flag.ACK])
            # Send FINACK if repeated FIN request was received or if it was not yet sent
            if message and message['flag'] is Flag.FIN:
                self.acknowledge_post(message, Flag.FINACK)
                start_time = self.time()
            # Terminate the connection if the acknowledgement was received
            elif message and message['flag'] is Flag.ACK and self.valid_ack(message) or timer > FIN_TIMEOUT:
                self.state = State.OPEN
                if self.show_prints:
                    print(f'-- Server terminated connection --', flush=True)
            timer = self.time() - start_time

    def close(self) -> None:
        """ Clean up any state """
        self._lossy_layer.destroy()