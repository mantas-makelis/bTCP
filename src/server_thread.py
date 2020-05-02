import os

from btcp.server_socket import BTCPServerSocket
from stoppable_thread import StoppableThread


class ServerThread(StoppableThread):
    """ Simulates the server with a single socket """

    def __init__(self, window, timeout):
        super().__init__()
        self.socket = BTCPServerSocket(window, timeout)

    def run(self):
        """ The main loop of the server """
        self.socket.accept()

        file_bytes = self.socket.recv()

        with open('src/inputs/output.file', 'w') as f:
            output = file_bytes.decode('utf-8')
            output = os.linesep.join([s for s in output.splitlines() if s])
            f.write(output)

        self.socket.close()
