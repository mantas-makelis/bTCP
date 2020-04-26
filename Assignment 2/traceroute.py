# by Mantas Makelis (s1007870)

from socket import *
import os
import sys
import struct
import time
import random

ICMP_ECHO_REQUEST = 8
ICMP_TTL_EXCEEDED = 11
ICMP_ECHO_REPLY = 0
TIMEOUT = 5


def in_cksum(data):
    """ Calculated the checksum """
    # Source: https://www.codeproject.com/tips/460867/python-implementation-of-ip-checksum
    # This function was a nightmare, no way I was able to figure out how to do all these actions on bytes
    # No explanation in the assignment, no clues! What a shame...
    size = len(data)
    checksum = 0
    pointer = 0
    while size > 1:
        checksum += int((str("%02x" % (data[pointer])) +
                         str("%02x" % (data[pointer + 1]))), 16)
        size -= 2
        pointer += 2
    if size:
        checksum += data[pointer]
    checksum = (checksum >> 16) + (checksum & 0xffff)
    checksum += (checksum >> 16)
    return (~checksum) & 0xFFFF


def build_echo_request():
    """ builds an echo request message with correct checksum """
    ID = os.getpid() & 0xffff  # Return the current process i
    # Header is type (8), code (8), checksum (16), sequence (16)
    myChecksum = 0
    # Make a dummy header with a 0 checksum
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    # The resulting bytes are in network byte order
    header = struct.pack("!bbHHH",
                         ICMP_ECHO_REQUEST,  # type (byte)
                         0,                  # code (byte)
                         0,                  # checksum (halfword, 2 bytes)
                         ID,                 # ID (halfword)
                         1)                  # sequence (halfword)
    data = struct.pack("!d", time.time())

    # Calculate the checksum on the data and the dummy header.
    myChecksum = in_cksum(header + data)
    header = struct.pack("!bbHHH", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    message = header + data

    return message


MAX_HOPS = 30
NUM_OF_PROBES = 3


def main():
    """ main method """
    if len(sys.argv) != 2:
        print("USEAGE: \npython traceroute.py hostname")
        exit(0)
    hostname = sys.argv[1]

    # Do a DNS lookup
    destAddr = gethostbyname(hostname)
    s = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)
    # Only make the receive timeout
    timeval = struct.pack('ll', TIMEOUT, 0)
    s.setsockopt(SOL_SOCKET, SO_RCVTIMEO, timeval)
    s.bind(('', 0))

    types = ["type", "code", "checksum", "packet_id", "seq_number"]

    pkt = build_echo_request()
    reply = -1
    addr = ''

    for ttl in range(1, MAX_HOPS+1):
        s.setsockopt(IPPROTO_IP, IP_TTL, ttl)
        print(f'{ttl}.\t', end="")

        for i in range(1, NUM_OF_PROBES + 1):
            try:
                startTime = time.time()

                s.sendto(pkt, (destAddr, random.choice(range(33434, 33535))))
                packed, sender = s.recvfrom(1024)

                print(f'{round(time.time() - startTime, 3)} ms\t', end="")

                addr = sender[0]
                unpacked = struct.unpack('!BBHHH', packed[20:28])
                data = dict(zip(types, unpacked))

                reply = data['type']
                if reply == ICMP_ECHO_REPLY:
                    break

            except:
                print('*\t', end="")
                pass

        print(f'{addr}')

        if reply == ICMP_ECHO_REPLY:
            break
    s.close()


if __name__ == "__main__":
    main()
