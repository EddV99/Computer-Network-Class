from socket import *
import re
import logging
import signal
from optparse import OptionParser
import sys

# set up logging
logging.basicConfig(level=logging.DEBUG)


def ctrl_c_pressed(signal, frame):
    """signal handler for pressing ctrl-c"""
    sys.exit(0)


def valid_url(url):
    """checks if the url is valid.

    The regex is kind of complicated, here are the lines explained
        1) matches 'http://'
        2) the host name "www.jasdf.234asjfa.com" or "123.123.123.123"
        3) port number ":123"
        4) "/" or "/dir1/dir2/..." or "/?search=..." or "/dir1/.../?search=.."

    Line 3 and 4 are optional
    source: https://www.rfc-editor.org/rfc/rfc1738 (section 3)
    """
    regex = br'http://'\
            br'([a-zA-Z0-9.]+\.[a-zA-Z]+[a-zA-Z0-9]*|\d+\.\d+\.\d+\.\d+)'\
            br'(:\d+)?'\
            br'((/)|(/[^/;?]+)+|(/[^/;?]+)+(\?[^/;?]+)|(/)(\?[^/;?]+))?'
    logging.debug(f'regex is {regex}')
    url_pattern = re.compile(regex)

    if re.match(url_pattern, url) is None:
        return False

    return True


def valid_request_line(request_line: bytes):
    """check if a request line is properly formatted."""

    split_request = request_line.split(b' ')

    if len(split_request) != 3:
        return False

    # check if method is valid
    method = split_request[0]
    if not (method == b'GET' or method == b'HEAD' or method == b'POST'):
        return False
    logging.debug('<METHOD> is valid')

    # check if url is valid
    url = split_request[1]
    if not valid_url(url):
        return False
    logging.debug('<URL> is valid')

    # check if http version is valid
    http_version = split_request[2]
    if http_version != b'HTTP/1.0':
        return False

    logging.debug('<HTTP VERSION> is valid')
    return True


def valid_header(header: bytes):
    """check if a header is properly formatted"""
    split_header = header.split(b' ')
    logging.debug(f'header {split_header}')
    if len(split_header) != 2:
        logging.debug(f'bad header {split_header}')
        return False

    first_half = split_header[0]
    logging.debug(f'header last {first_half[-1:]}')
    if first_half[-1:] != b':':
        return False

    return True


def valid_request(request: bytes):
    """check if a request from a client to proxy(this) is valid"""
    lines = request.split(b'\r\n')
    first_line = True
    for line in lines:
        if line:  # skip empty line
            logging.info(f'line is {line}')
            if first_line:
                first_line = False
                if not valid_request_line(line):
                    return False
            else:
                if (not valid_header(line)):
                    return False
    return True


def get_method(request: bytes):
    """get the method from the request line"""
    lines = request.split(b'\r\n')
    first_line = lines[0]
    method = first_line.split(b' ')[0]
    logging.debug(f'get_method returned {method}')
    return method


def get_hostname_port_and_path(request: bytes):
    """get the hostname, port and path from the request line

    If port is None set to 80 as default
    If path is None set to / as default
    return:
        A tuple containing hostname, port and path (hostname, port, path)
    """
    regex = br'http://'\
            br'([a-zA-Z0-9.]+\.[a-zA-Z]+[a-zA-Z0-9]*|\d+\.\d+\.\d+\.\d+)'\
            br'(:\d+)?'\
            br'(/[^/;?]+(?:/[^/;?]+)*|/[^/;?]+(?:/[^/;?]+)*\?[^/;?]+|/\?[^/;?]+|/)?'
    url_pattern = re.compile(regex)

    lines = request.split(b'\r\n')
    first_line = lines[0]
    url = first_line.split(b' ')[1]

    match = url_pattern.match(url)
    host = match.group(1)
    port = match.group(2)
    path = match.group(3)

    if not port:
        port = 80
    else:
        port = int(port[1:])  # regex included ':'

    if not path:
        path = b'/'

    return (host, port, path)


def get_headers(request: bytes):
    """get the headers from a request

    Return:
        A list with the headers
    """
    lines = request.split(b'\r\n')
    headers = []
    firstLine = True

    for line in lines:
        if (not firstLine) and line:
            headers.append(line)
        else:
            firstLine = False

    return headers


def create_request(host, path, headers):
    """create a new request

    For this assignment, ensure the request has one "Connection:" header with
    the value "close".

    Return:
        A byte string with the new request
    """
    request = b'GET' + b' ' + path + b' HTTP/1.0\r\n'

    header = b'Host: ' + host + b'\r\n'  # maybe add port here?
    request = request + header

    header = b'Connection: close\r\n'
    request = request + header

    for h in headers:
        name = h.split(b' ')[0]
        if name != b'Host:' or name != b'Connection:':
            header = h + b'\r\n'
            # request.append(header)
            request = request + header

    request = request + b'\r\n'
    logging.debug(f'created request is {request}')

    return request


def send_request(host, port, request):
    with socket(AF_INET, SOCK_STREAM) as client_socket:
        client_socket.connect((host, port))
        client_socket.send(request)
        response = client_socket.recv(2048)

    return response


# start of program execution
logging.info('start: parsing args')

# parse out the command line server address and port number to listen to
parser = OptionParser()
parser.add_option('-p', type='int', dest='serverPort')
parser.add_option('-a', type='string', dest='serverAddress')
(options, args) = parser.parse_args()

logging.info('end: parsing args')
logging.debug(f'parsed: options: {options}, args: {args}')

port = options.serverPort
address = options.serverAddress
if address is None:
    address = 'localhost'
if port is None:
    port = 2100

logging.debug(f'port: {port}, address: {address}')

# set up signal handling (ctrl-c)
signal.signal(signal.SIGINT, ctrl_c_pressed)

with socket(AF_INET, SOCK_STREAM) as listen_socket:
    # important for autograder
    listen_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    # bind the listening socket to an address and port
    listen_socket.bind((address, port))
    # tell OS we are listening with this socket
    listen_socket.listen()

    # keep the proxy server running and accepting connections
    while True:
        client_socket, client_addr = listen_socket.accept()
        request = client_socket.recv(2048)

        if not valid_request(request):
            logging.warning('uh oh bad request')
            client_socket.send(b'400 Bad request\r\n\r\n')
            client_socket.close()
            continue
        if get_method(request) != b'GET':
            logging.warning('uh oh not implemented')
            client_socket.send(b'501 Not implemented\r\n\r\n')
            client_socket.close()
            continue

        host, port, path = get_hostname_port_and_path(request)
        logging.info(f'host is {host}')
        logging.info(f'port is {port}')
        logging.info(f'path is {path}')

        headers = get_headers(request)

        request_for_origin_server = create_request(host, path, headers)

        response = send_request(host, port, request_for_origin_server)

        client_socket.send(response)
        client_socket.close()
