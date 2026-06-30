# -*- coding: utf-8 -*-
"""
检查部署包完整性
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_DIR = os.path.join(BASE_DIR, "部署包")

print("=" * 70)
print("  部署包完整性检查")
print("=" * 70)
print()

def check_package(name, required_files):
    print(f"【{name}】")
    pkg_dir = os.path.join(DEPLOY_DIR, name)
    if not os.path.exists(pkg_dir):
        print(f"    [ERROR] 目录不存在: {pkg_dir}")
        return False

    all_exist = True
    for f in required_files:
        fpath = os.path.join(pkg_dir, f)
        if os.path.exists(fpath):
            if f.endswith('.exe'):
                size = os.path.getsize(fpath) / (1024 * 1024)
                print(f"    [OK] {f} ({size:.2f} MB)")
            else:
                print(f"    [OK] {f}")
        else:
            print(f"    [MISSING] {f}")
            all_exist = False

    return all_exist

# 检查服务端
server_ok = check_package("服务端", [
    "库存管理系统服务器.exe",
    "inventory_server.py",
    "inventory_db_complete.py",
    "inventory_backup.py",
    "inventory_print.py",
    "inventory_manager_complete.py",
    "server_config.json",
])

print()

# 检查客户端完整功能版
client_ok = check_package("客户端完整功能版", [
    "库存管理完整版.exe",
    "库存管理客户端.exe",
    "inventory_client_config.json",
    "server_client_config.json",
])

print()

# 总结
print("=" * 70)
print("  检查结果")
print("=" * 70)

if server_ok and client_ok:
    print("[PASS] 所有部署包完整！")
else:
    print("[FAIL] 部分文件缺失！")

print()
print("部署包位置:")
print(f"  {DEPLOY_DIR}")
