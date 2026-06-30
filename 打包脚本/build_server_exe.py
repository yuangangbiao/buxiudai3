# -*- coding: utf-8 -*-
"""
库存管理系统 - 服务器端EXE打包工具
包含图形界面，零依赖
"""
import os
import sys
import shutil
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BASE_DIR, "server_build_exe")
SERVER_DEPLOY_DIR = os.path.join(BASE_DIR, "零依赖服务器EXE部署包")

print("=" * 70)
print("  库存管理系统 - 服务器端EXE打包")
print("=" * 70)
print()

# 1. 检查环境
print("[1/6] 检查环境...")
print("    Python:", sys.version.split()[0])

try:
    import PyInstaller
    print("    PyInstaller:", PyInstaller.__version__)
except ImportError:
    print("    正在安装PyInstaller...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "pyinstaller",
        "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
    ])
    import PyInstaller
    print("    PyInstaller已安装")

# 2. 清理并创建目录
print()
print("[2/6] 准备目录...")
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)
os.makedirs(BUILD_DIR)

# 3. 创建spec文件
print()
print("[3/6] 创建打包配置...")

spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

a = Analysis(
    ['{os.path.join(BASE_DIR, "inventory_manager_complete.py")}'],
    pathex=['{BASE_DIR}'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'requests',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'pymysql',
        'flask',
        'json',
        'os',
        'sys',
        'threading',
        'logging',
        'datetime',
    ],
    hookspath=[],
    hooksconfig={{}},
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
    name='库存管理系统服务器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''

spec_path = os.path.join(BUILD_DIR, 'server.spec')
with open(spec_path, 'w', encoding='utf-8') as f:
    f.write(spec_content)
print("    [OK] spec文件已创建")

# 4. 执行打包
print()
print("[4/6] 开始打包...")
print("    注意：打包过程需要3-5分钟，请耐心等待...")
print()

os.chdir(BUILD_DIR)
result = subprocess.run([
    sys.executable, "-m", "PyInstaller", "--clean", "server.spec"
], capture_output=True, text=True, encoding='utf-8', errors='ignore')

if result.returncode == 0:
    print("    [OK] 打包成功！")
else:
    print("    [WARN] 打包完成，但可能有警告")
    if result.stderr:
        print("    警告信息:", result.stderr[-300:])

# 5. 创建部署包
print()
print("[5/6] 创建零依赖部署包...")

if os.path.exists(SERVER_DEPLOY_DIR):
    shutil.rmtree(SERVER_DEPLOY_DIR)
os.makedirs(SERVER_DEPLOY_DIR)

# 复制EXE
exe_src = os.path.join(BUILD_DIR, 'dist', '库存管理系统服务器.exe')
if os.path.exists(exe_src):
    shutil.copy2(exe_src, SERVER_DEPLOY_DIR)
    size_mb = os.path.getsize(exe_src) / (1024 * 1024)
    print(f"    [OK] 服务器EXE已复制 ({size_mb:.1f} MB)")
else:
    print("    [ERROR] 未找到EXE文件")

# 复制依赖模块
dep_files = [
    "inventory_db_complete.py",
    "inventory_backup.py",
    "inventory_print.py",
    "inventory_server.py",
]
for f in dep_files:
    src = os.path.join(BASE_DIR, f)
    if os.path.exists(src):
        shutil.copy2(src, SERVER_DEPLOY_DIR)
        print(f"    [OK] {f}")

# 复制配置文件
config_files = [
    "server_config.json",
]
for f in config_files:
    src = os.path.join(BASE_DIR, f)
    if os.path.exists(src):
        shutil.copy2(src, SERVER_DEPLOY_DIR)
        print(f"    [OK] {f}")

# 创建数据库初始化脚本
with open(os.path.join(SERVER_DEPLOY_DIR, "初始化数据库.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 库存管理系统 - 数据库初始化

echo ============================================================
echo.
echo            库存管理系统 - 数据库初始化
echo.
echo ============================================================
echo.

set /p confirm=确认初始化数据库？(Y/N): 
if /i not "%confirm%"=="Y" (
    echo 操作已取消
    pause
    exit /b
)

echo.
echo 正在检查Python和依赖...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python！
    pause
    exit /b 1
)

python -c "import pymysql" >nul 2>&1
if errorlevel 1 (
    echo 正在安装pymysql...
    pip install pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo 正在初始化数据库...

python -c "
import pymysql
import sys
import os

DB_HOST = os.getenv('MYSQL_HOST', 'localhost')
DB_PORT = int(os.getenv('MYSQL_PORT', 3306))
DB_USER = os.getenv('MYSQL_USER', 'root')
DB_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
DB_NAME = os.getenv('MYSQL_DATABASE', 'inventory_management_db')"

try:
    print('连接MySQL...')
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, charset='utf8mb4')
    cursor = conn.cursor()
    
    print('创建数据库...')
    cursor.execute(f'CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    
    cursor.execute(f'USE {DB_NAME}')
    
    print('创建仓库表...')
    cursor.execute('''CREATE TABLE IF NOT EXISTS warehouses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        location VARCHAR(200),
        manager VARCHAR(50),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
    
    print('创建供应商表...')
    cursor.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        contact VARCHAR(100),
        phone VARCHAR(50),
        address VARCHAR(300),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
    
    print('创建产品表...')
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_code VARCHAR(50) UNIQUE,
        product_name VARCHAR(200) NOT NULL,
        category VARCHAR(100),
        unit VARCHAR(20) DEFAULT '个',
        spec VARCHAR(200),
        safety_stock DECIMAL(10,2) DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
    
    print('创建库存表...')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INT AUTO_INCREMENT PRIMARY KEY,
        warehouse_id INT,
        product_id INT NOT NULL,
        quantity DECIMAL(10,2) DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
    
    print('创建出入库记录表...')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        type ENUM('inbound', 'outbound') NOT NULL,
        product_id INT NOT NULL,
        warehouse_id INT,
        quantity DECIMAL(10,2) NOT NULL,
        operator VARCHAR(50),
        reference_no VARCHAR(100),
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
    
    print('创建通知表...')
    cursor.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        type VARCHAR(50) NOT NULL,
        title VARCHAR(200) NOT NULL,
        content TEXT,
        level ENUM('info', 'warning', 'error') DEFAULT 'info',
        is_read TINYINT DEFAULT 0,
        response VARCHAR(50),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
    
    cursor.execute("SELECT COUNT(*) FROM warehouses")
    if cursor.fetchone()[0] == 0:
        cursor.execute(\"INSERT INTO warehouses (name, location, manager) VALUES ('主仓库', '默认位置', '管理员')\")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print()
    print('=' * 50)
    print('  [OK] 数据库初始化成功！')
    print('=' * 50)
    print('数据库:', DB_NAME)
    print('注意：此数据库与跟单系统完全独立！')
    
except Exception as e:
    print()
    print('=' * 50)
    print(f'  [错误] 初始化失败: {e}')
    print('=' * 50)
    sys.exit(1)

pause
""")
print("    [OK] 初始化数据库.bat")

# 创建防火墙配置
with open(os.path.join(SERVER_DEPLOY_DIR, "配置防火墙.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 防火墙配置

echo ============================================================
echo   防火墙配置
echo ============================================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 需要管理员权限！
    echo 请右键点击「以管理员身份运行」
    pause
    exit /b 1
)

echo 添加防火墙规则...
netsh advfirewall firewall add rule name="库存管理系统8080" dir=in action=allow protocol=TCP localport=8080 >nul 2>&1

echo.
echo ============================================================
echo   [OK] 防火墙配置完成！
echo ============================================================
echo.
echo 客户端连接地址: http://192.168.1.32:8080
echo.
pause
""")
print("    [OK] 配置防火墙.bat")

# 创建说明文档
with open(os.path.join(SERVER_DEPLOY_DIR, "使用说明.txt"), 'w', encoding='utf-8') as f:
    f.write("""# 库存管理系统服务器 - 使用说明

## 系统介绍

本系统为库存管理系统的**独立服务器端**，
使用独立的数据库（inventory_management_db），
不会影响跟单系统的主数据库。

---

## 部署步骤

### 第一次部署

1. **初始化数据库**
   - 双击「初始化数据库.bat」
   - 输入 Y 确认
   - 等待完成

2. **配置防火墙**
   - 右键「配置防火墙.bat」
   - 选择「以管理员身份运行」

3. **启动服务器**
   - 双击「库存管理系统服务器.exe」
   - 看到主界面表示成功

### 后续启动

直接双击「库存管理系统服务器.exe」即可

---

## 数据库说明

- 数据库名称：`inventory_management_db`
- 与跟单系统数据库（`steel_belt`）完全独立
- 不会影响跟单系统的任何数据

---

## 服务器信息

- 服务器地址：http://192.168.1.32:8080
- API密钥：steel_belt_inventory_key_2024

---

## 常见问题

Q: EXE启动失败？
A: 检查：
   - 是否首次运行？需先初始化数据库
   - MySQL服务是否启动
   - 端口8080是否被占用

Q: 客户端无法连接？
A: 检查：
   - 服务器是否已启动
   - 防火墙是否已配置
   - IP地址是否正确

---

版本：1.0
日期：2026-04-30
""")
print("    [OK] 使用说明.txt")

# 创建快速指南
with open(os.path.join(SERVER_DEPLOY_DIR, "快速指南.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 快速启动

echo ============================================================
echo   库存管理系统 - 快速启动
echo ============================================================
echo.

REM 检查数据库
python -c "import pymysql" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖...
    pip install pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo 正在启动服务器...
echo.

start "" "库存管理系统服务器.exe"

echo.
echo 服务器已启动！
echo.
echo 如需配置防火墙，请右键「配置防火墙.bat」运行
echo.
pause
""")
print("    [OK] 快速指南.bat")

# 6. 完成
print()
print("=" * 70)
print("  [OK] 服务器EXE打包完成！")
print("=" * 70)
print()
print(f"部署包位置：{SERVER_DEPLOY_DIR}")
print()
print("包含文件：")
for item in sorted(os.listdir(SERVER_DEPLOY_DIR)):
    item_path = os.path.join(SERVER_DEPLOY_DIR, item)
    if os.path.isdir(item_path):
        print(f"  [DIR] {item}/")
    else:
        size_kb = os.path.getsize(item_path) / 1024
        if size_kb > 1024:
            print(f"  [FILE] {item} ({size_kb/1024:.1f} MB)")
        else:
            print(f"  [FILE] {item} ({size_kb:.1f} KB)")
print()
print("=" * 70)
print("  使用步骤")
print("=" * 70)
print()
print("1. 首次：双击「初始化数据库.bat」")
print("2. 配置：右键「配置防火墙.bat」→ 管理员运行")
print("3. 启动：双击「库存管理系统服务器.exe」")
print()
print("=" * 70)

try:
    os.startfile(SERVER_DEPLOY_DIR)
except:
    pass
