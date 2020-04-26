from btcp_socket import BTCPSocket
from lossy_layer import LossyLayer
from constants import *

# bTCP client socket
# A client application makes use of the services provided by bTCP by calling connect, send, disconnect, and close
class BTCPClientSocket(BTCPSocket):
    def __init__(self, window, timeout):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT)

    # Called by the lossy layer from another thread whenever a segment arrives. 
    def lossy_layer_input(self, segment, address):
        print("YAY")
        pass

    # Perform a three-way handshake to establish a connection
    def connect(self, ip, port):
        # build a SYN message
        syn_segment = self.make_segment(None, SYN)
        # send it
        self.send(syn_segment)
        # wait for response (SYN+ACK)
        # send ACK
    
    # Send data originating from the application in a reliable way to the server
    def send(self, segment):
        self._lossy_layer.send_segment(segment)

    # Perform a handshake to terminate a connection
    def disconnect(self):
        pass

    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()
