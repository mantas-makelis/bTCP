from btcp.btcp_socket import BTCPSocket
from btcp.lossy_layer import LossyLayer
from btcp.constants import CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT, MAX_ATTEMPTS, DATA_FORMAT, PAYLOAD_SIZE
from btcp.enums import State, Flag, Key
from btcp.segment import Segment
import array, struct

class BTCPClientSocket(BTCPSocket):
    """ bTCP client socket
    A client application makes use of the services provided by bTCP by calling connect, send, disconnect, and close 
    """

    def __init__(self, window, timeout):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT)

    def lossy_layer_input(self, segment, address):
        """ Called by the lossy layer from another thread whenever a segment arrives. """
        self.buffer.put(segment, block=True, timeout=100)
        

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
            self._handle_flow()
            # Block for sending SYN request
            if syn_count == 0 or timer > self._timeout:
                self.seq_nr = self.start_random_sequence()
                segment = self.pack_segment(flag=Flag.SYN)
                self._lossy_layer.send_segment(segment)
                syn_count += 1
                print(f'Client sent SYN (seq: {self.seq_nr}, ack: -)')
                timer = 0
                start_timer = self.time()
            # Block for receiving SYNACK
            elif Key.SYNACK in self.drop:
                message = self.drop.pop(Key.SYNACK)
                if self.seq_nr + 1 == message['ack']:
                    self.recv_win = message['win']
                    self.seq_nr += 1
                    segment = self.pack_segment(ack_nr=message['seq'] + 1, flag=Flag.ACK)
                    self._lossy_layer.send_segment(segment)
                    self.state = State.CONN_EST
                    print(f'Client sent ACK (seq: {self.seq_nr}, ack: {message["seq"] + 1}) and established connection')
                # Given an incorrect seq nr reset the connect attempt
                else:
                    syn_count = 0
            # Increase the timer if nothing happens
            else:
                timer = self.time() - start_timer
        # Reset the state if the connection failed
        if self.state is not State.CONN_EST and syn_count >= MAX_ATTEMPTS:
            self.state = State.OPEN


    def meta_data(self, data: bytes) -> [Segment]:
        size = len(data)
        last = size % PAYLOAD_SIZE
        length = int(size / PAYLOAD_SIZE)
        start = 0
        to = PAYLOAD_SIZE if size >= PAYLOAD_SIZE else 0
        split_data = []
        for i in range(length):
            split_data.append(data[start:to])
            # if not the last thing:
            if not i == length - 1:
                start += PAYLOAD_SIZE
                to += PAYLOAD_SIZE
        split_data.append(data[to:to+last])
    

        segments = []
        for i, data in enumerate(split_data):
            seq = self.seq_nr + i * PAYLOAD_SIZE
            exp_ack = seq + len(data)
            packed = self.pack_segment(data=data)
            segments.append(
                Segment(seq=seq,
                        exp_ack=exp_ack, 
                        packed=packed)
                        )
        return segments


    def send(self, data: bytes) -> None:
        """ Send data originating from the application in a reliable way to the server """
        if self.state is not State.CONN_EST:
            return        
        # Meta data for a segment
        segments = self.meta_data(data)
        
        # Window pointers
        lower = 0 
        upper = self.recv_win
        
        # Sending all data
        while lower != upper:
            
            # Sent segments
            for segment in segments[lower:upper]:
                # TODO: check if the window is available ???
                if not segment.sent or segment.timer < self._timeout:
                    self._lossy_layer.send_segment(segment.packed)
                    segment.sent = True
                    segment.start_time = self.time()
            
            # check messages
            if Key.RECV_ACK in self.drop:
                message = self.drop.pop(Key.RECV_ACK)
                for segment in segments[lower:upper]:
                    if message['ack'] != segment.exp_ack :
                        continue
                    segment.ack = True
                    if message['seq'] == segments[lower].seq:
                        steps = 0
                        for segment in segments[lower:upper]:
                            if segment.is_ack:
                                steps += 1
                        lower += steps
                        upper += steps
                        break
            
            # update time
            for segment in segments[lower:upper]:
                if segment.sent:
                    segment.timer = self.time() - segment.start_time

            self._handle_flow()


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
        while self.state is State.DISC_PEND:
            # Make a break and handle incoming segments
            self._handle_flow()
            # Block for sending FIN request
            if fin_count == 0 or timer > self._timeout:
                self.seq_nr += 1
                segment = self.pack_segment(flag=Flag.FIN)
                self._lossy_layer.send_segment(segment)
                fin_count += 1
                print("Client sent FIN")
                timer = 0
                start_timer = self.time()
            # Block for receiving FINACK
            elif Key.FINACK in self.drop:
                message = self.drop.pop(Key.FINACK)
                if self.seq_nr + 1 == message['ack']:
                    self.seq_nr += 1
                    segment = self.pack_segment(ack_nr=message['seq'] + 1, flag=Flag.ACK)
                    self._lossy_layer.send_segment(segment)
                    self.state = State.OPEN
                    print('Client sent ACK and terminated connection')
                # Given an incorrect seq nr reset the disconnect attempt
                else:
                    fin_count = 0
            # Increase the timer if nothing happens
            else:
                timer = self.time() - start_timer
        # Reset the state if the disconnect attempt failed
        if self.state is not State.OPEN and fin_count >= MAX_ATTEMPTS:
            self.state = State.CONN_EST


    def close(self):
        """ Clean up any state """
        self._lossy_layer.destroy()
