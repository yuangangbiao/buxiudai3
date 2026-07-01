import socket, errno

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = s.connect_ex(('127.0.0.1', 5003))
print(f'Port 5003 connect result: {result} (0=success)')
s.close()

import http.client
try:
    c = http.client.HTTPConnection('127.0.0.1', 5003, timeout=5)
    c.request('GET', '/api/dispatch-center/')
    r = c.getresponse()
    print(f'Status: {r.status}')
    data = r.read()
    print(f'Body length: {len(data)}')
    print(f'First 200 bytes: {data[:200]}')
except Exception as e:
    print(f'Error: {e}')
