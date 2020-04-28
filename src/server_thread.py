import threading
from btcp.server_socket import BTCPServerSocket

class ServerThread(threading.Thread):
    def __init__(self, window, timeout):
        threading.Thread.__init__(self)
        self.socket = BTCPServerSocket(window, timeout)

    def run(self):
        self.socket.accept()
        self.socket.close()