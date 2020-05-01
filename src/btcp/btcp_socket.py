import array
import struct
import time
import random
import queue
from btcp.constants import BUFFER_SIZE, SEGMENT_KEYS, HEADER_FORMAT, DATA_FORMAT, PAYLOAD_SIZE
from btcp.enums import Flag, State, Key


class BTCPSocket:
    """ Base bTCP socket on which both client and server sockets are based """
    
    def __init__(self, window, timeout):
        self._window = window
        self._timeout = timeout
        self.recv_win = 0
        self.state = State.OPEN
        self.seq_nr = 0
        self.buffer = queue.Queue(window)
        self.drop = {}


    def _handle_flow(self):
        """ Decides where to put a received message """
        # Check the buffer for incoming messages
        try:
            segment = self.buffer.get(block=False)
            message = self.unpack_segment(segment)
            # Throw away the segment if the checksum is invalid
            if not self.valid_checksum(message):
                return
        except queue.Empty:
            return
        flag = message['flag']
        # Connection attempt
        if self.state is State.OPEN and flag is Flag.SYN:
            self.drop[Key.SYN] = message
        # Connection approval from the server
        elif self.state is State.CONN_PEND and flag is Flag.SYNACK:
            self.drop[Key.SYNACK] = message
        # Connection approval from the client
        elif self.state is State.CONN_PEND and flag is Flag.ACK:
            self.drop[Key.CONN_ACK] = message
        # Termination request
        elif flag is Flag.FIN:
            self.drop[Key.FIN] = message
        # Termination approval from the server
        elif self.state is State.DISC_PEND and flag is Flag.FINACK:
            self.drop[Key.FINACK] = message
        # Termination approval from the client
        elif self.state is State.DISC_PEND and flag is Flag.ACK:
            self.drop[Key.DISC_ACK] = message
        # While transmitting
        elif self.state is State.TRANS and flag is Flag.ACK:
            self.drop[Key.RECV_ACK] = message
        # While receiving
        elif self.state is State.RECV and flag is Flag.NONE:
            self.drop[Key.DATA] = message
    

    def pack_segment(self, ack_nr=0, data=b'', flag=Flag.NONE):
        """ Creates a segment with the given data and current sequence and acknowledgement numbers """
        data_size = len(data)
        if data_size > PAYLOAD_SIZE:
            return # TODO: throw an error
        win_size = self._window - self.buffer.qsize()
        header = struct.pack(HEADER_FORMAT,
                             self.seq_nr,   # sequence number (halfword, 2 bytes)
                             ack_nr,        # acknowledgement number (halfword, 2 bytes)
                             flag.value,    # flags (byte),
                             win_size,      # window (byte)
                             data_size,     # data length (halfword, 2 bytes)
                             0)             # checksum (halfword, 2 bytes)
        payload = struct.pack(DATA_FORMAT, data)
        cksum = self.calc_checksum(header + payload)
        header = struct.pack(HEADER_FORMAT, self.seq_nr, ack_nr, flag.value, win_size, data_size, cksum)
        return header + payload


    def unpack_segment(self, segment):
        """ Creates a dictionary representation of the received segment """
        unpacked = struct.unpack(HEADER_FORMAT + DATA_FORMAT, segment)
        unpacked = dict(zip(SEGMENT_KEYS, unpacked))
        unpacked['flag'] = Flag(unpacked['flag'])
        return unpacked


    @staticmethod
    def valid_checksum(msg):
        """ Validates the received checksum """
        packed_seg = struct.pack(HEADER_FORMAT + DATA_FORMAT, msg['seq'], msg['ack'], msg['flag'].value, msg['win'], msg['dlen'], 0, msg['data'])
        cksum = BTCPSocket.calc_checksum(packed_seg)
        return cksum == msg['cksum']


    @staticmethod
    def calc_checksum(segment):
        """ Calculates the checksum for segment data """
        if len(segment) % 2 == 1:                 # padding
            segment += b'\x00'
        strarr = array.array('H', segment)        # split into 16-bit substrings
        cksum = sum(strarr)                       # sum
        cksum = (cksum >> 16) + (cksum & 0xffff)  # carry
        cksum += (cksum >> 16)                    # carry in case of spill
        cksum = ~cksum & 0xffff                   # 1's complement
        return cksum


    @staticmethod
    def time():
        return int(round(time.time() * 1000))


    @staticmethod
    def start_random_sequence():
        return random.randint(0, 2 ** 16)