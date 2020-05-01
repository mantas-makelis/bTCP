from btcp.btcp_socket import BTCPSocket
from btcp.lossy_layer import LossyLayer
from btcp.constants import SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT
from btcp.enums import State, Flag, Key
import time

class BTCPServerSocket(BTCPSocket):
    """ The bTCP server socket
    A server application makes use of the services provided by bTCP by calling accept, recv, and close
    """

    def __init__(self, window, timeout):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT)


    def lossy_layer_input(self, segment, address):
        """ Called by the lossy layer from another thread whenever a segment arrives """
        self.buffer.put(segment, block=True, timeout=100)

    
    def idle(self):
        self._handle_flow()
        if Key.FIN in self.drop:
            self._disconnect()
    
    
    def accept(self):
        """ Wait for the client to initiate a three-way handshake """
        # Only non-connected server can accept a connection
        if self.state is not State.OPEN:
            return
        # Move state to pending connection
        self.state = State.CONN_PEND
        # Wait for connection attempt
        while State.CONN_PEND:
            # Make a break and handle incoming segments
            self._handle_flow()
            # Block for receiving SYN request
            if Key.SYN in self.drop:
                message = self.drop.pop(Key.SYN)
                self.recv_win = message['win']
                ack_nr = self.safe_incr(message['seq_nr'])
                segment = self.pack_segment(ack_nr=ack_nr, flag=Flag.SYNACK)
                self._lossy_layer.send_segment(segment)
                print(f'Server sent SYNACK (seq_nr: {self.seq_nr}, ack_nr: {ack_nr})')
            # Block for receiving ACK
            if Key.CONN_ACK in self.drop:
                message = self.drop.pop(Key.CONN_ACK)
                next_seq = self.safe_incr(self.seq_nr)
                if next_seq == message['ack_nr']:
                    self.recv_win = message['win']
                    self.seq_nr = next_seq
                    self.state = State.CONN_EST
                    print(f'Server established connection (seq_nr: {self.seq_nr})')
            # In case ACK was lost but the next segment of data was received
            if Key.DATA in self.drop:
                self.state = State.CONN_EST
                break
                

    def recv(self) -> bytes:
        """ Send any incoming data to the application layer """
        # We can only receive if a connection has been established
        if self.state is not State.CONN_EST:
            return
        # Setting the state
        self.state = State.RECV
        # Initialising arrays
        data = []
        acked = []
        # The server receives while the client does not disconnect
        while Key.FIN not in self.drop:
            self._handle_flow()
            # Block for handling received data
            if Key.DATA in self.drop:
                message = self.drop.pop(Key.DATA)
                ack_nr = self.safe_incr(message['seq_nr'], message['dlen'])
                print(f'Server received segment {message["seq_nr"]}')
                # Only save the data if it was not yet acknowledged
                if ack_nr not in acked:
                    # Append the data without the padding bytes
                    data.append((message['data'][:message['dlen']], ack_nr))
                    acked.append(ack_nr)
                # Acknowledge the received segment
                segment = self.pack_segment(ack_nr=ack_nr, flag=Flag.ACK)
                self._lossy_layer.send_segment(segment)
                print(f'Server sent ACK {ack_nr}')
        # Accept the disconnect request
        self.state = State.CONN_EST
        self._disconnect()
        # Sort the data according to the ACK numbers
        data.sort(key=lambda tup: tup[1])
        # Merge the data bytes into a single object
        return b''.join([d for (d, _) in data])


    def close(self):
        """ Clean up any state """
        self._lossy_layer.destroy()

    
    def _disconnect(self):
        """ Internal function which handles the disconnect attempt """
        # Only connected server can begin disconnect request and if the FIN segment was received
        if self.state in [State.OPEN, State.CONN_PEND] or not Key.FIN in self.drop:
            return
        self.state = State.DISC_PEND
        timer = start_time = 0
        # Server responds with FINACK
        while self.state is State.DISC_PEND:
            # Make a break and handle incoming segments
            self._handle_flow()
            if Key.FIN in self.drop:
                message = self.drop.pop(Key.FIN)
                segment = self.pack_segment(ack_nr=self.safe_incr(message['seq_nr']) , flag=Flag.FINACK)
                self._lossy_layer.send_segment(segment)
                timer = 0
                start_time = self.time()
                print('Server sent FINACK')
            # Block for receiving ACK
            elif Key.DISC_ACK in self.drop:
                _ = self.drop.pop(Key.DISC_ACK)
                self.state = State.OPEN
                print('Server terminated connection')
            elif timer > 1000:
                break
            else:
                timer = self.time() - start_time
