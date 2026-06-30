# -*- coding: utf-8 -*-
"""
库存管理系统 - 零依赖服务器端打包工具
包含独立数据库，一键部署
"""
import os
import sys
import shutil
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DEPLOY_DIR = os.path.join(BASE_DIR, "零依赖服务器部署包")

print("=" * 70)
print("  库存管理系统 - 零依赖服务器端打包")
print("=" * 70)
print()

# 1. 清理目录
print("[1/6] 准备部署目录...")
if os.path.exists(SERVER_DEPLOY_DIR):
    shutil.rmtree(SERVER_DEPLOY_DIR)
os.makedirs(SERVER_DEPLOY_DIR)

# 2. 复制核心文件
print()
print("[2/6] 复制核心文件...")

files_to_copy = [
    "inventory_server.py",
    "inventory_db_complete.py",
    "inventory_backup.py",
    "inventory_print.py",
    "inventory_manager_complete.py",
]

for f in files_to_copy:
    src = os.path.join(BASE_DIR, f)
    if os.path.exists(src):
        shutil.copy2(src, SERVER_DEPLOY_DIR)
        print(f"    [OK] {f}")

# 3. 创建配置和脚本
print()
print("[3/6] 创建配置文件...")

# 服务器配置
with open(os.path.join(SERVER_DEPLOY_DIR, "server_config.json"), 'w', encoding='utf-8') as f:
    f.write("""{
    "host": "0.0.0.0",
    "port": 8080,
    "api_key": "${INVENTORY_API_KEY}"
}""")
print("    [OK] server_config.json")

# 启动脚本
with open(os.path.join(SERVER_DEPLOY_DIR, "启动服务器.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 库存管理系统 - 服务器
color 0A

echo ============================================================
echo.
echo               库存管理系统 - 服务器
echo.
echo ============================================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python！
    echo.
    pause
    exit /b 1
)
echo [OK] Python环境正常

REM 检查依赖
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖...
    pip install flask requests pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo [OK] 依赖检查完成
echo.
echo ============================================================
echo   正在启动服务器...
echo ============================================================
echo.
echo 服务器配置：
echo   地址: 0.0.0.0:8080
echo   API密钥: steel_belt_inventory_key_2024
echo.
echo   客户端连接地址: http://192.168.1.32:8080
echo.
echo ============================================================
echo.
echo 提示：请保持此窗口开启
echo.
cd /d "%~dp0"
python inventory_server.py

pause
""")
print("    [OK] 启动服务器.bat")

# 4. 创建数据库初始化脚本
print()
print("[4/6] 创建数据库初始化脚本...")

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

echo 此工具将：
echo   1. 创建独立的库存数据库
echo   2. 创建所有必要的表
echo   3. 初始化基础数据
echo.
echo 注意：不会影响跟单系统的主数据库！
echo.
echo ============================================================
echo.

set /p confirm=确认继续？(Y/N): 
if /i not "%confirm%"=="Y" (
    echo 操作已取消
    pause
    exit /b
)

echo.
echo 正在检查依赖...
python -c "import pymysql" >nul 2>&1
if errorlevel 1 (
    echo 正在安装 pymysql...
    pip install pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo 正在初始化数据库...
python -c "
import pymysql
import sys
import os

# 数据库配置
DB_HOST = os.getenv('MYSQL_HOST', 'localhost')
DB_PORT = int(os.getenv('MYSQL_PORT', 3306))
DB_USER = os.getenv('MYSQL_USER', 'root')
DB_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
DB_NAME = os.getenv('MYSQL_DATABASE', 'inventory_management_db')"

print(f'正在连接 MySQL...')

try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    
    print(f'创建数据库 {DB_NAME}...')
    cursor.execute(f'CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    print('[OK] 数据库创建成功')
    
    cursor.execute(f'USE {DB_NAME}')
    
    print('创建表结构...')
    
    # 仓库表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS warehouses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL COMMENT '仓库名称',
        location VARCHAR(200) COMMENT '仓库位置',
        manager VARCHAR(50) COMMENT '负责人',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='仓库表'
    ''')
    print('[OK] 仓库表')
    
    # 供应商表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS suppliers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200) NOT NULL COMMENT '供应商名称',
        contact VARCHAR(100) COMMENT '联系人',
        phone VARCHAR(50) COMMENT '联系电话',
        address VARCHAR(300) COMMENT '地址',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商表'
    ''')
    print('[OK] 供应商表')
    
    # 产品表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_code VARCHAR(50) UNIQUE COMMENT '产品编码',
        product_name VARCHAR(200) NOT NULL COMMENT '产品名称',
        category VARCHAR(100) COMMENT '分类',
        unit VARCHAR(20) DEFAULT '个' COMMENT '单位',
        spec VARCHAR(200) COMMENT '规格',
        safety_stock DECIMAL(10,2) DEFAULT 0 COMMENT '安全库存',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品表'
    ''')
    print('[OK] 产品表')
    
    # 库存表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        id INT AUTO_INCREMENT PRIMARY KEY,
        warehouse_id INT COMMENT '仓库ID',
        product_id INT NOT NULL COMMENT '产品ID',
        quantity DECIMAL(10,2) DEFAULT 0 COMMENT '当前库存',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存表'
    ''')
    print('[OK] 库存表')
    
    # 出入库记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        type ENUM('inbound', 'outbound') NOT NULL COMMENT '类型：inbound入库/outbound出库',
        product_id INT NOT NULL COMMENT '产品ID',
        warehouse_id INT COMMENT '仓库ID',
        quantity DECIMAL(10,2) NOT NULL COMMENT '数量',
        operator VARCHAR(50) COMMENT '操作员',
        reference_no VARCHAR(100) COMMENT '参考单号',
        notes TEXT COMMENT '备注',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='出入库记录表'
    ''')
    print('[OK] 出入库记录表')
    
    # 通知表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        type VARCHAR(50) NOT NULL COMMENT '通知类型',
        title VARCHAR(200) NOT NULL COMMENT '标题',
        content TEXT COMMENT '内容',
        level ENUM('info', 'warning', 'error') DEFAULT 'info' COMMENT '级别',
        is_read TINYINT DEFAULT 0 COMMENT '是否已读',
        response VARCHAR(50) COMMENT '响应',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知表'
    ''')
    print('[OK] 通知表')
    
    # 插入默认仓库
    cursor.execute("SELECT COUNT(*) FROM warehouses")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''INSERT INTO warehouses (name, location, manager) VALUES ('主仓库', '默认位置', '管理员')''')
        print('[OK] 默认仓库')
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print()
    print('=' * 50)
    print('  [OK] 数据库初始化成功！')
    print('=' * 50)
    print()
    print(f'数据库名称: {DB_NAME}')
    print('数据库位置: localhost:3306')
    print()
    print('注意：此数据库与跟单系统完全独立！')
    print()
    
except Exception as e:
    print()
    print('=' * 50)
    print(f'  [错误] 数据库初始化失败: {e}')
    print('=' * 50)
    sys.exit(1)

pause
""")
print("    [OK] 初始化数据库.bat")

# 5. 创建说明文档
print()
print("[5/6] 创建说明文档...")

with open(os.path.join(SERVER_DEPLOY_DIR, "README - 服务器部署说明.txt"), 'w', encoding='utf-8') as f:
    f.write("""# 库存管理系统 - 服务器端部署说明

## 系统说明

本系统为**库存管理系统独立服务器端**，
使用独立的数据库（inventory_management_db），
不会影响跟单系统的主数据库（steel_belt）。

---

## 部署步骤

### 第一步：初始化数据库（仅第一次）

1. 双击「初始化数据库.bat」
2. 输入 Y 确认
3. 等待数据库创建完成

### 第二步：启动服务器

1. 双击「启动服务器.bat」
2. 看到 "Running on http://0.0.0.0:8080" 表示成功
3. **保持窗口不要关闭**

### 第三步：配置防火墙（重要！）

1. 右键点击「配置防火墙.bat」
2. 选择「以管理员身份运行」
3. 这会开放8080端口，让客户端能连接

---

## 数据库说明

### 独立数据库
- 数据库名称：`inventory_management_db`
- 端口：3306
- 与跟单系统数据库（`steel_belt`）完全独立
- 不会影响跟单系统的任何数据

### 数据表结构
- `warehouses` - 仓库表
- `suppliers` - 供应商表
- `products` - 产品表
- `inventory` - 库存表
- `transactions` - 出入库记录表
- `notifications` - 通知表

---

## 客户端连接信息

- 服务器地址：http://192.168.1.32:8080
- API密钥：steel_belt_inventory_key_2024

---

## 常见问题

Q: 数据库初始化失败？
A: 检查：
   - MySQL服务是否启动？
   - 用户名密码是否正确（root/88888888）？
   - 是否有创建数据库的权限？

Q: 服务器启动失败？
A: 检查：
   - 端口8080是否被占用？
   - 数据库是否已初始化？

Q: 客户端无法连接？
A: 检查：
   - 服务器是否已启动？
   - 防火墙是否已配置？
   - IP地址是否正确？

---

## 文件说明

- inventory_server.py     → API服务器程序
- inventory_db_complete.py → 数据库操作模块
- inventory_backup.py     → 备份模块
- inventory_print.py      → 打印模块
- inventory_manager_complete.py → 管理界面
- server_config.json      → 服务器配置
- 启动服务器.bat         → 服务器启动脚本
- 初始化数据库.bat        → 数据库初始化脚本
- 配置防火墙.bat         → 防火墙配置脚本
- README - 服务器部署说明.txt → 本文档

---

## 安全建议

1. API密钥已设置，请妥善保管
2. 建议在局域网内使用
3. 定期备份数据库
4. 防火墙仅开放必要端口

---

版本：1.0
日期：2026-04-30
""")
print("    [OK] README - 服务器部署说明.txt")

# 快速配置
with open(os.path.join(SERVER_DEPLOY_DIR, "快速配置.txt"), 'w', encoding='utf-8') as f:
    f.write("""# 快速配置 - 3步

## 第一步：初始化数据库（仅第一次）
双击「初始化数据库.bat」→ 输入 Y → 等待完成

## 第二步：启动服务器
双击「启动服务器.bat」→ 看到启动成功信息

## 第三步：配置防火墙（重要！）
右键「配置防火墙.bat」→ 以管理员身份运行

---

## 客户端连接信息

- 服务器地址：http://192.168.1.32:8080
- API密钥：steel_belt_inventory_key_2024

---

就这么简单！
""")
print("    [OK] 快速配置.txt")

# 防火墙配置脚本
with open(os.path.join(SERVER_DEPLOY_DIR, "配置防火墙.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 库存管理系统 - 防火墙配置

echo ============================================================
echo            库存管理系统 - 防火墙配置
echo ============================================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 需要管理员权限！
    echo.
    echo 请右键点击「以管理员身份运行」
    echo.
    pause
    exit /b 1
)

echo [1/2] 添加防火墙规则（开放8080端口）...
netsh advfirewall firewall add rule name="库存管理系统8080" dir=in action=allow protocol=TCP localport=8080 >nul 2>&1

if %errorlevel% equ 0 (
    echo     [OK] 规则添加成功
) else (
    echo     [OK] 规则可能已存在
)

echo.
echo [2/2] 验证规则...
netsh advfirewall firewall show rule name="库存管理系统8080" | findstr "库存管理系统8080"
if errorlevel 1 (
    echo     验证完成
) else (
    echo     [OK] 规则验证成功
)

echo.
echo ============================================================
echo   防火墙配置完成！
echo ============================================================
echo.
echo 客户端现在可以连接服务器了！
echo.
echo 服务器地址: http://192.168.1.32:8080
echo.
pause
""")
print("    [OK] 配置防火墙.bat")

# 6. 完成
print()
print("=" * 70)
print("  [OK] 零依赖服务器部署包创建完成！")
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
        print(f"  [FILE] {item} ({size_kb:.1f} KB)")
print()
print("=" * 70)
print("  部署步骤")
print("=" * 70)
print()
print("1. 初始化数据库（仅第一次）：双击「初始化数据库.bat」")
print("2. 启动服务器：双击「启动服务器.bat」")
print("3. 配置防火墙：右键「配置防火墙.bat」→ 管理员运行")
print()
print("=" * 70)

# 尝试打开目录
try:
    os.startfile(SERVER_DEPLOY_DIR)
except:
    pass
