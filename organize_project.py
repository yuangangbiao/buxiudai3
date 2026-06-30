# -*- coding: utf-8 -*-
"""
整理项目结构，将工具和部署包分类存放
"""
import os
import shutil

print("=" * 70)
print("  整理项目结构")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 定义目标文件夹结构
folders = {
    "部署包": [
        "最终零依赖EXE部署包",
        "零依赖服务器EXE部署包",
        "零依赖客户端部署包",
        "零依赖服务器部署包",
        "完整功能EXE部署包",
        "完整功能客户端部署包",
        "最终一键复制部署包",
        "完整零依赖部署包",
        "client_final_complete",
        "server_build_exe",
        "client_build_exe",
        "client_build",
    ],
    "测试工具": [
        "测试工具包",
    ],
    "打包脚本": [
        "build_full_client_exe.py",
        "build_server_exe.py",
        "create_deploy_package.py",
        "create_final_package.py",
        "create_full_client.py",
        "create_verified_deployment.py",
        "create_test_tools.py",
        "create_server_deploy.py",
        "create_complete_zero_dep.py",
        "finalize_exe_deploy.py",
        "full_build_client.py",
        "package_exe_now.py",
        "update_deploy_packages.py",
    ],
    "诊断工具": [
        "服务器诊断.py",
        "客户端诊断修复.py",
        "check_deploy_integrity.py",
        "check_server_deploy.py",
    ],
}

# 创建文件夹
for category, items in folders.items():
    category_dir = os.path.join(BASE_DIR, category)
    os.makedirs(category_dir, exist_ok=True)
    print(f"创建目录: {category}")
    
    for item in items:
        src_path = os.path.join(BASE_DIR, item)
        dst_path = os.path.join(category_dir, item)
        
        if os.path.exists(src_path):
            # 如果目标已存在且是目录，先删除
            if os.path.exists(dst_path):
                if os.path.isdir(dst_path):
                    shutil.rmtree(dst_path)
                else:
                    os.remove(dst_path)
            
            # 移动文件/文件夹
            if os.path.isdir(src_path):
                shutil.move(src_path, dst_path)
                print(f"    [OK] 移动目录: {item}")
            else:
                shutil.move(src_path, dst_path)
                print(f"    [OK] 移动文件: {item}")
        else:
            print(f"    [SKIP] {item} 不存在")
    
    print()

print("=" * 70)
print("  [OK] 整理完成！")
print("=" * 70)
print()
print("项目结构:")
print()

# 显示最终结构
for category in folders.keys():
    category_dir = os.path.join(BASE_DIR, category)
    if os.path.exists(category_dir):
        items = os.listdir(category_dir)
        print(f"├── {category}/")
        for item in items[:5]:  # 最多显示5个
            print(f"│   └── {item}")
        if len(items) > 5:
            print(f"│   └── ... (共{len(items)}个)")
        print()

# 显示根目录剩余文件
root_items = [f for f in os.listdir(BASE_DIR) if os.path.isfile(os.path.join(BASE_DIR, f)) and f.endswith('.py')]
print(f"├── 主程序文件 ({len(root_items)}个)")
print("│   ├── inventory_client.py")
print("│   ├── inventory_server.py")
print("│   ├── main.py")
print("│   └── ...")
print()

# 打开部署包目录
try:
    os.startfile(os.path.join(BASE_DIR, "部署包"))
except Exception as e:
    print(f"打开部署包目录失败: {e}")
