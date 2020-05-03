from btcp.btcp_socket import BTCPSocket
from btcp.constants import CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT, MAX_ATTEMPTS, PAYLOAD_SIZE
from btcp.enums import State, Flag
from btcp.lossy_layer import LossyLayer
from btcp.segment import Segment


class BTCPClientSocket(BTCPSocket):
    """ bTCP client socket
    A client application makes use of the services provided by bTCP by calling connect, send, disconnect, and close 
    """

    def __init__(self, window: int, timeout: int, show_prints: bool):
        super().__init__(window, timeout, 'Client', show_prints)
        self._lossy_layer = LossyLayer(self, CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT)

    def lossy_layer_input(self, segment: bytes, address) -> None:
        """ Called by the lossy layer from another thread whenever a segment arrives. """
        self.buffer.put(segment, block=True, timeout=50)

    def connect(self) -> None:
        """ Perform a three-way handshake to establish a connection """
        # Only non-connected client can make a connection
        if self.state is not State.OPEN:
            return
        # Initialize local variables
        syn_count = syn_timer = start_timer = 0
        # Attempt to connect while the state is unchanged or maximum attempts are exceeded
        while self.state is State.OPEN and syn_count < MAX_ATTEMPTS:
            # Send SYN if it was not yet sent or if the timer expired
            if syn_count == 0 or syn_timer > self._timeout:
                self.post(seq_nr=self.seq_nr, ack_nr=self.ack_nr, flag=Flag.SYN)
                syn_count += 1
                syn_timer = 0
                start_timer = self.time()
            # Handle the incoming traffic
            message = self.handle_flow(expected=[Flag.SYNACK])
            if message:
                # Given an incorrect SEQ number reset the connect attempts
                if not self.valid_ack(message):
                    syn_count = 0
                    continue
                # Send ACK for the received SYNACK
                self.seq_nr = self.safe_incr(self.seq_nr)
                self.ack_nr = self.safe_incr(message['seq_nr'])
                self.acknowledge_post(message, Flag.ACK)
                self.state = State.CONN_EST
                if self.show_prints:
                    print('-- Client established connection --')
            # Increase the timer
            syn_timer = self.time() - start_timer

    def send(self, data: bytes) -> None:
        """ Send data originating from the application in a reliable way to the server """
        # Only allow sending if the connection is established
        if self.state is not State.CONN_EST:
            return
        # Prepare the data for transfer
        segments = self.meta_data(data)
        # self.seq_nr = segments[-1].exp_ack
        seg_end = len(segments)
        # Window pointers
        lower = 0
        upper = self.recv_win if seg_end > self.recv_win else seg_end
        recv_win_full = self.others_recv_win <= 0
        recv_win_full_timer = start_time = 0
        # Send the data until all segments were acknowledged
        while lower != upper:
            # Send/resend segments
            for segment in segments[lower:upper]:
                # Counting pending segments
                in_flight = sum([s.sent - s.is_acked for s in segments[lower:upper]])
                if self.others_recv_win - in_flight <= 0:
                    break
                if not segment.sent or segment.timer > self._timeout:
                    self.post(seq_nr=segment.seq_nr, ack_nr=self.ack_nr, flag=Flag.NONE, data=segment.data)
                    segment.sent = True
                    segment.timer = 0
                    segment.start_time = self.time()
            message = self.handle_flow(expected=[Flag.ACK])
            if message:
                # Find the segment which was acknowledged
                for segment in segments[lower:upper]:
                    if message['ack_nr'] == segment.exp_ack:
                        segment.is_acked = True
                        self.seq_nr = segment.exp_ack
                        break
                # Move window for each acknowledged segment
                for segment in segments[lower:upper]:
                    # Stop when unacknowledged segment is encountered
                    if not segment.is_acked:
                        break
                    lower += 1
                    upper += 1 if upper < seg_end else 0
            # Update timers for each sent and unacknowledged segment
            for segment in segments[lower:upper]:
                if segment.sent:
                    segment.timer = self.time() - segment.start_time            

    def disconnect(self) -> None:
        """ Perform a three-way handshake to terminate a connection """
        # Only connected client can disconnect
        if self.state is not State.CONN_EST:
            return
        # Initialize local variables
        fin_count = fin_timer = start_timer = 0
        # Attempt to disconnect while the state is unchanged or maximum attempts are exceeded
        while self.state is State.CONN_EST and fin_count < MAX_ATTEMPTS:
            # Send FIN if it was not yet sent or if the timer expired
            if fin_count == 0 or fin_timer > self._timeout:
                self.post(seq_nr=self.seq_nr, ack_nr=self.ack_nr, flag=Flag.FIN)
                fin_count += 1
                fin_timer = 0
                start_timer = self.time()
            # Handle the incoming traffic
            message = self.handle_flow(expected=[Flag.FINACK])
            if message:
                # Given an incorrect SEQ number reset the disconnect attempts
                if not self.valid_ack(message):
                    fin_count = 0
                    continue
                # Send ACK for the received FINACK
                self.seq_nr = self.safe_incr(self.seq_nr)
                self.acknowledge_post(message, Flag.ACK)
                self.state = State.OPEN
                if self.show_prints:
                    print('-- Client terminated connection --', flush=True)
            # Increase the timer
            fin_timer = self.time() - start_timer

    def close(self) -> None:
        """ Clean up any state """
        self._lossy_layer.destroy()

    def meta_data(self, data: bytes) -> [Segment]:
        """ Turns the data bytes into segments with their meta data """
        split_data = self.split_data(data)
        segments = []
        for i, data in enumerate(split_data):
            seq_nr = self.safe_incr(self.seq_nr, addition=i * PAYLOAD_SIZE)
            exp_ack = self.safe_incr(seq_nr, addition=len(data))
            segments.append(Segment(data=data, seq_nr=seq_nr, exp_ack=exp_ack))
        return segments

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