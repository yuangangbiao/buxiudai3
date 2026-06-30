# -*- coding: utf-8 -*-
"""
精简部署包 - 只保留EXE格式的最终版本
"""
import os
import shutil

print("=" * 70)
print("  精简部署包 - 只保留EXE版本")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_DIR = os.path.join(BASE_DIR, "部署包")

# 需要保留的文件/文件夹
keep_items = [
    # 服务器端
    "零依赖服务器EXE部署包",
    
    # 客户端 - 完整功能版
    "最终零依赖EXE部署包",
    "完整功能EXE部署包",
    
    # 客户端 - 简版
    "零依赖客户端部署包",
]

# 需要删除的文件/文件夹
delete_items = [
    # 源代码版部署包
    "零依赖服务器部署包",
    "完整功能客户端部署包",
    "最终一键复制部署包",
    "完整零依赖部署包",
    
    # 旧的构建目录
    "client_final_complete",
    "server_build_exe",
    "client_build_exe",
    "client_build",
]

# 删除不需要的项目
print("删除不需要的部署包...")
for item in delete_items:
    item_path = os.path.join(DEPLOY_DIR, item)
    if os.path.exists(item_path):
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
            print(f"    [DELETED] {item}")
        else:
            os.remove(item_path)
            print(f"    [DELETED] {item}")
    else:
        print(f"    [SKIP] {item} 不存在")

print()

# 验证保留的项目
print("保留的部署包...")
for item in keep_items:
    item_path = os.path.join(DEPLOY_DIR, item)
    if os.path.exists(item_path):
        # 检查是否包含EXE文件
        has_exe = any(f.endswith('.exe') for f in os.listdir(item_path))
        status = "✅" if has_exe else "⚠️"
        print(f"    [{status}] {item}")
    else:
        print(f"    [MISSING] {item}")

print()
print("=" * 70)
print("  [OK] 精简完成！")
print("=" * 70)
print()
print("保留的部署包:")
print()
print("├── 部署包/")
for item in keep_items:
    print(f"│   └── {item}/")
    item_path = os.path.join(DEPLOY_DIR, item)
    if os.path.exists(item_path):
        files = [f for f in os.listdir(item_path) if f.endswith('.exe')]
        for exe in files:
            size = os.path.getsize(os.path.join(item_path, exe)) / (1024 * 1024)
            print(f"│       └── {exe} ({size:.2f} MB)")
print()
print("└── 测试工具/")
print("    └── 测试工具包/")

# 打开部署包目录
try:
    os.startfile(DEPLOY_DIR)
except Exception as e:
    print(f"打开部署包目录失败: {e}")
