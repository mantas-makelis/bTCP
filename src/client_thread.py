import threading
from btcp.client_socket import BTCPClientSocket

class ClientThread(threading.Thread):
    def __init__(self, window, timeout):
        threading.Thread.__init__(self)
        self.socket = BTCPClientSocket(window, timeout)

    def run(self):
        self.socket.connect()
        self.socket.close()