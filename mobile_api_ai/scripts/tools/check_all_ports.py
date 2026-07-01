import socket
for port in [5002, 5003, 5004, 5008]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    r = s.connect_ex(('127.0.0.1', port))
    s.close()
    status = 'busy' if r == 0 else 'free'
    service = {5002: 'container_center', 5003: 'dispatch_center', 5004: '?', 5008: 'app'}
    print(f'{port} ({service.get(port, "?")}): {status}')
