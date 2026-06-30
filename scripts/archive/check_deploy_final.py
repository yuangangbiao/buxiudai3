# -*- coding: utf-8 -*-
"""
整理部署包 - 删除空目录并检查完整性
"""
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_DIR = os.path.join(BASE_DIR, "部署包")

# 删除空的完整功能EXE部署包
empty_dir = os.path.join(DEPLOY_DIR, "完整功能EXE部署包")
if os.path.exists(empty_dir) and not os.listdir(empty_dir):
    os.rmdir(empty_dir)
    print(f"已删除空目录: 完整功能EXE部署包")

# 检查服务器端部署包是否缺少EXE
server_dir = os.path.join(DEPLOY_DIR, "零依赖服务器EXE部署包")
has_exe = any(f.endswith('.exe') for f in os.listdir(server_dir))

if not has_exe:
    print()
    print("⚠️ 警告: 服务器端部署包缺少EXE文件！")
    print("需要重新打包服务器端。")
    print()

# 显示最终结构
print("=" * 70)
print("  最终部署包结构")
print("=" * 70)
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
            print(f"│   └── ({len(other_files)} 个配置文件和脚本)")

print()
print("测试工具:")
print("└── 测试工具/")
print("    └── 测试工具包/")
