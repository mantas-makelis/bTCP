from btcp.btcp_socket import BTCPSocket
from btcp.lossy_layer import LossyLayer
from btcp.constants import *
import random
import time

# bTCP client socket
# A client application makes use of the services provided by bTCP by calling connect, send, disconnect, and close
class BTCPClientSocket(BTCPSocket):
    def __init__(self, window, timeout):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT)
        self.syn_sent = False
        self.fin_sent = False

    # Called by the lossy layer from another thread whenever a segment arrives. 
    def lossy_layer_input(self, segment, address):

        # Unpack the segment
        message = self.unpack_segment(segment)

        # Put it in the buffer
        self.buffer.append(message)

    # Perform a three-way handshake to establish a connection
    def connect(self):
        syn_count = 0
        current_timer = 0
        while not self.con_est and syn_count < MAX_ATTEMPTS:
            
            if not self.syn_sent or current_timer > TIMEOUT:

                # Generate random seq_nr
                self._seq_nr = random.randint(0, 2 ** 16)

                # Send SYN
                segment = self.make_segment(seq_nr=self._seq_nr,
                                            flag=SYN)

                # The SYN will be sent
                self.syn_sent = True
                print("Client sent SYN")

                # Increase counter
                syn_count += 1
                
                # Start timer
                current_timer = 0
                start_timer = time.time()

                # Send the segment
                self.send(segment)


            elif self.buffer:

                # Get message
                message = self.buffer.pop(0)

                # Look at the flag
                if message['flag'] == SYNACK:

                    # Increase seq_nr
                    self._seq_nr += 1

                    # Set ack number 
                    self._ack_nr = message['seq_nr']+1

                    # Send ACK
                    segment = self.make_segment(seq_nr=self._seq_nr,
                                                ack_nr=self._ack_nr,
                                                flag=ACK)
                    # The connection is established
                    self.con_est = True

                    print("Client sent ACK")

                    # Send the segment
                    self.send(segment)
                else:
                    self.buffer.push(message)
                    current_timer = time.time() - start_timer
            else:
                current_timer = time.time() - start_timer

        if syn_count > MAX_ATTEMPTS:
            self.close()


    # Send data originating from the application in a reliable way to the server
    def send(self, segment):
        self._lossy_layer.send_segment(segment)

    # Perform a handshake to terminate a connection
    def disconnect(self):

        fin_count = 0
        current_timer = 0
        while self.con_est and fin_count < MAX_ATTEMPTS:
            
            if not self.fin_sent or current_timer > TIMEOUT:
                
                # Set seq number
                self._seq_nr += 1

                # Send FIN
                segment = self.make_segment(seq_nr=self._seq_nr,
                                            ack_nr=self._ack_nr,
                                            flag=FIN
                                            )

                # The SYN will be sent
                self.fin_sent = True
                print("Client sent FIN")

                # Increase counter
                fin_count +=1
                
                # Start timer
                current_timer = 0
                start_timer = time.time()

                # Send the segment
                self.send(segment)


            elif self.buffer:

                # Get message
                message = self.buffer.pop(0)

                # Look at the flag
                if message['flag'] == FINACK:

                    # Increase seq_nr
                    self._seq_nr += 1

                    # Set ack number 
                    self._ack_nr = message['seq_nr']+1

                    # Send ACK
                    segment = self.make_segment(seq_nr=self._seq_nr,
                                                ack_nr=self._ack_nr,
                                                flag=ACK)
                    # The connection is established
                    self.con_est = False

                    print("Client sent ACK")

                    # Send the segment
                    self.send(segment)
                else:
                    self.buffer.push(message)
                    current_timer = time.time() - start_timer
            else:
                current_timer = time.time() - start_timer

        if fin_count > MAX_ATTEMPTS:
            self.close()

    # Clean up any state
    def close(self):
        self._lossy_layer.destroy()
