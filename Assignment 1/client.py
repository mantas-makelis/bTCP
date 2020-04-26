# By Mantas Makelis (s1007870)

import socket
import time


def encode(msg: str):
    return msg.encode('utf-8')


def decode(msg: bytes):
    return msg.decode('utf-8')


serverPort = 20000
size = 1024

s = socket.create_connection(('localhost', serverPort))

client = 'Client: '
server = 'Server: '

message = 'hoi server'
print(client, message)
s.sendall(encode(message))
time.sleep(1)

message = 'hey, are you there?'
print(client, message)
s.sendall(encode(message))
time.sleep(1)

message = 'hello'
print(client, message)
s.sendall(encode(message))
time.sleep(1)

response = s.recv(size)
print(server, decode(response))
time.sleep(1)

message = 'how are you doing?'
print(client, message)
s.sendall(encode(message))
time.sleep(1)

response = s.recv(size)
print(server, decode(response))
time.sleep(1)

message = 'get not.found'
print(client, message)
s.sendall(encode(message))
time.sleep(1)

response = s.recv(size)
print(server, decode(response))
time.sleep(1)

message = 'get server.py'
print(client, message)
s.sendall(encode(message))
time.sleep(1)

response = s.recv(size)
print(server, decode(response))
time.sleep(1)

message = 'thanks!'
print(client, message)
s.sendall(encode(message))
time.sleep(1)

response = s.recv(size)
print(server, decode(response))
time.sleep(1)

response = s.recv(size)
print(server, decode(response))
time.sleep(1)

message = 'bye'
print(client, message)
s.sendall(encode(message))
time.sleep(1)

response = s.recv(size)
print(server, decode(response))
time.sleep(1)

s.close()
