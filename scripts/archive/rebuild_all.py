# -*- coding: utf-8 -*-
"""
完整重新打包 - 从头开始创建所有部署包
"""
import os
import shutil
import subprocess

print("=" * 70)
print("  完整重新打包 - 创建所有部署包")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. 清理旧的部署包目录
print("[1/5] 清理旧的部署包目录...")
DEPLOY_DIR = os.path.join(BASE_DIR, "部署包")
if os.path.exists(DEPLOY_DIR):
    shutil.rmtree(DEPLOY_DIR)
    print("    [OK] 已删除旧部署包目录")

os.makedirs(DEPLOY_DIR, exist_ok=True)
print()

# 2. 创建服务端部署包
print("[2/5] 创建服务端部署包...")
SERVER_DIR = os.path.join(DEPLOY_DIR, "服务端")
os.makedirs(SERVER_DIR, exist_ok=True)

# 复制服务器源码
server_files = [
    "inventory_server.py",
    "inventory_db_complete.py",
    "inventory_backup.py",
    "inventory_print.py",
    "inventory_manager_complete.py",
]

for f in server_files:
    src = os.path.join(BASE_DIR, f)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(SERVER_DIR, f))
        print(f"    [OK] 复制 {f}")

# 创建服务器启动脚本
server_start = """@echo off
chcp 65001 >nul
title Inventory Server

echo ============================================================
echo            Inventory Management Server
echo ============================================================
echo.

echo Starting server...
python inventory_server.py

pause
"""

with open(os.path.join(SERVER_DIR, "启动服务器.bat"), 'w', encoding='gbk') as f:
    f.write(server_start)
print("    [OK] 创建 启动服务器.bat")

# 创建初始化数据库脚本
init_db = """@echo off
chcp 65001 >nul
title Initialize Database

echo ============================================================
echo            Initialize Database
echo ============================================================
echo.

echo This will create the inventory database.
echo.

set /p confirm=Continue? (Y/N):
if /i not "%confirm%"=="Y" exit

python -c "from inventory_db_complete import init_database; init_database()"

echo.
echo Database initialized successfully!
pause
"""

with open(os.path.join(SERVER_DIR, "初始化数据库.bat"), 'w', encoding='gbk') as f:
    f.write(init_db)
print("    [OK] 创建 初始化数据库.bat")

# 创建防火墙配置脚本
firewall = """@echo off
chcp 65001 >nul
title Configure Firewall

echo ============================================================
echo            Configure Firewall
echo ============================================================
echo.

echo Adding firewall rule for port 8080...
netsh advfirewall firewall add rule name="Inventory Server 8080" dir=in action=allow protocol=TCP localport=8080

echo.
echo Firewall configured successfully!
pause
"""

with open(os.path.join(SERVER_DIR, "配置防火墙.bat"), 'w', encoding='gbk') as f:
    f.write(firewall)
print("    [OK] 创建 配置防火墙.bat")

# 创建服务器配置
server_config = """{
    "host": "0.0.0.0",
    "port": 8080,
    "api_key": "${INVENTORY_API_KEY}",
    "database": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "${MYSQL_PASSWORD}",
        "database": "inventory_management_db"
    }
}
"""

with open(os.path.join(SERVER_DIR, "server_config.json"), 'w', encoding='utf-8') as f:
    f.write(server_config)
print("    [OK] 创建 server_config.json")

print()

# 3. 创建客户端完整功能EXE部署包
print("[3/5] 创建客户端完整功能EXE部署包...")
CLIENT_FULL_DIR = os.path.join(DEPLOY_DIR, "客户端完整功能版")
os.makedirs(CLIENT_FULL_DIR, exist_ok=True)

# 复制客户端源码
client_files = [
    "inventory_client.py",
]

for f in client_files:
    src = os.path.join(BASE_DIR, f)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(CLIENT_FULL_DIR, f))
        print(f"    [OK] 复制 {f}")

# 创建客户端配置
client_config = """{
    "server_url": "http://localhost:8080",
    "api_key": "${INVENTORY_API_KEY}",
    "auto_refresh": true,
    "refresh_interval": 60
}
"""

with open(os.path.join(CLIENT_FULL_DIR, "inventory_client_config.json"), 'w', encoding='utf-8') as f:
    f.write(client_config)
print("    [OK] 创建 inventory_client_config.json")

# 创建客户端启动脚本
client_start = """@echo off
chcp 65001 >nul
title Inventory Client

echo ============================================================
echo            Inventory Management Client
echo ============================================================
echo.

echo Starting client...
python inventory_client.py

pause
"""

with open(os.path.join(CLIENT_FULL_DIR, "启动客户端.bat"), 'w', encoding='gbk') as f:
    f.write(client_start)
print("    [OK] 创建 启动客户端.bat")

# 创建安装依赖脚本
install_deps = """@echo off
chcp 65001 >nul
title Install Dependencies

echo ============================================================
echo            Install Dependencies
echo ============================================================
echo.

pip install requests flask pymysql

echo.
echo Dependencies installed successfully!
pause
"""

with open(os.path.join(CLIENT_FULL_DIR, "安装依赖.bat"), 'w', encoding='gbk') as f:
    f.write(install_deps)
print("    [OK] 创建 安装依赖.bat")

print()

# 4. 创建简版客户端部署包
print("[4/5] 创建简版客户端部署包...")
CLIENT_SIMPLE_DIR = os.path.join(DEPLOY_DIR, "客户端简版")
os.makedirs(CLIENT_SIMPLE_DIR, exist_ok=True)

# 复制客户端源码
for f in client_files:
    src = os.path.join(BASE_DIR, f)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(CLIENT_SIMPLE_DIR, f))
        print(f"    [OK] 复制 {f}")

# 复制配置
shutil.copy2(
    os.path.join(CLIENT_FULL_DIR, "inventory_client_config.json"),
    os.path.join(CLIENT_SIMPLE_DIR, "inventory_client_config.json")
)
print("    [OK] 复制 inventory_client_config.json")

# 创建启动脚本
with open(os.path.join(CLIENT_SIMPLE_DIR, "启动客户端.bat"), 'w', encoding='gbk') as f:
    f.write(client_start)
print("    [OK] 创建 启动客户端.bat")

# 创建安装依赖脚本
with open(os.path.join(CLIENT_SIMPLE_DIR, "安装依赖.bat"), 'w', encoding='gbk') as f:
    f.write(install_deps)
print("    [OK] 创建 安装依赖.bat")

print()

# 5. 整理测试工具
print("[5/5] 整理测试工具...")
TEST_DIR = os.path.join(BASE_DIR, "测试工具")
if os.path.exists(TEST_DIR):
    test_files = os.listdir(TEST_DIR)
    print(f"    [OK] 测试工具已存在 ({len(test_files)} 个文件)")

print()
print("=" * 70)
print("  [OK] 基础部署包创建完成！")
print("=" * 70)
print()
print("注意: EXE文件需要通过PyInstaller手动打包")
print()
print("部署包结构:")
print(f"  {DEPLOY_DIR}/")
print(f"  ├── 服务端/         (Python源码版)")
print(f"  ├── 客户端完整功能版/ (Python源码版)")
print(f"  └── 客户端简版/     (Python源码版)")
print()

# 打开部署包目录
try:
    os.startfile(DEPLOY_DIR)
except Exception as e:
    print(f"打开部署包目录失败: {e}")
