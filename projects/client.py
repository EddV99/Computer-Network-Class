from socket import *


with socket(AF_INET, SOCK_STREAM) as skt:
    skt.connect(('localhost', 2100))
    skt.send(b'GET http://www.cool.com:99/dir/text.txt HTTP/1.0\r\nYes: no\r\n\r\n')
    response = skt.recv(2048)
    print(response[:-1])
