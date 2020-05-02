from btcp.client_socket import BTCPClientSocket
from stoppable_thread import StoppableThread


class ClientThread(StoppableThread):
    """ Simulates the client with a single socket """

    def __init__(self, window, timeout):
        super().__init__()
        self.socket = BTCPClientSocket(window, timeout)

    def run(self):
        """ The main loop of the client """
        self.socket.connect()

        with open('inputs/input.file', 'rb') as f:
            file_bytes = f.read()
        self.socket.send(file_bytes)

        self.socket.disconnect()

        self.socket.close()
