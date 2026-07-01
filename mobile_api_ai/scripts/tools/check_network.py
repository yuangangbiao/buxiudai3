import socket

print("=== 检查网络连通性 ===")
print()

# 检查本机IP
hostname = socket.gethostname()
try:
    local_ip = socket.gethostbyname(hostname)
    print(f"本机 hostname: {hostname}")
    print(f"本机 IP: {local_ip}")
except Exception as e:
    print(f"无法获取本机IP: {e}")

print()

# 检查几个可能的 container_center 端口
ports_to_check = [
    ('', 5002, 'container_center (localhost)'),
    ('', 5003, 'wechat_server (localhost)'),
]

for target_host, port, label in ports_to_check:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        if target_host:
            result = sock.connect_ex((target_host, port))
        else:
            result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        status = '监听中' if result == 0 else f'不可达({result})'
        print(f"{label}: {status}")
    except Exception as e:
        sock.close()
        print(f"{label}: 错误({e})")

print()
print("=== 请确认 ===")
print("桌面端 main.py 发送工单时，日志显示发送成功还是失败？")
print("桌面端是否和 container_center_api 在同一台机器？")
