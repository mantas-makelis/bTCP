import array
import struct
import time
import random
import queue
from btcp.constants import BUFFER_SIZE, SEGMENT_KEYS, HEADER_FORMAT, DATA_FORMAT
from btcp.enums import Flag, State, Key


class BTCPSocket:
    """ Base bTCP socket on which both client and server sockets are based """
    
    def __init__(self, window, timeout):
        self._window = window
        self._timeout = timeout
        self.state = State.OPEN
        self.seq_nr = self.ack_nr = 0
        self.buffer = queue.Queue(BUFFER_SIZE)
        self.drop = {}


    def _handle_flow(self):
        """ Decides where to put a received message """
        # Check the buffer for incomming messages
        try:
            segment = self.buffer.get(block=False)
            message, has_data = self.unpack_segment(segment)
            # Throw away the segment if the checksum is invalid
            if not self.valid_checksum(message, has_data):
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


    def pack_segment(self, data=None, flag=Flag.NONE):
        """ Creates a segment with the given data and current sequence and acknoledgement numbers """
        data_size = len(data) if data else 0
        header = struct.pack(HEADER_FORMAT,
                             self.seq_nr,   # sequence number (halfword, 2 bytes)
                             self.ack_nr,   # acknowledgement number (halfword, 2 bytes)
                             flag.value,    # flags (byte),
                             self._window,  # window (byte)
                             data_size,     # data length (halfword, 2 bytes)
                             0)             # checksum (halfword, 2 bytes)
        if data is None:
            cksum = self.calc_checksum(header)
            header = struct.pack(HEADER_FORMAT, self.seq_nr, self.ack_nr, flag.value, self._window, data_size, cksum)
            return header
        else:
            packed_data = struct.pack(DATA_FORMAT, data)
            cksum = self.calc_checksum(header + packed_data)
            header = struct.pack(HEADER_FORMAT, self.seq_nr, self.ack_nr, flag.value, self._window, data_size, cksum)
            return header + packed_data


    def unpack_segment(self, segment):
        """ Creates a dictionary representation of the received segment """
        has_data = False
        try:
            unpacked = struct.unpack(HEADER_FORMAT + DATA_FORMAT, segment)
            has_data = True
        except:
            unpacked = struct.unpack(HEADER_FORMAT, segment)
        unpacked = dict(zip(SEGMENT_KEYS, unpacked))
        unpacked['flag'] = Flag(unpacked['flag'])
        return unpacked, has_data


    @staticmethod
    def valid_checksum(msg, has_data):
        """ Validates the received checksum """
        if has_data:
            packed_seg = struct.pack(HEADER_FORMAT + DATA_FORMAT, msg['seq'], msg['ack'], msg['flag'], msg['win'], msg['dlen'], 0, msg['data'])
        else:
            packed_seg = struct.pack(HEADER_FORMAT, msg['seq'], msg['ack'], msg['flag'].value, msg['win'], msg['dlen'], 0)
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