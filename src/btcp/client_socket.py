from btcp.btcp_socket import BTCPSocket
from btcp.constants import CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT, MAX_ATTEMPTS, PAYLOAD_SIZE
from btcp.enums import State, Flag, Key
from btcp.lossy_layer import LossyLayer
from btcp.segment import Segment


class BTCPClientSocket(BTCPSocket):
    """ bTCP client socket
    A client application makes use of the services provided by bTCP by calling connect, send, disconnect, and close 
    """

    def __init__(self, window: int, timeout: int):
        super().__init__(window, timeout)
        self._lossy_layer = LossyLayer(self, CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT)

    def lossy_layer_input(self, segment: bytes, address) -> None:
        """ Called by the lossy layer from another thread whenever a segment arrives. """
        self.buffer.put(segment, block=True, timeout=100)

    def connect(self) -> None:
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
                segment = self.pack_segment(flag=Flag.SYN)
                self._lossy_layer.send_segment(segment)
                syn_count += 1
                print(f'Client sent SYN (seq: {self.seq_nr}, ack: -)')
                timer = 0
                start_timer = self.time()
            # Block for receiving SYNACK
            elif Key.SYNACK in self.drop:
                message = self.drop.pop(Key.SYNACK)
                if self.safe_incr(self.seq_nr) == message['ack_nr']:
                    self.recv_win = message['win']
                    self.seq_nr = self.safe_incr(self.seq_nr)
                    ack_nr = self.safe_incr(message['seq_nr'])
                    segment = self.pack_segment(ack_nr=message['seq_nr'], flag=Flag.ACK)
                    self._lossy_layer.send_segment(segment)
                    self.state = State.CONN_EST
                    print(
                        f'Client sent ACK (seq: {self.seq_nr}, ack: {self.safe_incr(message["seq_nr"])}) and established connection')
                # Given an incorrect seq nr reset the connect attempt
                else:
                    syn_count = 0
            # Increase the timer if nothing happens
            else:
                timer = self.time() - start_timer
        # Reset the state if the connection failed
        if self.state is not State.CONN_EST and syn_count >= MAX_ATTEMPTS:
            self.state = State.OPEN

    def split_data(self, data: bytes) -> [bytes]:
        """ Splits the data into chunks of 1008 bytes """
        size = len(data)
        last = size % PAYLOAD_SIZE  # remaining data for the last chunk
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
        split_data.append(data[to:to + last])
        return split_data

    def meta_data(self, data: bytes) -> [Segment]:
        """ Turns the data bytes into segments with their meta data """
        split_data = self.split_data(data)
        segments = []
        for i, data in enumerate(split_data):
            seq_nr = self.safe_incr(self.seq_nr, addition=i * PAYLOAD_SIZE)
            exp_ack = seq_nr + len(data)
            segments.append(Segment(seq=seq_nr, exp_ack=exp_ack, data=data))
        return segments

    def send(self, data: bytes) -> None:
        """ Send data originating from the application in a reliable way to the server """
        # Only allow sending if the connection is established
        if self.state is not State.CONN_EST:
            return
        self.state = State.TRANS
        # Calculate meta data for all segments
        segments = self.meta_data(data)
        seg_end = len(segments)
        # Window pointers
        lower = 0
        upper = self.recv_win if seg_end > self.recv_win else seg_end
        # Send the data until all segments were acknowledged
        while lower != upper:
            # Send/resend segments
            for segment in segments[lower:upper]:
                if not segment.sent or segment.timer > self._timeout:
                    packed = self.pack_segment(seq_nr=segment.seq, data=segment.data)
                    self._lossy_layer.send_segment(packed)
                    print(f'Client sent segment {segment.seq}')
                    segment.sent = True
                    segment.start_time = self.time()
            # Block for handling the received ACKs
            if Key.RECV_ACK in self.drop:
                message = self.drop.pop(Key.RECV_ACK)
                print(f"Client received ACK {message['ack_nr']}")
                # Find a segment which was acked
                for segment in segments[lower:upper]:
                    if message['ack_nr'] != segment.exp_ack:
                        continue
                    segment.is_acked = True
                    # Given that the first segment in the window is acked
                    if message['ack_nr'] == segments[lower].exp_ack:
                        # Check how many segments in a row are acked
                        for segment in segments[lower:upper]:
                            if not segment.is_acked:
                                break
                            lower += 1
                            upper += 1 if upper < seg_end else 0
                        break
            # Update timers for each sent and not ACKed segment
            for segment in segments[lower:upper]:
                if segment.sent:
                    segment.timer = self.time() - segment.start_time
            self._handle_flow()
        self.state = State.CONN_EST

    def disconnect(self) -> None:
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
            if (fin_count == 0 or timer > self._timeout) and fin_count < MAX_ATTEMPTS:
                segment = self.pack_segment(flag=Flag.FIN)
                self._lossy_layer.send_segment(segment)
                fin_count += 1
                print("Client sent FIN")
                timer = 0
                start_timer = self.time()
            # Block for receiving FINACK
            elif Key.FINACK in self.drop:
                message = self.drop.pop(Key.FINACK)
                if self.safe_incr(self.seq_nr) == message['ack_nr']:
                    self.seq_nr = self.safe_incr(self.seq_nr)
                    segment = self.pack_segment(ack_nr=self.safe_incr(self.seq_nr), flag=Flag.ACK)
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
            self.state = State.OPEN

    def close(self) -> None:
        """ Clean up any state """
        self._lossy_layer.destroy()
