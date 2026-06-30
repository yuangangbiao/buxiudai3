# -*- coding: utf-8 -*-
"""
部署包完整性检查工具
"""
import os
import json
import subprocess

print("=" * 70)
print("  部署包完整性检查")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_DIR = os.path.join(BASE_DIR, "最终零依赖EXE部署包")

# 1. 检查部署包目录
print("[1/5] 检查部署包目录...")
if os.path.exists(DEPLOY_DIR):
    print(f"    [OK] 部署包目录存在: {DEPLOY_DIR}")
else:
    print(f"    [ERROR] 部署包目录不存在: {DEPLOY_DIR}")

print()

# 2. 检查文件完整性
print("[2/5] 检查文件完整性...")
required_files = [
    "库存管理客户端.exe",
    "inventory_client_config.json",
    "README - 超级简单使用说明.txt",
    "快速配置.txt",
    "打开本目录.bat"
]

all_files_ok = True
for file in required_files:
    file_path = os.path.join(DEPLOY_DIR, file)
    if os.path.exists(file_path):
        if file.endswith(".exe"):
            size = os.path.getsize(file_path) / (1024 * 1024)
            print(f"    [OK] {file} ({size:.2f} MB)")
        else:
            print(f"    [OK] {file}")
    else:
        print(f"    [ERROR] {file} 缺失")
        all_files_ok = False

print()

# 3. 检查配置文件内容
print("[3/5] 检查配置文件...")
config_path = os.path.join(DEPLOY_DIR, "inventory_client_config.json")
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        print(f"    [OK] 服务器地址: {config.get('server_url')}")
        print(f"    [OK] API密钥: {config.get('api_key')}")
        print(f"    [OK] 自动刷新: {config.get('auto_refresh')}")

print()

# 4. 检查服务器状态
print("[4/5] 检查服务器状态...")
try:
    import requests
    response = requests.get('http://192.168.1.32:8080/api/health', timeout=3)
    if response.status_code == 200:
        data = response.json()
        print(f"    [OK] 服务器运行正常")
        print(f"    [OK] 数据库连接: {data.get('database')}")
        print(f"    [OK] 产品数量: {data.get('stats', {}).get('product_count')}")
    else:
        print(f"    [ERROR] 服务器响应异常: {response.status_code}")
except Exception as e:
    print(f"    [WARN] 无法连接到服务器: {e}")
    print("          请确保服务器已启动")

print()

# 5. 检查EXE版本信息
print("[5/5] 检查EXE信息...")
exe_path = os.path.join(DEPLOY_DIR, "库存管理客户端.exe")
if os.path.exists(exe_path):
    size = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"    [OK] EXE文件大小: {size:.2f} MB")
    
    # 检查是否为有效PE文件
    try:
        with open(exe_path, 'rb') as f:
            header = f.read(2)
            if header == b'MZ':
                print("    [OK] 有效的Windows可执行文件")
            else:
                print("    [ERROR] 不是有效的PE文件")
    except Exception as e:
        print(f"    [ERROR] 无法读取EXE文件: {e}")

print()
print("=" * 70)

# 总结
if all_files_ok:
    print("  [OK] 部署包完整性检查通过！")
else:
    print("  [WARNING] 部分文件缺失，请检查部署包")

print("=" * 70)
print()
print("部署包位置:")
print(f"  {DEPLOY_DIR}")
print()
print("包含文件:")
for file in os.listdir(DEPLOY_DIR):
    print(f"  - {file}")

print()
input("按回车键退出...")
