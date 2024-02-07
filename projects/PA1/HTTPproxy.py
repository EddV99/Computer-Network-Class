from socket import *
import time
import re
import logging
import signal
from optparse import OptionParser
import sys

# set up logging
# logging.basicConfig(level=logging.DEBUG)


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

    Args:
        url - the url to check if valid
    Returns:
        True if valid, False otherwise
    """
    regex = br'http://'\
            br'([a-zA-Z0-9.]+\.[a-zA-Z]+[a-zA-Z0-9-]*|[a-zA-Z][a-zA-Z0-9-]*|\d+\.\d+\.\d+\.\d+)'\
            br'(:\d+)?'\
            br'((/)|(/[^/;?]+)+|(/[^/;?]+)+(\?[^/;?]+)|(/)(\?[^/;?]+))'
    url_pattern = re.compile(regex)

    if re.match(url_pattern, url) is None:
        return False

    return True


def valid_request_line(request_line: bytes):
    """check if a request line is properly formatted.
    Args:
        request_line - the request line to check if valid
    Returns:
        True if valid, False otherwise
    """

    split_request = request_line.split(b' ')
    # should be only 3 parts <method> <url> <version>
    if len(split_request) != 3:
        return False

    # check if method is valid
    method = split_request[0]
    if not (method == b'GET' or method == b'HEAD' or method == b'POST'):
        return False
    # logging.debug('<METHOD> is valid')

    # check if url is valid
    url = split_request[1]
    if not valid_url(url):
        return False
    # logging.debug('<URL> is valid')

    # check if http version is valid
    # valid only for specific version 1.0
    http_version = split_request[2]
    if http_version != b'HTTP/1.0':
        return False

    # logging.debug('<HTTP VERSION> is valid')
    return True


def valid_header(header: bytes):
    """check if a header is properly formatted

    just check if the header in form
        <name>: <rest>
    we are just worried about the "<name>:" part

    Args:
        header - the header to check if valid
    Returns:
        True if valid, False otherwise

    """
    split_header = header.split(b' ')
    # logging.debug(f'header {split_header}')

    header_name = split_header[0]
    # logging.debug(f'header last {first_half[-1:]}')
    if header_name[-1:] != b':':
        return False

    return True


def valid_request(request: bytes):
    """check if a request from a client to proxy(this) is valid

    Args:
        request - the request to check if valid
    Returns:
        True if valid, False otherwise
    """
    lines = request.split(b'\r\n')
    first_line = True
    for line in lines:
        if line:  # skip empty line
            # logging.info(f'line is {line}')
            if first_line:
                first_line = False
                if not valid_request_line(line):
                    return False
            else:
                if not valid_header(line):
                    return False
    return True


def get_method(request_line: bytes):
    """get the method from the request line
    Args:
        request_line - extract method from
    Returns:
        The method as byte string
    """
    lines = request_line.split(b'\r\n')
    first_line = lines[0]
    method = first_line.split(b' ')[0]
    # logging.debug(f'get_method returned {method}')
    return method


def get_hostname_port_and_path(request: bytes):
    """get the hostname, port and path from the request line

    If port is None set to 80 as default
    If path is None set to / as default
    Args:
        request - the request to extract host, port, and path from
    Returns:
        A tuple containing hostname, port and path (hostname, port, path)
    """
    regex = br'http://'\
            br'([a-zA-Z0-9.]+\.[a-zA-Z]+[a-zA-Z0-9-]*|[a-zA-Z][a-zA-Z0-9-]*|\d+\.\d+\.\d+\.\d+)'\
            br'(:\d+)?'\
            br'(/[^/;?]+(?:/[^/;?]+)*|/[^/;?]+(?:/[^/;?]+)*\?[^/;?]+|/\?[^/;?]+|/)'

    url_pattern = re.compile(regex)

    lines = request.split(b'\r\n')
    first_line = lines[0]
    url = first_line.split(b' ')[1]

    match = url_pattern.match(url)
    host = match.group(1)
    port = match.group(2)
    path = match.group(3)

    # logging.debug(f'host is {host}')
    # logging.debug(f'port is {port}')
    # logging.debug(f'path is {path}')

    # set default port
    if not port:
        port = 80
    else:
        port = int(port[1:])  # regex included ':'

    # set default path
    if not path:
        path = b'/'

    return (host, port, path)


def get_headers(request: bytes):
    """get the headers from a request
    Args:
        request - extract headers from
    Returns:
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

    Args:
        host - hostname
        path - path to put in request line
        headers - list of headers
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
        if name != b'Connection:' and name != b'Hosts:':
            header = h + b'\r\n'
            request = request + header

    request = request + b'\r\n'
    # logging.debug(f'created request is {request}')

    return request


def send_request(host, port, request):
    """send a request to some server
    Args:
        host - hostname (should be a string)
        port - port number to connect to
        request - the request to send
    Returns:
        The response from the server we just sent a request to (as is)
    """
    with socket(AF_INET, SOCK_STREAM) as client_socket:
        # empty means localhost
        if host == 'localhost':
            host = ''

        client_socket.connect((host, port))
        client_socket.send(request)
        response = b''
        buf = client_socket.recv(2048)
        # continue recieving until nothing comes in
        while buf:
            response = response + buf
            buf = client_socket.recv(2048)

    return response


# start of program execution

# parse out the command line server address and port number to listen to
parser = OptionParser()
parser.add_option('-p', type='int', dest='serverPort')
parser.add_option('-a', type='string', dest='serverAddress')
(options, args) = parser.parse_args()

port = options.serverPort
address = options.serverAddress
if address is None:
    address = 'localhost'
if port is None:
    port = 2100

# logging.debug(f'port: {port}, address: {address}')

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

        # request should end in \r\n\r\n
        # if not timeout
        request = client_socket.recv(2048)
        timeout = time.time() + 30  # 30 second timeout
        while b'\r\n\r\n' not in request and (time.time() < timeout):
            request = request + client_socket.recv(2048)

        if not valid_request(request):
            # logging.warning('uh oh bad request')
            client_socket.send(b'HTTP/1.0 400 Bad Request\r\n\r\n')
            client_socket.close()
            continue
        if get_method(request) != b'GET':
            # logging.warning('uh oh not implemented')
            client_socket.send(b'HTTP/1.0 501 Not Implemented\r\n\r\n')
            client_socket.close()
            continue

        host, port, path = get_hostname_port_and_path(request)
        # logging.debug(f'host is {host}')
        # logging.debug(f'port is {port}')
        # logging.debug(f'path is {path}')

        headers = get_headers(request)

        request_for_origin_server = create_request(host, path, headers)

        response = send_request(host.decode(), port, request_for_origin_server)

        client_socket.send(response)
        client_socket.close()
