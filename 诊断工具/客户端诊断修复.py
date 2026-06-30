# -*- coding: utf-8 -*-
"""
客户端连接诊断和修复工具
"""
import os
import sys
import json

print("=" * 70)
print("  客户端连接诊断和修复")
print("=" * 70)
print()

# 1. 检查服务器状态
print("[1/4] 检查服务器状态...")
try:
    import requests
    response = requests.get('http://192.168.1.32:8080/api/health', timeout=3)
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'ok':
            print("    [OK] 服务器运行正常")
            print(f"    数据库: {data.get('database')}")
            print(f"    产品数: {data.get('stats', {}).get('product_count', 'N/A')}")
        else:
            print(f"    [WARN] 服务器状态: {data.get('status')}")
    else:
        print(f"    [ERROR] 服务器响应异常: {response.status_code}")
except Exception as e:
    print(f"    [ERROR] 无法连接到服务器: {e}")
    print("    可能原因：")
    print("      1. 服务器未启动")
    print("      2. IP地址不正确")
    print("      3. 网络不通")

print()

# 2. 检查客户端配置
print("[2/4] 检查客户端配置...")
config_locations = [
    os.path.join(os.path.dirname(__file__), "最终零依赖EXE部署包", "inventory_client_config.json"),
    os.path.join(os.path.dirname(__file__), "inventory_client_config.json"),
    os.path.join(os.path.dirname(__file__), "零依赖客户端部署包", "inventory_client_config.json"),
]

found_config = None
for loc in config_locations:
    if os.path.exists(loc):
        found_config = loc
        print(f"    [OK] 找到配置文件: {loc}")
        with open(loc, 'r', encoding='utf-8') as f:
            config = json.load(f)
            print(f"    服务器地址: {config.get('server_url')}")
            print(f"    API密钥: {config.get('api_key')}")
        break

if not found_config:
    print("    [ERROR] 未找到配置文件")
    print("    将创建默认配置...")

print()

# 3. 检查Python环境
print("[3/4] 检查Python环境...")
try:
    import tkinter as tk
    print("    [OK] tkinter已安装")
except ImportError:
    print("    [ERROR] tkinter未安装")
    print("    EXE版本可能存在问题")

print()

# 4. 解决方案
print("[4/4] 提供解决方案...")
print()
print("=" * 70)
print("  解决方案")
print("=" * 70)
print()

print("如果客户端无法连接，请按以下步骤：")
print()
print("步骤1：确保服务器运行中")
print("  - 服务器应显示'Running on http://0.0.0.0:8080'")
print("  - 本机测试: http://localhost:8080/api/health")
print()

print("步骤2：检查客户端配置")
print("  - 配置文件应放在EXE同一目录")
print("  - 文件名: inventory_client_config.json")
print("  - 内容:")
print('  {')
print('    "server_url": "http://192.168.1.32:8080",')
print('    "api_key": "请设置环境变量 INVENTORY_API_KEY"')
print('  }')
print()

print("步骤3：手动启动客户端测试")
print("  - 如果EXE无法连接，可以尝试Python版本")
print("  - 运行: python inventory_client.py")
print()

print("步骤4：检查网络")
print("  - 确保客户端电脑与服务器在同一局域网")
print("  - ping 192.168.1.32 测试连通性")
print()

# 创建测试脚本
print()
print("=" * 70)
print("  创建测试脚本...")
print("=" * 70)
print()

test_script = '''@echo off
chcp 65001 >nul
title 库存系统连接测试

echo ============================================================
echo   库存系统连接测试
echo ============================================================
echo.

echo 测试服务器连接...
python -c "import requests; r=requests.get('http://192.168.1.32:8080/api/health', timeout=5); print('服务器状态:', r.json().get('status'))"

echo.
echo 按任意键退出...
pause >nul
'''

with open(os.path.join(os.path.dirname(__file__), "连接测试.bat"), 'w', encoding='gbk') as f:
    f.write(test_script)

print("已创建: 连接测试.bat")
print()
print("您可以双击运行此脚本测试服务器连接")

print()
print("=" * 70)

input("按回车键退出...")
