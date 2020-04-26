import socket
from lossy_layer import LossyLayer
from btcp_socket import BTCPSocket
from constants import *


# The bTCP server socket
# A server application makes use of the services provided by bTCP by calling accept, recv, and close
class BTCPServerSocket(BTCPSocket):
    def __init__(self, window, timeout):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, SERVER_IP, SERVER_PORT, CLIENT_IP, CLIENT_PORT)
        self.conn_req = False
        self.data = None

    # Called by the lossy layer from another thread whenever a segment arrives
    def lossy_layer_input(self, segment, address):
        # If segment SYN:
            # do accept()
        self.conn_req = True

        # Disect the segment
        # Compute the checksum
        # Compare the checksum
        # Receive (recv)
        pass

    # Wait for the client to initiate a three-way handshake
    def accept(self):
        if not self.conn_req:
            return

        # SYN+ACK
        synack_segment = self.make_segment(None, SYNACK)
        
        # Send
        self.send(synack_segment)
        self.conn_req = False
        

    # Send any incoming data to the application layer
    def recv(self):
        pass

    # Send data originating from the application in a reliable way to the client
    def send(self, segment):
        self._lossy_layer.send_segment(segment)

    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()
