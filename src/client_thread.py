from btcp.client_socket import BTCPClientSocket
from threading import Thread

from btcp.enums import State


class ClientThread(Thread):
    """ Simulates the client with a single socket """

    def __init__(self, window: int, timeout: int, file_name: str, show_prints: bool = False):
        super().__init__()
        self.socket = BTCPClientSocket(window, timeout, show_prints)
        self.file_name = file_name

    def run(self):
        """ The main loop of the client """
        self.socket.connect()
        if self.socket.state is State.CONN_EST:
            self.socket.send(self.file_name)
            self.socket.disconnect()
        self.socket.close()

    def get_sent_file(self):
        with open(self.file_name, 'rb') as f:
            return f.read()
