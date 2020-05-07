import array
import queue
import random
import struct
import time
from typing import Optional

from btcp.classes import Segment, WrongFlag
from btcp.constants import SEGMENT_KEYS, HEADER_FORMAT, DATA_FORMAT, PAYLOAD_SIZE, TWO_BYTES
from btcp.enums import Flag, State


class BTCPSocket:
    """ Base bTCP socket on which both client and server sockets are based """

    def __init__(self, window: int, timeout: int, name: str, show_prints: bool = False):
        self._window = window
        self._timeout = timeout
        self._name = name
        self.connectedAddress = None
        self.show_prints = show_prints
        self.recv_win = 0
        self.others_recv_win = 0
        self.state = State.OPEN
        self.seq_nr = self.start_random_sequence()
        self.ack_nr = 0
        self.buffer = queue.Queue(window)
        self.data_buffer = {}

    def handle_flow(self, expected: [Flag]) -> Optional[Segment]:
        """ Checks if any message was received and returns it if it was """
        try:
            address, segment = self.buffer.get(block=False)
            unpacked_segment = self.unpack_segment(segment)
            unpacked_segment.address = address
            if self.state is State.CONN_EST and self.connectedAddress != unpacked_segment.address:
                return None
            if unpacked_segment.flag in expected and self.valid_checksum(unpacked_segment):
                self.others_recv_win = unpacked_segment.win
                return unpacked_segment
        except queue.Empty:
            pass
        return None

    def acknowledge_post(self, segment: Segment, flag: Flag) -> None:
        """ Sends an acknowledgement segment """
        if flag not in [Flag.ACK, Flag.SYNACK, Flag.FINACK]:
            raise WrongFlag('Only acknowledgement flag can be sent using this method')
        self.post(self.seq_nr, self.safe_incr(segment.seq_nr), flag)

    def post(self, seq_nr: int, ack_nr: int, flag: Flag, data: bytes = b''):
        """ Sends a segment """
        segment = self.pack_segment(seq_nr=seq_nr, ack_nr=ack_nr, data=data, flag=flag)
        if self.show_prints:
            print(f'[seq: {seq_nr}; ack: {ack_nr}] {self._name} sent {flag.name}', flush=True)
        self._lossy_layer.send_segment(segment)

    def valid_ack(self, segment: Segment, addition: int = 1) -> bool:
        """ Checks if the received ACK number is good """
        return self.safe_incr(self.seq_nr, addition) == segment.ack_nr

    def pack_segment(self, seq_nr: int = -1, ack_nr: int = 0, data: bytes = b'', flag: Flag = Flag.NONE) -> bytes:
        """ Creates a segment with the given data and current sequence and acknowledgement numbers """
        data_size = len(data)
        if data_size > PAYLOAD_SIZE:
            raise ValueError
        if seq_nr == -1:
            seq_nr = self.seq_nr
        self.recv_win = self._window - self.buffer.qsize() - len(self.data_buffer)
        header = struct.pack(HEADER_FORMAT,
                             seq_nr,  # sequence number (halfword, 2 bytes)
                             ack_nr,  # acknowledgement number (halfword, 2 bytes)
                             flag.value,  # flags (byte),
                             self.recv_win,  # window (byte)
                             data_size,  # data length (halfword, 2 bytes)
                             0)  # checksum (halfword, 2 bytes)
        payload = struct.pack(DATA_FORMAT, data)
        cksum = self.calc_checksum(header + payload)
        header = struct.pack(HEADER_FORMAT, seq_nr, ack_nr, flag.value, self.recv_win, data_size, cksum)
        return header + payload

    def unpack_segment(self, segment: bytes) -> Segment:
        """ Creates a dictionary representation of the received segment """
        unpacked = struct.unpack(HEADER_FORMAT + DATA_FORMAT, segment)
        unpacked = dict(zip(SEGMENT_KEYS, unpacked))
        return Segment(unpacked)

    def valid_checksum(self, segment: Segment) -> bool:
        """ Validates the received checksum """
        packed_seg = struct.pack(HEADER_FORMAT + DATA_FORMAT, segment.seq_nr, segment.ack_nr,
                                 segment.flag.value, segment.win, segment.dlen, 0, segment.data)
        cksum = self.calc_checksum(packed_seg)
        return cksum == segment.cksum

    def calc_checksum(self, segment: bytes) -> int:
        """ Calculates the checksum for segment data """
        if len(segment) % 2 == 1:  # padding
            segment += b'\x00'
        strarr = array.array('H', segment)  # split into 16-bit substrings
        cksum = sum(strarr)  # sum
        cksum = (cksum >> 16) + (cksum & 0xffff)  # carry
        cksum += (cksum >> 16)  # carry in case of spill
        cksum = ~cksum & 0xffff  # 1's complement
        return cksum

    def time(self) -> int:
        """ Returns current time in milliseconds """
        return int(round(time.time() * 1000))

    def start_random_sequence(self) -> int:
        """ Generates a random two byte number """
        return random.randint(0, TWO_BYTES)

    def safe_incr(self, number: int, addition: int = 1) -> int:
        """ Returns the successor with a wraparound condition in case its larger than two bytes """
        summed = number + addition
        return summed if summed < TWO_BYTES else summed % TWO_BYTES
