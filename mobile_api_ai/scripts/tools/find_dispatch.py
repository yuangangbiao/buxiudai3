import psutil
import os
import time
import subprocess
import socket

os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

print("=== 查找调度中心进程 ===")
found = False
for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
    try:
        cmdline = proc.info['cmdline']
        if not cmdline:
            continue
        cmd_str = ' '.join(cmdline)
        if 'dispatch_center.py' in cmd_str and '5003' not in cmd_str:
            # Filter out launcher which has both container_center and dispatch_center
            continue
        if 'dispatch_center' in cmd_str and 'python' in cmd_str.lower():
            print(f"PID: {proc.info['pid']}, Name: {proc.info['name']}")
            print(f"  CMD: {cmd_str[:200]}")
            print(f"  Started: {time.ctime(proc.info['create_time'])}")
            found = True
    except Exception as e:
        print(f"[find_dispatch] 遍历进程失败: {e}")

if not found:
    print("未找到直接运行的 dispatch_center.py 进程")
    
# Also find by port
print("\n=== 检查端口 5003 ===")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
r = s.connect_ex(('127.0.0.1', 5003))
s.close()
if r == 0:
    print("5003 端口被占用")
else:
    print("5003 端口空闲")

print("\nDone")
