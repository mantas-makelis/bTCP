#!/usr/local/bin/python3

import argparse
from btcp.constants import *
from btcp.server_socket import BTCPServerSocket

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--window", help="Define bTCP window size", type=int, default=100)
    parser.add_argument("-t", "--timeout", help="Define bTCP timeout in milliseconds", type=int, default=100)
    parser.add_argument("-o", "--output", help="Where to store the file", default="output.file")
    args = parser.parse_args()

    # Create a bTCP server socket
    self.socket = BTCPServerSocket(args.window, args.timeout)

    # TODO Write your file transfer server code here using your BTCPServerSocket's accept, and recv methods.
    while 1:
        # Wait for connection
        self.socket.accept()  # conn, addr = 

        # Clean up any state
        self.socket.close()


main()
