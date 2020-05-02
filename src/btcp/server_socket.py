from typing import Optional
from btcp.btcp_socket import BTCPSocket
from btcp.constants import SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT
from btcp.enums import State, Flag, Key
from btcp.lossy_layer import LossyLayer


class BTCPServerSocket(BTCPSocket):
    """ The bTCP server socket
    A server application makes use of the services provided by bTCP by calling accept, recv, and close
    """

    def __init__(self, window, timeout):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT)

    def lossy_layer_input(self, segment, address):
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
                self.recv_win = message['win']
                ack_nr = self.safe_incr(message['seq_nr'])
                segment = self.pack_segment(ack_nr=ack_nr, flag=Flag.SYNACK)
                print(f'[seq: {self.seq_nr}; ack: {ack_nr}] Server sent SYNACK', flush=True)
                self._lossy_layer.send_segment(segment)
            # Establish the connection if the acknowledgement was received
            elif message and message['flag'] is Flag.ACK:
                if self.valid_ack(message):
                    self.recv_win = message['win']
                    self.seq_nr = self.safe_incr(self.seq_nr)
                    self.state = State.CONN_EST
                    print(f'-- Server established connection --', flush=True)
            # In case ACK was lost but the next segment of data was received
            elif message and message['flag'] is Flag.NONE and message['dlen'] > 0:
                self.state = State.CONN_EST
                # TODO: save the message for handling in recv()
                break

    def recv(self) -> Optional[bytes]:
        """ Send any incoming data to the application layer """
        # We can only receive if a connection has been established
        if self.state is not State.CONN_EST:
            return None
        # Initialize local variables
        data = []
        acked = []
        fin_received = False
        # The server receives while the client does not disconnect
        while not fin_received:
            message = self.handle_flow(expected=[Flag.NONE, Flag.FIN])
            if not message:
                continue
            if message['flag'] is Flag.NONE and message['dlen'] > 0:
                ack_nr = self.safe_incr(message['seq_nr'], message['dlen'])
                # Only save the data if it was not yet acknowledged
                if ack_nr not in acked:
                    # Append the data without the padding bytes and ACK number tuple
                    data.append((message['data'][:message['dlen']], ack_nr))
                    acked.append(ack_nr)
                # Acknowledge the received segment
                segment = self.pack_segment(ack_nr=ack_nr, flag=Flag.ACK)
                print(f'[seq: -; ack: {ack_nr}] Server sent ACK', flush=True)
                self._lossy_layer.send_segment(segment)
            elif message['flag'] is Flag.FIN:
                fin_received = True
        # Accept the disconnect request
        self.accept_disconnect(message)
        # Sort the data according to the ACK numbers
        data.sort(key=lambda tup: tup[1])
        # Merge the data bytes into a single object
        return b''.join([d for (d, _) in data])

    def close(self) -> None:
        """ Clean up any state """
        self._lossy_layer.destroy()

    def accept_disconnect(self, message) -> None:
        """ Internal function which handles the disconnect attempt """
        # Only connected server can begin disconnect request and if the FIN segment was received
        if self.state is not State.CONN_EST:
            return
        # Send the initial FINACK
        self.send_finack(message)
        # Initialize timer
        timer = 0
        start_time = self.time()
        # Attempt to disconnect until the state is changed or timer is exceeded
        while self.state is State.CONN_EST:
            message = self.handle_flow(expected=[Flag.FIN, Flag.ACK])
            # Send FINACK if repeated FIN request was received or if it was not yet sent
            if message and message['flag'] is Flag.FIN:
                self.send_finack(message)
                start_time = self.time()
            # Terminate the connection if the acknowledgement was received
            elif message and message['flag'] is Flag.ACK or timer > 1000:
                self.state = State.OPEN
                print(f'-- Server terminated connection --', flush=True)
            timer = self.time() - start_time

    def send_finack(self, message):
        ack_nr = self.safe_incr(message['seq_nr'])
        segment = self.pack_segment(ack_nr=ack_nr, flag=Flag.FINACK)
        print(f'[seq: -; ack: {ack_nr}] Server sent FINACK', flush=True)
        self._lossy_layer.send_segment(segment)
