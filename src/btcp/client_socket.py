from functools import partial

from btcp.btcp_socket import BTCPSocket
from btcp.classes import Payload, BadState, Segment
from btcp.constants import CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT, MAX_ATTEMPTS, PAYLOAD_SIZE
from btcp.enums import State, Flag
from btcp.lossy_layer import LossyLayer


class BTCPClientSocket(BTCPSocket):
    """ bTCP client socket
    A client application makes use of the services provided by bTCP by calling connect, send, disconnect, and close 
    """

    def __init__(self, window: int, timeout: int, show_prints: bool = False):
        super().__init__(window, timeout, 'Client', show_prints)
        self._lossy_layer = LossyLayer(self, CLIENT_IP, CLIENT_PORT, SERVER_IP, SERVER_PORT)

    def lossy_layer_input(self, segment: bytes, address: str) -> None:
        """ Called by the lossy layer from another thread whenever a segment arrives. """
        self.buffer.put((address, segment), block=True, timeout=25)

    def connect(self) -> None:
        """ Perform a three-way handshake to establish a connection """
        if self.state is not State.OPEN:
            raise BadState('Only non-connected client can make a connection')
        # Initialize local variables
        syn_count = syn_timer = start_timer = 0
        # Attempt to connect while the state is unchanged or maximum attempts are exceeded
        while syn_count < MAX_ATTEMPTS:
            # Send SYN if it was not yet sent or if the timer expired
            counter, timer, start_timer = self._send_syn_fin(syn_count, syn_timer, start_timer, Flag.SYN)
            # Handle the incoming traffic
            segment = self.handle_flow(expected=[Flag.SYNACK])
            if segment:
                # Given an incorrect SEQ number reset the connect attempts
                if not self.valid_ack(segment):
                    syn_count = 0
                    continue
                # Send ACK for the received SYNACK
                self._synack_finack_resp(segment, State.CONN_EST)
                self.connectedAddress = segment.address
                break
            # Increase the timer
            syn_timer = self.time() - start_timer
        # Print information regarding the client's state
        self._connect_prints(syn_count)

    def send(self, file: str) -> None:
        """ Send data originating from the application in a reliable way to the server """
        if self.state is not State.CONN_EST:
            raise BadState('Send is only allowed if the connection is established')
        # Setup payloads and pointers
        payloads, payload_count, lower, upper, highest_id_sent = self._setup(file)
        while lower != upper:
            # Send/resend segments
            highest_id_sent = self._send_resend_segments(highest_id_sent, payloads, lower, upper)
            segment = self.handle_flow(expected=[Flag.ACK])
            if segment:
                # Find the segment which was acknowledged
                self._find_acked_segment(segment, payloads, lower, upper)
                # Move window for each acknowledged segment
                lower, upper = self._slide_window(payloads, payload_count, lower, upper)
            # Update timers for each sent and unacknowledged segment
            for payload in payloads[lower:upper]:
                if payload.sent:
                    payload.timer = self.time() - payload.start_time
            # Update the upper pointer of the receiving window
            new_upper = upper + self.others_recv_win - (upper - lower)
            upper = new_upper if new_upper < payload_count else payload_count
        # Update the sequence number after the file was sent
        self.seq_nr = self.safe_incr(self.seq_nr, payloads[-1].id)

    def disconnect(self) -> None:
        """ Perform a three-way handshake to terminate a connection """
        if self.state is not State.CONN_EST:
            raise BadState('Only connected client can disconnect')
        # Initialize local variables
        fin_count = fin_timer = start_timer = 0
        # Attempt to disconnect while the state is unchanged or maximum attempts are exceeded
        while self.state is State.CONN_EST and fin_count < MAX_ATTEMPTS:
            # Send FIN if it was not yet sent or if the timer expired
            counter, timer, start_timer = self._send_syn_fin(fin_count, fin_timer, start_timer, Flag.FIN)
            # Handle the incoming traffic
            segment = self.handle_flow(expected=[Flag.FINACK])
            if segment:
                # Given an incorrect SEQ number reset the disconnect attempts
                if not self.valid_ack(segment):
                    fin_count = 0
                    continue
                # Send ACK for the received FINACK
                self._synack_finack_resp(segment, State.OPEN)
                if self.show_prints:
                    print('-- Client terminated connection --', flush=True)
            # Increase the timer
            fin_timer = self.time() - start_timer

    def _prepare_payloads(self, file: str) -> [Payload]:
        """ Segments the file to a list of payloads """
        payloads = []
        with open(file, 'rb') as f:
            for i, payload in enumerate(iter(partial(f.read, PAYLOAD_SIZE), b'')):
                payloads.append(Payload(identifier=i, data=payload))
        return payloads

    def _send_syn_fin(self, counter: int, timer: int, start_timer: int, flag: Flag) -> tuple:
        """ Helper function to send SYNs or FINs """
        if counter == 0 or timer > self._timeout:
            self.post(seq_nr=self.seq_nr, ack_nr=self.ack_nr, flag=flag)
            counter += 1
            timer = 0
            start_timer = self.time()
        return counter, timer, start_timer

    def _connect_prints(self, syn_count: int) -> None:
        """ Prints information regarding the client's state during connection"""
        if self.show_prints and syn_count < MAX_ATTEMPTS:
            print('-- Client established connection --')
        elif self.show_prints and syn_count >= MAX_ATTEMPTS:
            print('--! Client timed out !--')

    def _synack_finack_resp(self, segment: Segment, state: State) -> None:
        """ Sends an ACK for the received SYNACK """
        self.seq_nr = self.safe_incr(self.seq_nr)
        self.ack_nr = self.safe_incr(segment.seq_nr)
        self.acknowledge_post(segment, Flag.ACK)
        self.state = state

    def _setup(self, file: str) -> tuple:
        """ Sets the initial payloads and necessary pointers """
        # Arrange the data into payloads as buffer
        payloads = self._prepare_payloads(file)
        payload_count = len(payloads)
        # Set window pointers
        lower = highest_id_sent = 0
        upper = self.others_recv_win if payload_count > self.others_recv_win else payload_count
        return payloads, payload_count, lower, upper, highest_id_sent

    def _send_resend_segments(self, highest_id_sent: int, payloads: list, lower: int, upper: int) -> int:
        """ Sends or resends segments in current window """
        for payload in payloads[lower:upper]:
            # Filter out only not sent or timed out segments
            if not payload.sent or payload.timer > self._timeout:
                seq_nr = self.safe_incr(self.seq_nr, payload.id)
                self.post(seq_nr=seq_nr, ack_nr=self.ack_nr, flag=Flag.NONE, data=payload.data)
                payload.sent = True
                payload.timer = 0
                payload.start_time = self.time()
                highest_id_sent = payload.id if payload.id > highest_id_sent else highest_id_sent
        return highest_id_sent

    def _find_acked_segment(self, segment: Segment, payloads: list, lower: int, upper: int) -> None:
        """ Finds the segment which was acknowledged """
        for payload in payloads[lower:upper]:
            if segment.ack_nr == self.safe_incr(self.seq_nr, self.safe_incr(payload.id)):
                payload.is_acked = True
                break

    def _slide_window(self, payloads: list, payload_count: int, lower: int, upper: int) -> tuple:
        """ Slides up the current window by counting acknowledged segments, starting from the lowest one"""
        for payload in payloads[lower:upper]:
            # Stop when unacknowledged segment is encountered
            if not payload.is_acked:
                break
            lower += 1
            upper += 1 if upper < payload_count else 0
        return lower, upper

    def close(self) -> None:
        """ Clean up any state """
        self._lossy_layer.destroy()