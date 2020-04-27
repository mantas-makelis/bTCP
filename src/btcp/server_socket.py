import socket
from btcp.lossy_layer import LossyLayer
from btcp.btcp_socket import BTCPSocket
from btcp.constants import *
import random


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

        if not self.con_est:
            self.accept()

        # if not self.con_est and message['flag'] == SYN:
        #     self.accept()
        # elif message['flag'] == FIN:
        #     self.disconnect()
        # elif message['flag'] == ACK:
            # if FINACK was sent:
                # close connection
            # acknowledge / keep track of ack_nr, win_size
    
    # Wait for the client to initiate a three-way handshake
    def accept(self):
        while not self.con_est:
            if self.buffer:

                # Get message
                message = self.buffer.pop(0)

                # Inspect flag
                if message['flag'] == SYN:

                    # Generate random seq_nr
                    self._seq_nr = random.randint(0, 2 ** 16)

                    # Set ack number
                    self._ack_nr = message['seq_nr']+1

                    # Send SYNACK
                    segment = self.make_segment(seq_nr=self._seq_nr,
                                                ack_nr=self._ack_nr,
                                                flag=SYNACK)
                    self.con_est = True
                    print("Server sent SYNACK")
                    self.send(segment)

    # Send any incoming data to the application layer
    def recv(self):
        while self.buffer:
            # Get message
                message = self.buffer.pop(0)

                # Inspect flag
                if message['flag'] == FIN:
                    self.disconnect(message)

    # Send data originating from the application in a reliable way to the client
    def send(self, segment):
        self._lossy_layer.send_segment(segment)

    def disconnect(self, message):

        # Set ack number
        self._ack_nr = message['seq_nr']+1

        # Send SYNACK
        segment = self.make_segment(seq_nr=self._seq_nr,
                                    ack_nr=self._ack_nr,
                                    flag=FINACK)
        print("Server sent FINACK")
        self.send(segment)


    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()
