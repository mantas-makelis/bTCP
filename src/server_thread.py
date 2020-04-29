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

        while not self._stopevent.isSet():
            self.socket.idle()

        self.socket.close()