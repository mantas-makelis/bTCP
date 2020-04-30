from stoppable_thread import StoppableThread
from btcp.server_socket import BTCPServerSocket


class ServerThread(StoppableThread):
    """ Simulates the server with a single socket """

    def __init__(self, window, timeout):
        super().__init__()
        self.socket = BTCPServerSocket(window, timeout)

    def run(self):
        """ The main loop of the server """
        self.socket.accept()

        file_bytes = self.socket.recv()
        print(file_bytes.decode('utf-8'))

        self.socket.close()
