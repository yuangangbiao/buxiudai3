import psutil
import os

os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

# Find and kill dispatch center process (port 5003)
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
        if ('dispatch_center.py' in cmdline or 'standalone_dispatch_server.py' in cmdline) and '5003' in cmdline:
            print(f"Killing dispatch center: PID={proc.info['pid']}")
            proc.kill()
    except Exception as e:
        print(f"[restart_dispatch] 处理进程失败: {e}")

print("Done")
