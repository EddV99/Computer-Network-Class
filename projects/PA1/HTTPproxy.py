from socket import *
import threading
import time
import re
import signal
from optparse import OptionParser
import sys

# global variables ------------------------------------------------
cache = {}
cache_enabled = False
blocklist = []
blocklist_enabled = False


def ctrl_c_pressed(signal, frame):
    """signal handler for pressing ctrl-c"""
    sys.exit(0)


def get_last_modified(obj: bytes) -> bytes:
    """get the Last Modified value from the obj

    Args:
        obj - the obj to get the header from
    Returns:
        the value of the header
    """
    headers = get_headers(obj)

    for header in headers:
        split = header.split(b' ')
        name = split[0]
        if name == b'Last-Modified:':
            return header[header.find(b':') + 2:]


def update_cache(key: bytes, data: bytes):
    """update the cache with a new or updated value
    Args:
        key - the key to update the cache with
        data - the data for the cooresponding key
    Returns:
        None
    """
    global cache
    cache[key] = data


def get_obj_from_cache(key: bytes) -> bytes:
    """check if an obj is cached and return it
    Args:
       key - key to get an obj from
    Returns:
        the obj or None if not in cache
    """
    global cache

    if key in cache:
        return cache[key]
    return None


def caching(host: bytes, path: bytes, port: int, headers: [bytes], client_socket):
    """check if the requested obj is in the cache, if not request it and update
    the cache. If in the cache, check if we have the most up-to-date version of
    the obj, update if needed. Also finish connections here.

    Args:
        host - the host of the wanted obj
        path - the path to the wanted obj
        headers - the headers from the request
        client_socket - the client socket to use when finishing connections
    Returns:
        None
    """
    requested_obj = host + path
    cached_obj = get_obj_from_cache(requested_obj)

    if cached_obj is None:
        request_for_origin_server = create_request(host, path, headers)
        response = send_request(host.decode(), port, request_for_origin_server)

        lines = response.split(b'\r\n')
        request_line = lines[0]
        # only cache obj with 200 OK
        if b'200 OK' in request_line:
            update_cache(requested_obj, response)
        client_socket.send(response)
        client_socket.close()
    else:
        # we have an obj, but don't know if up-to-date
        # so send a conditional get
        request_for_origin_server = create_request(host, path, headers, True,
                                                   get_last_modified(cached_obj))
        response = send_request(host.decode(), port, request_for_origin_server)
        lines = response.split(b'\r\n')
        request_line = lines[0]
        if b'304 Not Modified' in request_line:
            client_socket.send(cached_obj)
            client_socket.close()
        else:
            # only cache obj with 200 OK
            if b'200 OK' in request_line:
                update_cache(requested_obj, response)
            client_socket.send(response)
            client_socket.close()


def uri_forbidden(uri) -> bool:
    """check the blocklist if our uri is forbidden
    Args:
        uri - the uri to check
    Returns:
        True if forbidden, false otherwise
    """
    global blocklist

    for blocked in blocklist:
        if blocked in uri:
            return True

    return False


def control_interface(command: bytes) -> bool:
    """a control interface for the cache and blocklist.
    Args:
        command - the command to do
    Returns:
        True if we used the interface, false otherwise
    """
    global cache
    global cache_enabled
    global blocklist
    global blocklist_enabled

    if command == b'/proxy/cache/enable':
        cache_enabled = True
        return True
    elif command == b'/proxy/cache/disable':
        cache_enabled = False
        return True
    elif command == b'/proxy/cache/flush':
        cache.clear()
        return True
    elif command == b'/proxy/blocklist/enable':
        blocklist_enabled = True
        return True
    elif command == b'/proxy/blocklist/disable':
        blocklist_enabled = False
        return True
    elif b'/proxy/blocklist/add/' in command:
        split = command.split(b'/')
        block = split[len(split) - 1]
        blocklist.append(block)
        return True
    elif b'/proxy/blocklist/remove/' in command:
        split = command.split(b'/')
        block = split[len(split) - 1]
        blocklist.remove(block)
        return True
    elif command == b'/proxy/blocklist/flush':
        blocklist.clear()
        return True

    return False


def valid_url(url: bytes) -> bool:
    """checks if the url is valid.

    Args:
        url - the url to check if valid
    Returns:
        True if valid, False otherwise
    """

    # The regex is kind of complicated, here are the lines explained
    #    1) matches 'http://'
    #    2) the host name "www.jasdf.234asjfa.com" or "123.123.123.123"
    #    3) port number ":123"
    #    4) "/" or "/dir1/dir2/..." or "/?search=..." or "/dir1/.../?search=.."
    #
    # Line 3 and 4 are optional
    # source: https://www.rfc-editor.org/rfc/rfc1738 (section 3)
    regex = br'http://'\
            br'([a-zA-Z0-9.]+\.[a-zA-Z]+[a-zA-Z0-9-]*|[a-zA-Z][a-zA-Z0-9-]*|\d+\.\d+\.\d+\.\d+)'\
            br'(:\d+)?'\
            br'((/)|(/[^/;?]+)+|(/[^/;?]+)+(\?[^/;?]+)|(/)(\?[^/;?]+))'
    url_pattern = re.compile(regex)

    if re.match(url_pattern, url) is None:
        return False

    return True


def valid_request_line(request_line: bytes) -> bool:
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

    # check if url is valid
    url = split_request[1]
    if not valid_url(url):
        return False

    # check if http version is valid
    # valid only for specific version 1.0
    http_version = split_request[2]
    if http_version != b'HTTP/1.0':
        return False

    return True


def valid_header(header: bytes) -> bool:
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

    # valid if the first split ends with ':'
    header_name = split_header[0]
    if header_name[-1:] != b':':
        return False

    return True


def valid_request(request: bytes) -> bool:
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
            if first_line:
                first_line = False
                if not valid_request_line(line):
                    return False
            else:
                if not valid_header(line):
                    return False
    return True


def get_method(request_line: bytes) -> bytes:
    """get the method from the request line
    Args:
        request_line - extract method from
    Returns:
        The method as byte string
    """
    lines = request_line.split(b'\r\n')
    first_line = lines[0]
    method = first_line.split(b' ')[0]
    return method


def get_hostname_port_and_path(request: bytes) -> (bytes, int, bytes):
    """get the hostname, port and path from the request line

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

    # set default path
    if not path:
        path = b'/'

    if port:
        port = int(port[1:])

    return (host, port, path)


def get_headers(request: bytes) -> [bytes]:
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


def create_request(host: bytes, path: bytes, headers: bytes,
                   conditional: bool = False, date: bytes = b'') -> bytes:
    """create a new request

    For this assignment, ensure the request has one "Connection:" header with
    the value "close".

    Args:
        host - hostname
        path - path to put in request line
        headers - list of headers
        conditional - is this a conditional GET request (default False)
        date - date for the conditional GET request (default b'')
    Return:
        A byte string with the new request
    """
    request = b'GET' + b' ' + path + b' HTTP/1.0\r\n'

    header = b'Host: ' + host + b'\r\n'  # maybe add port here?
    request = request + header
    header = b'Connection: close\r\n'
    request = request + header

    if conditional:
        if date:
            header = b'If-Modified-Since: ' + date
        else:
            header = b'If-Modified-Since:'
        request = request + header

    for h in headers:
        name = h.split(b' ')[0]
        if name != b'Connection:' and name != b'Hosts:':
            header = h + b'\r\n'
            request = request + header

    request = request + b'\r\n\r\n'

    return request


def send_request(host: str, port: int, request: bytes) -> bytes:
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


def handle_client(client_socket, client_addr):
    """grab the client's request, send a request ourselves (proxy),
    send the respone back to the client

    Intended to be called in a new thread to allow concurrent users.

    Args:
        client_socket - the socket the client connected to
        client_addr - the address of the client
    Returns:
        None
    """
    global cache_enabled
    global blocklist_enabled

    # recieve the request from the client
    request = client_socket.recv(2048)
    timeout = time.time() + 30  # 30 second timeout
    while (b'\r\n\r\n' not in request) and (time.time() < timeout):
        request = request + client_socket.recv(2048)

    # check if the request is something we can handle
    if not valid_request(request):
        client_socket.send(b'HTTP/1.0 400 Bad Request\r\n\r\n')
        client_socket.close()
        return
    if get_method(request) != b'GET':
        client_socket.send(b'HTTP/1.0 501 Not Implemented\r\n\r\n')
        client_socket.close()
        return

    host, port, path = get_hostname_port_and_path(request)
    headers = get_headers(request)

    # might be a request to change some global settings
    if control_interface(path):
        client_socket.send(b'HTTP/1.0 200 OK\r\n\r\n')
        client_socket.close()
        return

    if blocklist_enabled:
        uri = b''
        if port:
            uri = host + b':' + bytes(str(port), 'utf-8')
        else:
            uri = host
        if uri_forbidden(uri):
            client_socket.send(b'HTTP/1.0 403 Forbidden\r\n\r\n')
            client_socket.close()
            return

    # if no port was given, default to 80
    if not port:
        port = 80

    if cache_enabled:
        caching(host, path, port, headers, client_socket)
    else:
        request_for_origin_server = create_request(host, path, headers)
        response = send_request(host.decode(), port, request_for_origin_server)

        client_socket.send(response)
        client_socket.close()


# start of program execution ------------------------------------------

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
        # accept and let thread handle connection
        client_socket, client_addr = listen_socket.accept()
        threading.Thread(target=handle_client, args=(
            client_socket, client_addr)).start()
