# -*- coding: utf-8 -*-
"""
服务器端打包完整性检查工具
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_DIR = os.path.join(BASE_DIR, "零依赖服务器EXE部署包")

print("=" * 70)
print("  服务器端打包完整性检查")
print("=" * 70)
print()

# 1. 检查EXE文件
print("[1/5] 检查核心EXE文件...")
exe_path = os.path.join(DEPLOY_DIR, "库存管理系统服务器.exe")
if os.path.exists(exe_path):
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"    [OK] 库存管理系统服务器.exe ({size_mb:.1f} MB)")
else:
    print(f"    [ERROR] 库存管理系统服务器.exe 不存在！")

# 2. 检查核心模块
print()
print("[2/5] 检查核心模块文件...")
required_modules = [
    "inventory_server.py",
    "inventory_db_complete.py",
    "inventory_backup.py",
    "inventory_print.py",
]

for module in required_modules:
    path = os.path.join(DEPLOY_DIR, module)
    if os.path.exists(path):
        size_kb = os.path.getsize(path) / 1024
        print(f"    [OK] {module} ({size_kb:.1f} KB)")
    else:
        print(f"    [ERROR] {module} 不存在！")

# 3. 检查配置文件
print()
print("[3/5] 检查配置文件...")
config_files = [
    "server_config.json",
]

for cfg in config_files:
    path = os.path.join(BASE_DIR, cfg)  # 配置文件在主目录
    if os.path.exists(path):
        print(f"    [OK] {cfg}")
    else:
        print(f"    [WARN] {cfg} 不存在（将在首次运行时创建）")

# 4. 检查脚本文件
print()
print("[4/5] 检查脚本文件...")
scripts = [
    "初始化数据库.bat",
    "配置防火墙.bat",
    "快速指南.bat",
    "使用说明.txt",
]

for script in scripts:
    path = os.path.join(DEPLOY_DIR, script)
    if os.path.exists(path):
        size_kb = os.path.getsize(path) / 1024
        print(f"    [OK] {script} ({size_kb:.1f} KB)")
    else:
        print(f"    [ERROR] {script} 不存在！")

# 5. 检查数据库模块完整性
print()
print("[5/5] 检查数据库模块完整性...")
db_module = os.path.join(DEPLOY_DIR, "inventory_db_complete.py")
if os.path.exists(db_module):
    with open(db_module, 'r', encoding='utf-8') as f:
        content = f.read()
        has_connection = "pymysql.connect" in content
        has_tables = "warehouses" in content and "products" in content
        if has_connection and has_tables:
            print(f"    [OK] 数据库模块包含必要的连接和表结构")
        else:
            print(f"    [WARN] 数据库模块可能不完整")

print()
print("=" * 70)
print("  检查完成")
print("=" * 70)
print()

# 总结
all_files = [
    "库存管理系统服务器.exe",
    "inventory_server.py",
    "inventory_db_complete.py",
    "inventory_backup.py",
    "inventory_print.py",
    "初始化数据库.bat",
    "配置防火墙.bat",
    "使用说明.txt",
]

missing = []
for f in all_files:
    if not os.path.exists(os.path.join(DEPLOY_DIR, f)):
        missing.append(f)

if missing:
    print(f"[ERROR] 缺少以下文件：")
    for f in missing:
        print(f"    - {f}")
else:
    print("[OK] 所有必要文件完整！")
    print()
    print("服务器端打包验证通过！")
    print()
    print("部署包位置：")
    print(f"  {DEPLOY_DIR}")
    print()

print("=" * 70)
