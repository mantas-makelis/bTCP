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
        self.data = None

    # Called by the lossy layer from another thread whenever a segment arrives
    def lossy_layer_input(self, segment, address):

        # Unpack the segment
        message = self.unpack_segment(segment)
        self.buffer.append(message)

        # Look at the flag
        if message['flag'] == SYN:
            self.accept()
            self.conn_req = True
        else:
            self.recv()
        # Receive (recv)

    # Wait for the client to initiate a three-way handshake
    def accept(self):
        while not self.con_est:
            if self.buffer:

                # Get message
                message = self.buffer.pop(0)

                # Look at the flag
                if message['flag'] == SYN:

                    # Send SYNACK
                    segment = self.make_segment(None, SYNACK)
                    self.con_est = True
                    print("Server sent SYNACK")
                    self.send(segment)

    # Send any incoming data to the application layer
    def recv(self):

        pass

    # Send data originating from the application in a reliable way to the client
    def send(self, segment):
        self._lossy_layer.send_segment(segment)

    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()
