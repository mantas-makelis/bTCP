import array
import os
import struct
import time
import socket


class BTCPSocket:
    def __init__(self, window, timeout):
        self._window = window
        self._timeout = timeout
        self._seq_nr = 0
        self._ack_nr = 0
        self.types = ["sequence", "acknowledge", "flag", "window", "datalength", "checksum"]

    @staticmethod
    def in_cksum(data):
        """[Return the Internet checksum of data]

        Arguments:
            data {[bytes]} -- [header and data bytes for the segment]

        Returns:
            [bytes] -- [checksum]
        """

        # Padding
        if len(data) % 2 == 1:
            data += "\0"

        # split into 16-bit substrings
        strarr = array.array("H", data)

        # sum
        cksum = sum(strarr)

        # carry
        cksum = (cksum >> 16) + (cksum & 0xffff)

        # carry in case of spill
        cksum += (cksum >> 16)

        # 1's complement
        cksum = ~cksum & 0xffff

        return cksum

    def make_segment(self, data, flag=0):
        """[Creates a segment given the data]

        Arguments:
            data {[bytes]} -- [data for the segment]

        Keyword Arguments:
            flag {int} -- [1=ACK, 2=SYN, 3=SYN+ACK, 4=FIN, 5=FIN+ACK] (default: {0})

        Returns:
            [bytes] -- [a segment message]
        """

        if data is None:
            data = 0

        # The resulting bytes are in network byte order
        header = struct.pack("!HHbbHH",
                             self._seq_nr,       # sequence number (halfword, 2 bytes)
                             self._ack_nr,       # acknowledgement number (halfword, 2 bytes)
                             flag,               # flags (byte), [1=ACK, 2=SYN, 3=SYN+ACK, 4=FIN, 5=FIN+ACK]
                             self._window,       # window (byte)
                             len(str(data)),          # data length (halfword, 2 bytes)
                             0)                  # checksum (halfword, 2 bytes)

        data = struct.pack("!d", data)

        # Calculate the checksum on the data and the dummy header.
        myChecksum = self.in_cksum(header + data)
        
        header = struct.pack("!HHbbHH", 
                             self._seq_nr,
                             self._ack_nr,
                             flag,
                             self._window,
                             len(data),
                             myChecksum)                 
        message = header + data

        return message

    @staticmethod
    def read_segment(self, segment):
        unpacked = struct.unpack('!HHbbHH')
        data = dict(zip(self.types, unpacked))
        # received_flag = 

        return data
