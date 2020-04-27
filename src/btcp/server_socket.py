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
        self.synack_sent = False
        self.finack_sent = False

    # Called by the lossy layer from another thread whenever a segment arrives
    def lossy_layer_input(self, segment, address):

        # Unpack the segment
        message = self.unpack_segment(segment)
        self.buffer.append(message)

        if not self.con_est and message['flag'] == SYN:
            print("Server received SYN")
            self.accept()
        elif message['flag'] == FIN:
            print("Server received FIN")
            self.disconnect()
        elif message['flag'] == ACK:
            if self.synack_sent:
                self.synack_sent = False
                self.con_est = True
                print("Server received ACK, connection established")
            elif self.finack_sent:
                self.finack_sent = False
                self.con_est = False
                print("Server received ACK, connection broken")

        # switch = {
        #     SYN: self.accept(message),
        #     ACK: self.resolve(message),
        #     FIN: self.disconnect(message),
        #     NONE: self.resolve(message)
        # }

        # switch[message['flag']]
    
    # Wait for the client to initiate a three-way handshake
    def accept(self):
        # Get message
        message = self.buffer.pop(0)

        # Generate random seq_nr
        self._seq_nr = random.randint(0, 2 ** 16)

        # Set ack number
        self._ack_nr = message['seq_nr']+1

        # Send SYNACK
        segment = self.make_segment(seq_nr=self._seq_nr,
                                    ack_nr=self._ack_nr,
                                    flag=SYNACK)
        
        print("Server sent SYNACK")
        self.send(segment)

        self.synack_sent = True

    # Send any incoming data to the application layer
    def recv(self):
        pass

    # Send data originating from the application in a reliable way to the client
    def send(self, segment):
        self._lossy_layer.send_segment(segment)

    def disconnect(self):

        message = self.buffer.pop(0)

        # Set ack number
        self._ack_nr = message['seq_nr']+1

        # Send SYNACK
        segment = self.make_segment(seq_nr=self._seq_nr,
                                    ack_nr=self._ack_nr,
                                    flag=FINACK)
        print("Server sent FINACK")
        self.send(segment)

        self.finack_sent = True


    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()
