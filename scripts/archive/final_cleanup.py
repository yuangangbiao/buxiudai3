# -*- coding: utf-8 -*-
"""
彻底清理部署包 - 删除源代码和旧构建目录
"""
import os
import shutil

print("=" * 70)
print("  彻底清理部署包")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_DIR = os.path.join(BASE_DIR, "部署包")

# 删除旧的构建目录
print("删除旧的构建目录...")
old_build_dirs = [
    "client_build",
    "client_build_exe",
    "client_final_complete",
    "server_build_exe",
]

for dir_name in old_build_dirs:
    dir_path = os.path.join(DEPLOY_DIR, dir_name)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
        print(f"    [DELETED] {dir_name}")
    else:
        print(f"    [SKIP] {dir_name} 不存在")

print()

# 删除压缩包
print("删除压缩包...")
rar_file = os.path.join(DEPLOY_DIR, "最终零依赖EXE部署包.rar")
if os.path.exists(rar_file):
    os.remove(rar_file)
    print(f"    [DELETED] 最终零依赖EXE部署包.rar")
else:
    print("    [SKIP] 压缩包不存在")

print()

# 删除各部署包中的源代码文件
print("删除源代码文件...")

# 最终零依赖EXE部署包
final_client_dir = os.path.join(DEPLOY_DIR, "最终零依赖EXE部署包")
for f in os.listdir(final_client_dir):
    if f.endswith('.py'):
        os.remove(os.path.join(final_client_dir, f))
        print(f"    [DELETED] 最终零依赖EXE部署包/{f}")

# 零依赖客户端部署包
simple_client_dir = os.path.join(DEPLOY_DIR, "零依赖客户端部署包")
for f in os.listdir(simple_client_dir):
    if f.endswith('.py'):
        os.remove(os.path.join(simple_client_dir, f))
        print(f"    [DELETED] 零依赖客户端部署包/{f}")

# 零依赖服务器EXE部署包
server_dir = os.path.join(DEPLOY_DIR, "零依赖服务器EXE部署包")
for f in os.listdir(server_dir):
    if f.endswith('.py'):
        os.remove(os.path.join(server_dir, f))
        print(f"    [DELETED] 零依赖服务器EXE部署包/{f}")

print()
print("=" * 70)
print("  [OK] 清理完成！")
print("=" * 70)
print()
print("最终部署包结构:")
print()

for item in os.listdir(DEPLOY_DIR):
    item_path = os.path.join(DEPLOY_DIR, item)
    if os.path.isdir(item_path):
        print(f"├── {item}/")
        files = os.listdir(item_path)
        exe_files = [f for f in files if f.endswith('.exe')]
        other_files = [f for f in files if not f.endswith('.exe')]
        
        for exe in exe_files:
            size = os.path.getsize(os.path.join(item_path, exe)) / (1024 * 1024)
            print(f"│   └── {exe} ({size:.2f} MB)")
        
        if other_files:
            print(f"│   └── (配置文件和脚本)")

print()
print("└── 测试工具/")
print("    └── 测试工具包/")

# 打开部署包目录
try:
    os.startfile(DEPLOY_DIR)
except Exception as e:
    print(f"打开部署包目录失败: {e}")
