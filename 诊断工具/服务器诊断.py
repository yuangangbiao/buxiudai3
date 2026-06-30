# -*- coding: utf-8 -*-
"""
服务器连接诊断工具
"""
import os
import sys
import socket
import requests
from datetime import datetime

print("=" * 70)
print("  库存管理系统 - 服务器连接诊断")
print("=" * 70)
print()
print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 1. 检查服务器是否运行
print("[1/5] 检查服务器运行状态...")
print()

# 检查端口8080是否被占用
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('192.168.1.32', 8080))
    sock.close()
    
    if result == 0:
        print("    [OK] 端口8080已被占用，服务器可能在运行")
    else:
        print("    [ERROR] 端口8080未被监听，服务器可能未运行")
except Exception as e:
    print(f"    [ERROR] 检查失败: {e}")

print()

# 2. 测试本地API
print("[2/5] 测试本地API...")
try:
    response = requests.get('http://localhost:8080/api/health', timeout=3)
    print(f"    [OK] API响应: {response.status_code}")
    print(f"    内容: {response.text}")
except Exception as e:
    print(f"    [ERROR] API连接失败: {e}")
    print("    可能原因：服务器未启动或端口未监听")

print()

# 3. 测试远程API
print("[3/5] 测试远程API...")
try:
    response = requests.get('http://192.168.1.32:8080/api/health', timeout=3)
    print(f"    [OK] API响应: {response.status_code}")
    print(f"    内容: {response.text}")
except Exception as e:
    print(f"    [ERROR] 远程API连接失败: {e}")

print()

# 4. 检查客户端配置
print("[4/5] 检查客户端配置...")
config_path = os.path.join(os.path.dirname(__file__), "最终零依赖EXE部署包", "inventory_client_config.json")
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        print(f"    [OK] 配置文件存在: {config_path}")
        content = f.read()
        if "192.168.1.32" in content:
            print("    [OK] 服务器地址配置为: 192.168.1.32")
        else:
            print("    [WARN] 服务器地址可能不正确")
else:
    print(f"    [WARN] 配置文件不存在: {config_path}")

print()

# 5. 网络诊断
print("[5/5] 网络诊断...")
try:
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"    本机主机名: {hostname}")
    print(f"    本机IP地址: {local_ip}")
    
    if local_ip == "192.168.1.32":
        print("    [OK] 本机IP与服务器IP一致")
    else:
        print("    [WARN] 本机IP与服务器IP不一致")
        print("    客户端需要连接服务器的实际IP，而不是本机IP")
except Exception as e:
    print(f"    [ERROR] 获取IP失败: {e}")

print()
print("=" * 70)
print("  诊断完成")
print("=" * 70)
print()

# 解决方案提示
print("=" * 70)
print("  解决方案")
print("=" * 70)
print()
print("如果服务器未运行：")
print("  1. 双击「启动服务器.bat」或「库存管理系统服务器.exe」")
print("  2. 确保看到'Running on http://0.0.0.0:8080'")
print()
print("如果服务器已运行但仍无法连接：")
print("  1. 检查客户端配置的服务器地址是否正确")
print("  2. 服务器地址应为：http://192.168.1.32:8080")
print("  3. 两台电脑必须在同一局域网")
print()
print("如果在不同网段：")
print("  1. 需要路由器端口转发")
print("  2. 或使用VPN连接")
print()
print("=" * 70)

input("按回车键退出...")
