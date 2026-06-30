# -*- coding: utf-8 -*-
"""
库存管理系统 - 完整测试工具包
"""
import os
import sys
import json
import subprocess

print("=" * 70)
print("  库存管理系统 - 完整测试工具包")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(BASE_DIR, "测试工具包")
os.makedirs(TEST_DIR, exist_ok=True)

# 1. 创建连接测试脚本
print("[1/4] 创建连接测试...")
test_content = """@echo off
chcp 65001 >nul
title 库存系统连接测试

echo ============================================================
echo   库存管理系统 - 连接测试
echo ============================================================
echo.

echo [1/3] 测试本地服务器...
python -c "import requests; r=requests.get('http://localhost:8080/api/health', timeout=5); print('本地服务器:', r.json().get('status'))"
if errorlevel 1 (
    echo   [失败] 本地服务器无响应
) else (
    echo   [成功]
)

echo.
echo [2/3] 测试网络服务器...
python -c "import requests; r=requests.get('http://192.168.1.32:8080/api/health', timeout=5); print('网络服务器:', r.json().get('status'))"
if errorlevel 1 (
    echo   [失败] 网络服务器无响应
) else (
    echo   [成功]
)

echo.
echo [3/3] 测试数据库连接...
python -c "import requests; r=requests.get('http://192.168.1.32:8080/api/health', timeout=5); print('数据库:', r.json().get('database'))"

echo.
echo ============================================================
echo   测试完成
echo ============================================================
echo.
pause
"""

with open(os.path.join(TEST_DIR, "1-连接测试.bat"), 'w', encoding='gbk') as f:
    f.write(test_content)
print("    [OK] 1-连接测试.bat")

# 2. 创建网络诊断脚本
print("[2/4] 创建网络诊断...")
net_content = """@echo off
chcp 65001 >nul
title 网络诊断

echo ============================================================
echo   网络诊断工具
echo ============================================================
echo.

echo [1/5] 检查本机IP配置...
ipconfig | findstr /i "IPv4"
echo.

echo [2/5] 测试本机回环...
ping 127.0.0.1 -n 2 | findstr "TTL"
if not errorlevel 1 (
    echo   [成功] 本机回环正常
) else (
    echo   [失败] 本机回环异常
)
echo.

echo [3/5] 测试服务器连接...
ping 192.168.1.32 -n 2 | findstr "TTL"
if not errorlevel 1 (
    echo   [成功] 服务器可达
) else (
    echo   [失败] 无法连接到服务器
)
echo.

echo [4/5] 检查服务器端口...
netstat -an | findstr "8080"
echo.

echo [5/5] 测试API端口...
python -c "import socket; s=socket.socket(); result=s.connect_ex(('192.168.1.32', 8080)); s.close(); exit(0 if result==0 else 1)"
if not errorlevel 1 (
    echo   [成功] 端口8080可访问
) else (
    echo   [失败] 端口8080不可访问
)

echo.
echo ============================================================
echo   诊断完成
echo ============================================================
echo.
pause
"""

with open(os.path.join(TEST_DIR, "2-网络诊断.bat"), 'w', encoding='gbk') as f:
    f.write(net_content)
print("    [OK] 2-网络诊断.bat")

# 3. 创建客户端测试
print("[3/4] 创建客户端测试...")
client_content = """@echo off
chcp 65001 >nul
title 客户端测试

echo ============================================================
echo   客户端配置测试
echo ============================================================
echo.

echo [1/4] 检查Python环境...
python --version
if errorlevel 1 (
    echo   [失败] Python未安装
    pause
    exit /b 1
)
echo   [成功]
echo.

echo [2/4] 检查配置文件...
if exist "inventory_client_config.json" (
    echo   [成功] 配置文件存在
    type inventory_client_config.json
) else (
    echo   [失败] 配置文件不存在
)
echo.

echo [3/4] 测试requests库...
python -c "import requests; print('requests版本:', requests.__version__)"
if errorlevel 1 (
    echo   [失败] requests未安装
    echo   运行: pip install requests
) else (
    echo   [成功]
)
echo.

echo [4/4] 测试服务器连接...
python -c "import requests; r=requests.get('http://192.168.1.32:8080/api/health', timeout=5); print('服务器响应:', r.json())"
if errorlevel 1 (
    echo   [失败] 无法连接到服务器
) else (
    echo   [成功]
)

echo.
echo ============================================================
echo   测试完成
echo ============================================================
echo.
pause
"""

with open(os.path.join(TEST_DIR, "3-客户端测试.bat"), 'w', encoding='gbk') as f:
    f.write(client_content)
print("    [OK] 3-客户端测试.bat")

# 4. 创建使用说明
print("[4/4] 创建使用说明...")
readme_content = """# 库存管理系统 - 测试工具包使用说明

## 测试工具清单

### 1-连接测试.bat
测试服务器连接状态
- 测试本地服务器 (localhost:8080)
- 测试网络服务器 (192.168.1.32:8080)
- 测试数据库连接

### 2-网络诊断.bat
诊断网络问题
- 检查本机IP配置
- 测试本机回环
- 测试服务器连接
- 检查端口8080状态
- 测试API端口可达性

### 3-客户端测试.bat
测试客户端环境
- 检查Python环境
- 检查配置文件
- 测试requests库
- 测试服务器连接

## 使用顺序

1. 先运行 `1-连接测试.bat` - 确认服务器是否可达
2. 如果连接失败，运行 `2-网络诊断.bat` - 诊断网络问题
3. 如果环境问题，运行 `3-客户端测试.bat` - 检查客户端环境

## 常见问题

Q: 测试显示"失败"怎么办？
A: 根据测试结果判断：
   - 如果本地服务器失败 → 服务器未启动，启动服务器
   - 如果网络服务器失败 → 检查网络连接和防火墙
   - 如果数据库失败 → 检查MySQL服务是否启动

Q: 所有测试都成功但客户端还是无法连接？
A: 可能原因：
   - 客户端配置的服务器IP不正确
   - 尝试使用 localhost 而不是 192.168.1.32
   - 重启服务器和客户端

## 技术支持

如果问题无法解决，请记录：
1. 运行所有测试的输出
2. 服务器IP地址
3. 错误提示截图
"""

with open(os.path.join(TEST_DIR, "使用说明.txt"), 'w', encoding='utf-8') as f:
    f.write(readme_content)
print("    [OK] 使用说明.txt")

print()
print("=" * 70)
print("  [OK] 测试工具包创建完成")
print("=" * 70)
print()
print(f"位置: {TEST_DIR}")
print()
print("包含：")
print("  1-连接测试.bat   - 测试服务器连接")
print("  2-网络诊断.bat   - 诊断网络问题")
print("  3-客户端测试.bat - 测试客户端环境")
print("  使用说明.txt     - 使用指南")
print()
print("=" * 70)
print()
print("请双击运行测试工具，按顺序测试：")
print()
print("1. 先运行「1-连接测试.bat」")
print("2. 如果失败，运行「2-网络诊断.bat」")
print("3. 如果是客户端问题，运行「3-客户端测试.bat」")
print()
print("=" * 70)

# 打开测试目录
try:
    os.startfile(TEST_DIR)
except:
    pass
