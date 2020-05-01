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

    # Called by the lossy layer from another thread whenever a segment arrives
    def lossy_layer_input(self, segment, address):
        print('got stuff')
        # Unpack the segment
        message = self.unpack_segment(segment)
        self.buffer.append(message)
    
    # Wait for the client to initiate a three-way handshake
    def accept(self):
        # while True:

        # Check whether the server has a connection
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
                else:
                    self.buffer.append(message)

    # Send any incoming data to the application layer
    def recv(self):

        while self.con_est:

            # While there are incoming segments
            while self.buffer:
                # Get message
                segment = self.buffer.pop(0)

                if segment['flag'] == ACK:
                    self.other(segment)
                    print('connection established')
                elif segment['flag'] == FIN:
                    print('disconnecting')
                    self.disconnect(segment)
                else:
                    self.buffer.append(segment)

    def other(self, segment):
        pass

    # Send data originating from the application in a reliable way to the client
    def send(self, segment):
        self._lossy_layer.send_segment(segment)

    def disconnect(self, segment):

        # Set ack number
        self._ack_nr = segment['seq_nr'] + 1

        # Send FINACK
        segment = self.make_segment(seq_nr=self._seq_nr,
                                    ack_nr=self._ack_nr,
                                    flag=FINACK)
        print("Server sent FINACK")
        self.send(segment)

        # Wait for final ACK
        while self.buffer:
            segment = self.buffer.pop(0)
            if segment['flag'] == ACK:
                self.con_est = False
                print('Server: Disconnected')
            else:
                self.buffer.append(segment)

    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()
