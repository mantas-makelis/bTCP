from functools import partial

from btcp.btcp_socket import BTCPSocket
from btcp.classes import Payload, BadState
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

    def lossy_layer_input(self, segment: bytes, address) -> None:
        """ Called by the lossy layer from another thread whenever a segment arrives. """
        self.buffer.put(segment, block=True, timeout=50)

    def connect(self) -> None:
        """ Perform a three-way handshake to establish a connection """
        if self.state is not State.OPEN:
            raise BadState('Only non-connected client can make a connection')
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
            segment = self.handle_flow(expected=[Flag.SYNACK])
            if segment:
                # Given an incorrect SEQ number reset the connect attempts
                if not self.valid_ack(segment):
                    syn_count = 0
                    continue
                # Send ACK for the received SYNACK
                self.seq_nr = self.safe_incr(self.seq_nr)
                self.ack_nr = self.safe_incr(segment.seq_nr)
                self.acknowledge_post(segment, Flag.ACK)
                self.state = State.CONN_EST
                if self.show_prints:
                    print('-- Client established connection --')
            # Increase the timer
            syn_timer = self.time() - start_timer

    def send(self, file: str) -> None:
        """ Send data originating from the application in a reliable way to the server """
        if self.state is not State.CONN_EST:
            raise BadState('Send is only allowed if the connection is established')
        # Arrange the data into payloads as buffer
        payloads = self._prepare_payloads(file)
        load_count = len(payloads)
        # Set window pointers
        lower = 0
        upper = self.recv_win if load_count > self.recv_win else load_count
        # Set in-flight trackers
        highest_sent = lowest_acked = 0
        while lower != upper:
            # Send/resend segments
            for payload in payloads[lower:upper]:
                # Do not send any if pending segments are more than window size
                in_flight = highest_sent - lowest_acked
                if self.others_recv_win - in_flight <= 0:
                    break
                # Filter out only not sent or timed out segments
                if not payload.sent or payload.timer > self._timeout:
                    self.post(seq_nr=self.seq_nr+payload.id, ack_nr=self.ack_nr, flag=Flag.NONE, data=payload.data)
                    payload.sent = True
                    payload.timer = 0
                    payload.start_time = self.time()
                    highest_sent = payload.id if payload.id > highest_sent else highest_sent
            segment = self.handle_flow(expected=[Flag.ACK])
            if segment:
                # Find the segment which was acknowledged
                for payload in payloads[lower:upper]:
                    if segment.ack_nr == self.seq_nr + payload.id + 1:
                        payload.is_acked = True
                        break
                # Move window for each acknowledged segment
                for payload in payloads[lower:upper]:
                    # Stop when unacknowledged segment is encountered
                    if not payload.is_acked:
                        break
                    lower += 1
                    upper += 1 if upper < load_count else 0
            # Update timers for each sent and unacknowledged segment
            for payload in payloads[lower:upper]:
                if payload.sent:
                    payload.timer = self.time() - payload.start_time

    def disconnect(self) -> None:
        """ Perform a three-way handshake to terminate a connection """
        if self.state is not State.CONN_EST:
            raise BadState('Only connected client can disconnect')
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
            segment = self.handle_flow(expected=[Flag.FINACK])
            if segment:
                # Given an incorrect SEQ number reset the disconnect attempts
                if not self.valid_ack(segment):
                    fin_count = 0
                    continue
                # Send ACK for the received FINACK
                self.seq_nr = self.safe_incr(self.seq_nr)
                self.acknowledge_post(segment, Flag.ACK)
                self.state = State.OPEN
                if self.show_prints:
                    print('-- Client terminated connection --', flush=True)
            # Increase the timer
            fin_timer = self.time() - start_timer

    def close(self) -> None:
        """ Clean up any state """
        self._lossy_layer.destroy()

    def _prepare_payloads(self, file: str) -> [Payload]:
        payloads = []
        with open(file, 'rb') as f:
            for i, payload in enumerate(iter(partial(f.read, PAYLOAD_SIZE), b'')):
                payloads.append(Payload(identifier=i, data=payload))
        return payloads
