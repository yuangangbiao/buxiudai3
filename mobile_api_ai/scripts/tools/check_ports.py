import socket

s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
r1 = s1.connect_ex(('127.0.0.1', 5003))
s1.close()
print(f'5003 port: {"busy" if r1 == 0 else "free"}')

s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
r2 = s2.connect_ex(('127.0.0.1', 5004))
s2.close()
print(f'5004 port: {"busy" if r2 == 0 else "free"}')
