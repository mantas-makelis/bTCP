# from socket import *
import socket
import os
import sys
import struct
import time
import select
import math
import array

ICMP_ECHO_REQUEST = 8
ICMP_TTL_EXCEEDED = 11
ICMP_ECHO_REPLY = 0
TIMEOUT  = 1
MAX_HOPS = 30
NUM_OF_PROBES = 3


def checksum(pkt):

    # Pad with zero byte
    if len(pkt) % 2 == 1:
        pkt += "\0"

    # split into 16-bit substrings
    stringarray = array.array("H", pkt)

    # sum 
    currentsum = sum(stringarray)

    # carry the most significant bits over to the right (https://en.wikipedia.org/wiki/Internet_Control_Message_Protocol#Datagram%20structure)
    currentsum = (currentsum >> 16) + (currentsum & 0xffff)

    # carry once more in case we spilled over
    currentsum += (currentsum >> 16)

    # get the 1's complement
    currentsum = ~currentsum & 0xffff 

    return currentsum
                                                                    
# builds an echo request message with correct checksum
def build_echo_request():

    # Return the current process id
    ID = os.getpid() & 0xffff  

    # Construct and pack a header with a dummy checksum
    header = struct.pack("bbHHH",
                         ICMP_ECHO_REQUEST,  # type (byte)
                         0,                  # code (byte)
                         0,                  # checksum (halfword, 2 bytes)
                         ID,                 # ID (halfword)
                         1)                  # sequence (halfword)

    # Pack the current time in "d" = (float or double) format
    data = struct.pack("d", time.time())

    # Calculate the checksum on the data and the header with the 0 checksum
    myChecksum = checksum(header + data)

    # Construct a new header containing the checksum
    header = struct.pack("bbHHH",
                        ICMP_ECHO_REQUEST,
                        0,
                        myChecksum,
                        ID,
                        1)

    # Construct new message
    message = header + data 
    # If you sum the 16-bit strings that make up this message, the sum is zero
    # This is because the checksum is the 1's complement of the sum of the packet WITHOUT a checksum 

    return message

# main method
def main():
    if len(sys.argv) != 2:
        print ("USEAGE: \npython traceroute.py hostname")
        exit(0)

    # Get the target hostname from the command line arguments
    hostname = sys.argv[1]

    # Do a DNS lookup to get the associated IPv4 address
    destAddr = socket.gethostbyname(hostname)

    # Create a new raw ICMP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)

    # Set the timeout on the socket to the specified value
    s.settimeout(TIMEOUT)

    # Create a new echo request
    pkt = build_echo_request()

    # pack the timeout value
    timeval = struct.pack('ll', TIMEOUT, 0)

    # Set the socket receive timeout to the correct length
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, timeval)

    # loop over time-to-live
    for ttl in range(1, MAX_HOPS+1):

        # set the TTL on the socket 
        s.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, struct.pack('I', ttl))

        # loop over probes
        for i in range(1,NUM_OF_PROBES+1):
            try:
                # Start timer
                starttime = time.time()

                # Send packet
                s.sendto(pkt,(destAddr,0))

                # Receive packet
                recPacket, addr = s.recvfrom(1024)

                # Stop timer
                endtime = time.time()

                # Extract type of the received message 
                # The first 20 bytes are IPv4 stuff (https://en.wikipedia.org/wiki/Internet_Control_Message_Protocol#Datagram%20structure)
                # We are only interested in the ICMP type, so we ignore them
                # After the first 20 bytes, the first byte contains the type
                request_type = recPacket[20]

                # If this is the first probe
                if i == 1:
                    # Format ip for printing
                    ip_of_reply = addr[0].ljust(20)

                    # Get and format FQDN for printing
                    fqdn_of_reply = socket.getfqdn(addr[0]).ljust(50)

                    # Print ip and probe
                    print(ip_of_reply,fqdn_of_reply,end = " ")

                # Always print RTT
                print(round((endtime-starttime)*1000,2), end = "\t ")

                # Finish with a newline
                if i == 3:
                    print()

                    # If it is a echo reply message, break out of the loop, because we are DONE
                    if request_type == ICMP_ECHO_REPLY:
                        return

            except socket.timeout:
                print(71*" ",NUM_OF_PROBES*("*".ljust(4)+"\t"), end = "\t")
                print ()
                break

if __name__ == "__main__":
    main()
