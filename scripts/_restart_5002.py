# -*- coding: utf-8 -*-
"""重启5002服务脚本"""
import subprocess
import time
import os

PYTHON = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe"
APP_PATH = r"d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center_api.py"

def main():
    # 1. 找进程
    result = subprocess.run(
        ["powershell", "-Command", "Get-NetTCPConnection -LocalPort 5002 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess"],
        capture_output=True,
        text=True
    )
    pids = [int(p.strip()) for p in result.stdout.strip().split('\n') if p.strip().isdigit()]
    
    # 2. 杀进程
    print("[1/3] 停止5002服务...")
    for pid in pids:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    time.sleep(2)

    # 3. 启动服务
    print("[2/3] 启动5002服务...")
    subprocess.Popen(
        [PYTHON, APP_PATH],
        cwd=os.path.dirname(APP_PATH),
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    print("  服务已启动")

    # 4. 验证
    print("[3/3] 验证服务状态...")
    time.sleep(5)
    import urllib.request
    try:
        resp = urllib.request.urlopen("http://localhost:5002/container", timeout=5)
        content = resp.read().decode('utf-8')
        print(f"  /container 返回: {len(content)} 字节")
    except Exception as e:
        print(f"  验证失败: {e}")

    print("Done!")

if __name__ == '__main__':
    main()
