from btcp.btcp_socket import BTCPSocket
from btcp.lossy_layer import LossyLayer
from btcp.constants import *
from btcp.enums import State, Flag, Key


class BTCPClientSocket(BTCPSocket):
    """ bTCP client socket
    A client application makes use of the services provided by bTCP by calling connect, send, disconnect, and close 
    """

    def __init__(self, window, timeout):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT)


    def lossy_layer_input(self, segment, address):
        """ Called by the lossy layer from another thread whenever a segment arrives. """
        if not self.buffer.full():
            self.buffer.put(segment, block=False)
        

    def connect(self):
        """ Perform a three-way handshake to establish a connection """
        # Only non-connected client can make a connection
        if self.state is not State.OPEN:
            return
        # Change state to a pending connection
        self.state = State.CONN_PEND
        # Initialize local variables
        syn_count = timer = start_timer = 0
        # Attempt to connect while the state is unchanged or maximum attempts are exeeded
        while self.state is State.CONN_PEND and syn_count < MAX_ATTEMPTS:
            # Make a break and handle incoming segments
            self.handle_flow()
            # Block for sending SYN request
            if syn_count == 0 or timer > self._timeout:
                self.seq_nr = self.start_random_sequence()
                segment = self.pack_segment(flag=Flag.SYN)
                self._lossy_layer.send_segment(segment)
                syn_count += 1
                print('Client sent SYN')
                timer = 0
                start_timer = self.time()
            # Block for receiving SYNACK
            elif Key.SYNACK in self.drop:
                message = self.drop.pop(Key.SYNACK)
                self.ack_nr = message['seq_nr'] + 1
                segment = self.pack_segment(flag=Flag.ACK)
                self._lossy_layer.send_segment(segment)
                self.state = State.CONN_EST
                print('Client sent ACK and established connection')
            # Increase the timer if nothing happens
            else:
                timer = self.time() - start_timer
        # Reset the state if the connection failed
        if self.state is not State.CONN_EST and syn_count >= MAX_ATTEMPTS:
            self.state = State.OPEN


    def send(self, segment):
        """ Send data originating from the application in a reliable way to the server """
        pass


    def disconnect(self):
        """ Perform a handshake to terminate a connection """
        # Only connected client can disconnect
        if self.state is not State.CONN_EST:
            return
        # Change state to a pending disconnect request
        self.state = State.DISC_PEND
        # Initialize local variables
        fin_count = timer = start_timer = 0
        # Attempt to disconnect while the state is unchanged or maximum attempts are exeeded
        while self.state is State.CONN_EST and fin_count < MAX_ATTEMPTS:
            # Make a break and handle incoming segments
            self.handle_flow()
            # Block for sending FIN request
            if not self.fin_sent or timer > self._timeout:
                self.seq_nr += 1
                segment = self.make_segment(flag=Flag.FIN)
                self._lossy_layer.send_segment(segment)
                fin_count += 1
                print("Client sent FIN")
                timer = 0
                start_timer = self.time()
            # Block for receiving FINACK
            elif Key.FINACK in self.drop:
                message = self.drop.pop(Key.FINACK)
                self.ack_nr = message['seq_nr'] + 1
                segment = self.make_segment(flag=Flag.ACK)
                self._lossy_layer.send_segment(segment)
                self.state = State.OPEN
                print('Client sent ACK and terminated connection')
            # Increase the timer if nothing happens
            else:
                timer = self.time() - start_timer
        # Reset the state if the disconnect attempt failed
        if self.state is not State.OPEN and fin_count >= MAX_ATTEMPTS:
            self.state = State.CONN_EST


    def close(self):
        """ Clean up any state """
        self._lossy_layer.destroy()
