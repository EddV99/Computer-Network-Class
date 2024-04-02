from socket import *
import time

while(True):
    uri = input("enter uri: ")
     # http://www.flux.utah.edu/pics/campus-fall.jpg 
    with socket(AF_INET, SOCK_STREAM) as skt:
        skt.connect(('localhost', 2100))
        skt.send(b'GET ' + b'http://' + bytes(uri, 'utf-8') + b' HTTP/1.0\r\n\r\n')
        
        got = skt.recv(2048)
        response = got
        while len(got) > 0:
            got = skt.recv(2048)
            response = response + got

        print(response)
