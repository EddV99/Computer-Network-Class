from socket import *

with socket(AF_INET, SOCK_STREAM) as listen_skt:
    listen_skt.bind(('', 1234))
    listen_skt.listen()

    while True:
        skt, client_addr = listen_skt.accept()
        request = skt.recv(2048)
        print(request)
        skt.send(request.upper())
        skt.close()
