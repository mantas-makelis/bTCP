# By Mantas Makelis (s1007870)

from socket import *
from pathlib import Path


def encode(message: str):
    return message.encode('utf-8')


def decode(message: bytes):
    return message.decode('utf-8')


serverPort = 20000
size = 1024
correctGreeting = 'hello'

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(1)

print('The echo server is ready to receive')
while 1:
    conn, address = serverSocket.accept()
    print(address, 'Processing client')

    try:
        cmd = conn.recv(size)

        while cmd:
            if decode(cmd) == correctGreeting:
                break
            print(address, 'Wrong greeting received')
            cmd = conn.recv(size)

        print(address, 'Relationship established')
        conn.send(cmd)
        cmd = conn.recv(size)

        while cmd:
            issuedCommand = decode(cmd)

            if issuedCommand == 'bye':
                print(address, 'Ending connection ')
                conn.send(cmd)
                break

            elif issuedCommand.startswith('get'):
                file_name = issuedCommand[4:]  # if string is shorter than 4 i.e. only 'get' - it become an empty string
                print(address, 'Searching for', file_name)

                file = Path(file_name)
                if file.is_file():
                    print(address, 'File found: ', file_name)
                    conn.send(encode('file_content'))
                else:
                    print(address, 'File not found: ', file_name)
                    conn.send(encode('file_not_found'))

            else:
                print(address, 'Unknown command issued: ', issuedCommand)
                conn.send(encode('cannot_understand'))

            cmd = conn.recv(size)

    except error:
        print('Exception occurred')
        pass

    print(address, 'Client closed')
    conn.close()
