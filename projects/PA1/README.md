# HTTP Proxy
A simple HTTP proxy that recieves requests then sends requests and recieves responses from the origin server. 
Can handle multiple requests at the same time and uses a cache for performance. 
The proxy also features domain blocking.
## Usage
To start the proxy server:

`python HTTPproxy.py`
### Arguments
- `-a` `interface` (defaults to localhost)
- `-p` `portnumber` (defaults to 2100)
