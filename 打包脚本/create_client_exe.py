# -*- coding: utf-8 -*-
"""
创建库存管理系统客户端独立EXE
"""
import os
import sys
import shutil

print("=" * 70)
print("  创建库存管理系统客户端独立EXE")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE = os.path.join(BASE_DIR, "inventory_client.py")
DEST_DIR = r"F:\智能跟单系统\库存管理系统\客户端"

os.makedirs(DEST_DIR, exist_ok=True)

spec_content = '''# -*- coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = [
    ('inventory_client.py', '.'),
]

hiddenimports = [
    'tkinter',
    'requests',
    'pymysql',
    'cryptography',
    'urllib3',
    'idna',
    'charset_normalizer',
    'certifi',
]

a = Analysis(
    ['inventory_client.py'],
    pathex=[os.path.dirname(os.path.abspath(__file__))],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
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
    name='库存管理客户端',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=None,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''

spec_file = os.path.join(BASE_DIR, 'client.spec')
with open(spec_file, 'w', encoding='utf-8') as f:
    f.write(spec_content)

print(f"源文件: {SOURCE_FILE}")
print(f"目标目录: {DEST_DIR}")
print()

if not os.path.exists(SOURCE_FILE):
    print("[ERROR] 客户端文件不存在!")
    sys.exit(1)

shutil.copy2(SOURCE_FILE, os.path.join(DEST_DIR, 'inventory_client.py'))
print("[OK] 复制客户端文件")

config_content = '''{
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

with open(os.path.join(DEST_DIR, 'client_config.json'), 'w', encoding='utf-8') as f:
    f.write(config_content)
print("[OK] 创建配置文件")

readme_content = '''库存管理系统 - 客户端
===================================

一、配置说明
------------
1. 首次运行会自动创建配置文件
2. 服务器地址在启动后点击 "设置" 修改
3. 确保服务器端已启动并正常运行

二、启动方式
------------
1. 双击运行 "启动客户端.bat"
2. 或直接双击 "库存管理客户端.exe"

三、连接测试
------------
使用 "连接测试工具.bat" 测试与服务器的连接

四、常见问题
------------
1. 连接失败：检查服务器地址和端口是否正确
2. 超时错误：检查网络连接，或增加超时时间
3. 数据同步问题：刷新页面或重启客户端

作者：库存管理系统
版本：3.0
'''

with open(os.path.join(DEST_DIR, 'README.txt'), 'w', encoding='utf-8') as f:
    f.write(readme_content)
print("[OK] 创建说明文档")

start_bat = '''@echo off
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

echo [INFO] 启动客户端...
start "库存管理客户端" "库存管理客户端.exe"

echo.
echo [OK] 客户端已启动
echo.
pause
'''

with open(os.path.join(DEST_DIR, '启动客户端.bat'), 'w', encoding='utf-8') as f:
    f.write(start_bat)
print("[OK] 创建启动脚本")

connection_test_bat = '''@echo off
chcp 65001 >nul
title 连接测试工具

echo.
echo ======================================================
echo.
echo            连接测试工具
echo.
echo ======================================================
echo.

set /p host="请输入服务器地址 (默认localhost): "
if "%host%"=="" set host=localhost

set /p port="请输入端口 (默认5000): "
if "%port%"=="" set port=5000

echo.
echo 正在测试连接 %host%:%port%...
echo.

powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://%host%:%port%/health' -TimeoutSec 5 -UseBasicParsing; if ($response.StatusCode -eq 200) { Write-Host '[OK] 连接成功!' -ForegroundColor Green } else { Write-Host '[WARNING] 服务器响应异常' -ForegroundColor Yellow } } catch { Write-Host '[ERROR] 连接失败!' -ForegroundColor Red; Write-Host $_.Exception.Message }"

echo.
echo 测试完成。按任意键退出...
pause >nul
'''

with open(os.path.join(DEST_DIR, '连接测试工具.bat'), 'w', encoding='utf-8') as f:
    f.write(connection_test_bat)
print("[OK] 创建连接测试工具")

print()
print("=" * 70)
print("  客户端部署包创建完成!")
print("=" * 70)
print()
print(f"目标目录: {DEST_DIR}")
print()
print("下一步:")
print("1. 使用 PyInstaller 构建 EXE:")
print("   pyinstaller client.spec")
print()
print("2. 构建完成后将 dist\\\\库存管理客户端.exe 复制到目标目录")
print()
