# HTTP Proxy
A simple HTTP proxy that recieves requests then sends requests and recieves responses from the origin server. 
Can handle multiple requests at the same time and uses a cache for performance. 
The proxy also features domain blocking. The proxy also features domain blocking and is 
controlled through the use of certain GET requests.

## Usage
To start the proxy server:

`python HTTPproxy.py`
### Arguments
- `-a` `interface` (defaults to localhost)
- `-p` `portnumber` (defaults to 2100)

### GET Commands
The proxy has cache and domain blocking capabilities that are controlled using GET requests.

- `/proxy/cache/enable`

   Enable the proxy’s cache; if it is already enabled, do nothing. This request does not affect the contents of the cache. Future requests will consult the cache.

- `/proxy/cache/disable`

  Disable the proxy’s cache; if it is already disabled, do nothing. This request does not affect the contents of the cache. Future requests will not consult the cache.
  
- `/proxy/cache/flush`
  
    Flush (empty) the proxy’s cache. This request does not affect the enabled/disabled state of the cache.

- `/proxy/blocklist/enable`
  
    Enable the proxy’s blocklist; if it is already enabled, do nothing. This request does not affect the contents of the blocklist. Future requests will consult the blocklist.

- `/proxy/blocklist/disable`
  
    Disable the proxy’s blocklist; if it is already disabled, do nothing. This request does not affect the contents of the blocklist. Future requests will not consult the blocklist.

- `/proxy/blocklist/add/<string>`
  
    Add the specified string to the proxy’s blocklist; if it is already in the blocklist, do nothing.

- `/proxy/blocklist/remove/<string>`
  
    Remove the specified string from the proxy’s blocklist; if it is not already in the blocklist, do nothing.

- `/proxy/blocklist/flush`
  
    Flush (empty) the proxy’s blocklist. This request does not affect the enabled/disabled state of the blocklist.

