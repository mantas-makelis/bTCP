from btcp.enums import State
from btcp.server_socket import BTCPServerSocket
from threading import Thread


class ServerThread(Thread):
    """ Simulates the server with a single socket """

    def __init__(self, window: int, timeout: int, file_name: str, show_prints: bool = False):
        super().__init__()
        self.socket = BTCPServerSocket(window, timeout, show_prints)
        self.file_name = file_name

    def run(self):
        """ The main loop of the server """
        self.socket.accept()
        while self.socket.state is State.CONN_EST:
            recv_bytes = self.socket.recv()
            if recv_bytes:
                with open(self.file_name, 'ab') as f:
                    f.write(recv_bytes)
        self.socket.close()

    def get_recv_file(self):
        with open(self.file_name, 'rb') as f:
            return f.read()
