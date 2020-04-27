from btcp_socket import BTCPSocket
from lossy_layer import LossyLayer
from constants import *

# bTCP client socket
# A client application makes use of the services provided by bTCP by calling connect, send, disconnect, and close
class BTCPClientSocket(BTCPSocket):
    def __init__(self, window, timeout):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT)
        self.syn_sent = False


    # Called by the lossy layer from another thread whenever a segment arrives. 
    def lossy_layer_input(self, segment, address):

        # Unpack the segment
        message = self.unpack_segment(segment)

        # Put it in the buffer
        self.buffer.append(message)

    # Perform a three-way handshake to establish a connection
    def connect(self):
        while not self.con_est:
            if not self.syn_sent:

                # Send SYN
                segment = self.make_segment(None, SYN)
                self.syn_sent = True
                print("Client sent SYN")
                self.send(segment)

            elif self.buffer:

                # Get message
                message = self.buffer.pop(0)

                # Look at the flag
                if message['flag'] == SYNACK:

                    # Send ACK
                    segment = self.make_segment(b'hello', ACK)
                    self.con_est = True
                    print("Client sent ACK")
                    self.send(segment)

    # Send data originating from the application in a reliable way to the server
    def send(self, segment):
        self._lossy_layer.send_segment(segment)

    # Perform a handshake to terminate a connection
    def disconnect(self):
        pass

    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()
