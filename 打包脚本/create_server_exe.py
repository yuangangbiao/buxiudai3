# -*- coding: utf-8 -*-
"""
创建库存管理系统服务器端独立EXE
"""
import os
import sys
import shutil
import subprocess

print("=" * 70)
print("  创建库存管理系统服务器端独立EXE")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(BASE_DIR, "inventory_server.py")
DEST_DIR = r"F:\智能跟单系统\库存管理系统\服务器端"

os.makedirs(DEST_DIR, exist_ok=True)

spec_content = '''# -*- coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# 收集所有数据文件
datas = [
    ('inventory_server.py', '.'),
]

# 收集所有导入的模块
hiddenimports = [
    'flask',
    'pymysql',
    'cryptography',
    'werkzeug',
    'jinja2',
    'markupsafe',
    'itsdangerous',
    'click',
    'certifi',
    'urllib3',
    'idna',
    'charset_normalizer',
]

a = Analysis(
    ['inventory_server.py'],
    pathex=[os.path.dirname(os.path.abspath(__file__))],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='库存管理服务器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''

spec_file = os.path.join(BASE_DIR, 'server.spec')
with open(spec_file, 'w', encoding='utf-8') as f:
    f.write(spec_content)

print(f"源文件: {SOURCE_DIR}")
print(f"目标目录: {DEST_DIR}")
print()

if not os.path.exists(SOURCE_DIR):
    print("[ERROR] 服务器文件不存在!")
    sys.exit(1)

shutil.copy2(SOURCE_DIR, os.path.join(DEST_DIR, 'inventory_server.py'))
print("[OK] 复制服务器文件")

config_content = '''{
    "server": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": false
    },
    "database": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": os.getenv('MYSQL_PASSWORD', ''),
        "database": "inventory_db",
        "charset": "utf8mb4"
    },
    "security": {
        "api_key": os.getenv('INVENTORY_API_KEY', ''),
        "allowed_origins": "*"
    }
}
'''

with open(os.path.join(DEST_DIR, 'server_config.json'), 'w', encoding='utf-8') as f:
    f.write(config_content)
print("[OK] 创建配置文件")

readme_content = '''库存管理系统 - 服务器端
===================================

一、配置说明
------------
1. 打开 server_config.json 修改数据库连接配置
2. 确保 MySQL 数据库已安装并运行
3. 确保指定端口(默认5000)未被占用

二、启动方式
------------
1. 双击运行 "启动服务器.bat"
2. 等待窗口显示 "starting server on port 5000"
3. 出现 "Press Ctrl+C to quit" 表示启动成功

三、端口测试
------------
使用 "端口测试工具.bat" 测试服务器端口是否可用

四、常见问题
------------
1. 数据库连接失败：检查 MySQL 是否运行，密码是否正确
2. 端口被占用：修改 server_config.json 中的 port 值
3. 防火墙拦截：添加防火墙例外规则

作者：库存管理系统
版本：3.0
'''

with open(os.path.join(DEST_DIR, 'README.txt'), 'w', encoding='utf-8') as f:
    f.write(readme_content)
print("[OK] 创建说明文档")

start_bat = '''@echo off
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
if not exist "server_config.json" (
    echo [ERROR] 配置文件不存在！
    pause
    exit /b 1
)

echo [INFO] 启动服务器...
start "库存管理服务器" "库存管理服务器.exe"

timeout /t 2 /nobreak >nul

echo.
echo [OK] 服务器已在后台启动
echo.
echo 提示：关闭窗口不会停止服务器
echo       如需停止服务器，请关闭 "库存管理服务器" 窗口
echo.
pause
'''

with open(os.path.join(DEST_DIR, '启动服务器.bat'), 'w', encoding='utf-8') as f:
    f.write(start_bat)
print("[OK] 创建启动脚本")

port_test_bat = '''@echo off
chcp 65001 >nul
title 端口测试工具

echo.
echo ======================================================
echo.
echo            端口测试工具
echo.
echo ======================================================
echo.

set /p port="请输入要测试的端口 (默认5000): "
if "%port%"=="" set port=5000

echo.
echo 正在测试端口 %port%...
echo.

netstat -an | findstr :%port%

if %errorlevel%==0 (
    echo.
    echo [WARNING] 端口 %port% 已被占用!
    echo.
    echo 以下是占用端口的进程:
    netstat -ano | findstr :%port%
) else (
    echo.
    echo [OK] 端口 %port% 可用!
)

echo.
echo 测试完成。按任意键退出...
pause >nul
'''

with open(os.path.join(DEST_DIR, '端口测试工具.bat'), 'w', encoding='utf-8') as f:
    f.write(port_test_bat)
print("[OK] 创建端口测试工具")

print()
print("=" * 70)
print("  服务器端部署包创建完成!")
print("=" * 70)
print()
print(f"目标目录: {DEST_DIR}")
print()
print("下一步:")
print("1. 使用 PyInstaller 构建 EXE:")
print(f"   pyinstaller server.spec")
print()
print("2. 构建完成后将 dist\\库存管理服务器.exe 复制到目标目录")
print()
