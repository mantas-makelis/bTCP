from stoppable_thread import StoppableThread
from btcp.client_socket import BTCPClientSocket


class ClientThread(StoppableThread):
    """ Simulates the client with a single socket """

    def __init__(self, window, timeout):
        super().__init__()
        self.socket = BTCPClientSocket(window, timeout)

    def run(self):
        """ The main loop of the client """
        self.socket.connect()

        while not self._stopevent.isSet():
            continue

        self.socket.close()