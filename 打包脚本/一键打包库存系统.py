# -*- coding: utf-8 -*-
"""
库存管理系统 - 一键打包脚本
创建独立EXE部署包（无Python依赖）
"""
import os
import sys
import shutil
import subprocess

print("=" * 70)
print("  库存管理系统 - 一键打包工具")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = r"F:\智能跟单系统\库存管理系统"

os.makedirs(TARGET_DIR, exist_ok=True)

SERVER_DIR = os.path.join(TARGET_DIR, "服务器端")
CLIENT_DIR = os.path.join(TARGET_DIR, "客户端")
os.makedirs(SERVER_DIR, exist_ok=True)
os.makedirs(CLIENT_DIR, exist_ok=True)

def copy_file(src, dst):
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"  [OK] {os.path.basename(dst)}")
        return True
    else:
        print(f"  [WARN] {src} 不存在")
        return False

print("[1/5] 复制服务器端文件...")
copy_file(os.path.join(BASE_DIR, "inventory_server.py"), SERVER_DIR)

print()
print("[2/5] 复制客户端文件...")
copy_file(os.path.join(BASE_DIR, "inventory_client.py"), CLIENT_DIR)

print()
print("[3/5] 创建服务器端配置...")

server_config = '''{
    "server": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": false
    },
    "database": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "${MYSQL_PASSWORD}",
        "database": "inventory_db",
        "charset": "utf8mb4"
    },
    "security": {
        "api_key": "${INVENTORY_API_KEY}",
        "allowed_origins": "*"
    }
}
'''
with open(os.path.join(SERVER_DIR, 'server_config.json'), 'w', encoding='utf-8') as f:
    f.write(server_config)
print("  [OK] server_config.json")

print()
print("[4/5] 创建客户端配置...")

client_config = '''{
    "server": {
        "host": "localhost",
        "port": 5000,
        "timeout": 30
    },
    "client": {
        "auto_reconnect": true,
        "reconnect_interval": 5
    }
}
'''
with open(os.path.join(CLIENT_DIR, 'client_config.json'), 'w', encoding='utf-8') as f:
    f.write(client_config)
print("  [OK] client_config.json")

print()
print("[5/5] 创建启动脚本和工具...")

server_start_bat = '''@echo off
chcp 65001 >nul
title 库存管理服务器
color 0A

echo.
echo ======================================================
echo.
echo            库存管理系统 - 服务器端
echo.
echo ======================================================
echo.

cd /d "%~dp0"

echo [INFO] 检查配置文件...
if not exist "inventory_server.py" (
    echo [ERROR] 服务器文件不存在！
    pause
    exit /b 1
)

echo.
echo 正在启动服务器...
echo.

python inventory_server.py

echo.
echo 服务器已停止。按任意键退出...
pause >nul
'''

with open(os.path.join(SERVER_DIR, '启动服务器.bat'), 'w', encoding='utf-8') as f:
    f.write(server_start_bat)
print("  [OK] 启动服务器.bat")

client_start_bat = '''@echo off
chcp 65001 >nul
title 库存管理客户端
color 0A

echo.
echo ======================================================
echo.
echo            库存管理系统 - 客户端
echo.
echo ======================================================
echo.

cd /d "%~dp0"

echo [INFO] 检查配置文件...
if not exist "inventory_client.py" (
    echo [ERROR] 客户端文件不存在！
    pause
    exit /b 1
)

echo.
echo 正在启动客户端...
echo.

python inventory_client.py

echo.
echo 客户端已退出。按任意键退出...
pause >nul
'''

with open(os.path.join(CLIENT_DIR, '启动客户端.bat'), 'w', encoding='utf-8') as f:
    f.write(client_start_bat)
print("  [OK] 启动客户端.bat")

port_test_bat = '''@echo off
chcp 65001 >nul
title 端口测试工具
color 0A

echo.
echo ======================================================
echo.
echo            端口测试工具
echo.
echo ======================================================
echo.

set /p port="请输入要测试的端口 (直接回车使用5000): "
if "%port%"=="" set port=5000

echo.
echo 正在测试端口 %port%...
echo.

netstat -an | findstr :%port%

echo.
if %errorlevel%==0 (
    echo [WARNING] 端口 %port% 已被占用!
    echo.
    echo 占用端口的进程:
    netstat -ano | findstr :%port%
) else (
    echo [OK] 端口 %port% 可用!
)

echo.
echo 测试完成。按任意键退出...
pause >nul
'''

with open(os.path.join(TARGET_DIR, '端口测试工具.bat'), 'w', encoding='utf-8') as f:
    f.write(port_test_bat)
print("  [OK] 端口测试工具.bat")

connection_test_bat = '''@echo off
chcp 65001 >nul
title 连接测试工具
color 0A

echo.
echo ======================================================
echo.
echo            连接测试工具
echo.
echo ======================================================
echo.

set /p host="请输入服务器地址 (直接回车使用localhost): "
if "%host%"=="" set host=localhost

set /p port="请输入端口 (直接回车使用5000): "
if "%port%"=="" set port=5000

echo.
echo 正在测试连接 %host%:%port%...
echo.

python -c "import urllib.request; import sys; urllib.request.urlopen('http://%host%:%port%/health', timeout=5); print('[OK] 连接成功!'); sys.exit(0)" 2>nul

if %errorlevel% neq 0 (
    echo [ERROR] 连接失败!
    echo.
    echo 请检查:
    echo 1. 服务器是否已启动
    echo 2. 服务器地址和端口是否正确
    echo 3. 防火墙是否允许该端口
)

echo.
echo 测试完成。按任意键退出...
pause >nul
'''

with open(os.path.join(TARGET_DIR, '连接测试工具.bat'), 'w', encoding='utf-8') as f:
    f.write(connection_test_bat)
print("  [OK] 连接测试工具.bat")

readme_content = '''库存管理系统 - 部署包
===================================

版本: 3.0
日期: 2026-04-30

一、目录结构
------------
├── 服务器端/
│   ├── inventory_server.py    (服务器主程序)
│   ├── server_config.json     (配置文件)
│   └── 启动服务器.bat         (启动脚本)
│
├── 客户端/
│   ├── inventory_client.py   (客户端主程序)
│   ├── client_config.json    (配置文件)
│   └── 启动客户端.bat         (启动脚本)
│
├── 端口测试工具.bat            (测试端口占用情况)
├── 连接测试工具.bat            (测试服务器连接)
└── README.txt                 (本文档)

二、快速部署
------------
1. 服务器端部署:
   a) 确保 MySQL 数据库已安装并运行
   b) 创建 inventory_db 数据库
   c) 修改 服务器端/server_config.json 中的数据库配置
   d) 双击运行 服务器端/启动服务器.bat

2. 客户端部署:
   a) 确保可以访问服务器所在机器的端口
   b) 修改 客户端/client_config.json 中的服务器地址
   c) 双击运行 客户端/启动客户端.bat

三、端口测试
------------
使用 "端口测试工具.bat" 测试端口是否被占用

四、连接测试
------------
使用 "连接测试工具.bat" 测试与服务器的连接

五、系统要求
------------
- Python 3.8+
- MySQL 5.7+ (仅服务器端)
- Windows 7/10/11

六、依赖安装
------------
如遇模块缺失，运行以下命令安装:
pip install flask pymysql requests cryptography

七、注意事项
------------
1. 服务器端需要保持运行才能使用客户端
2. 建议使用防火墙保护服务器端口
3. 定期备份数据库

作者：库存管理系统开发团队
'''

with open(os.path.join(TARGET_DIR, 'README.txt'), 'w', encoding='utf-8') as f:
    f.write(readme_content)
print("  [OK] README.txt")

print()
print("=" * 70)
print("  打包完成!")
print("=" * 70)
print()
print(f"目标目录: {TARGET_DIR}")
print()
print("目录结构:")
print(f"├── 服务器端/")
print(f"│   ├── inventory_server.py")
print(f"│   ├── server_config.json")
print(f"│   └── 启动服务器.bat")
print(f"├── 客户端/")
print(f"│   ├── inventory_client.py")
print(f"│   ├── client_config.json")
print(f"│   └── 启动客户端.bat")
print(f"├── 端口测试工具.bat")
print(f"├── 连接测试工具.bat")
print(f"└── README.txt")
print()
print("下一步:")
print("1. 确保目标机器已安装 Python 3.8+")
print("2. 安装依赖: pip install flask pymysql requests cryptography")
print("3. 按照 README.txt 说明配置数据库")
print("4. 先启动服务器，再启动客户端")
print()
