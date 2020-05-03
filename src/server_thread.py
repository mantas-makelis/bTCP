from btcp.server_socket import BTCPServerSocket
from threading import Thread


class ServerThread(Thread):
    """ Simulates the server with a single socket """

    def __init__(self, window, timeout):
        super().__init__()
        self.socket = BTCPServerSocket(window, timeout)
        self.received_bytes = b''

    def run(self):
        """ The main loop of the server """
        self.socket.accept()
        self.received_bytes = self.socket.recv()
        with open('src/inputs/output.file', 'wb') as f:
            f.write(self.received_bytes)
        self.socket.close()

    def get_recv_file(self):
        return self.received_bytes
