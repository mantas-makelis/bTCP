from btcp.client_socket import BTCPClientSocket
from threading import Thread


class ClientThread(Thread):
    """ Simulates the client with a single socket """

    def __init__(self, window, timeout, show_prints):
        super().__init__()
        self.socket = BTCPClientSocket(window, timeout, show_prints)
        self.sent_bytes = b''

    def run(self):
        """ The main loop of the client """
        self.socket.connect()
        with open('src/inputs/output.file', 'rb') as f:
            self.sent_bytes = f.read()
        self.socket.send(self.sent_bytes)
        self.socket.disconnect()
        self.socket.close()

    def get_sent_file(self):
        return self.sent_bytes
