
# -*- coding: utf-8 -*-
"""
打包库存管理系统（带批量出入库和打印功能）
"""
import os
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp_inventory_exe")
BUILD_DIR = os.path.join(BASE_DIR, "temp_inventory_build")
TARGET_DIR = r"F:\智能跟单系统\库存管理系统\客户端"

print("=" * 70)
print("  库存管理系统 - EXE打包")
print("=" * 70)
print()

# 1. 清理旧目录
print("[1/4] 清理临时目录...")
if os.path.exists(TEMP_DIR):
    shutil.rmtree(TEMP_DIR)
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)
os.makedirs(TEMP_DIR)

# 2. 打包命令
print()
print("[2/4] 开始打包...")

cmd = [
    r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
    "--onefile",
    "--windowed",
    "--name=库存管理系统",
    f"--distpath={TEMP_DIR}",
    f"--workpath={BUILD_DIR}",
    "--clean",
    "--hidden-import=pymysql",
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.ttk",
    "--hidden-import=tkinter.messagebox",
    "--hidden-import=tkinter.filedialog",
    "--hidden-import=openpyxl",
    "inventory_manager_complete.py"
]

print(f"命令: {' '.join(cmd)}")
print()
print("注意：打包过程需要2-5分钟，请耐心等待...")
print()

result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')

if result.returncode == 0:
    print("[OK] 打包成功！")
    exe_path = os.path.join(TEMP_DIR, "库存管理系统.exe")
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"    文件: {exe_path}")
        print(f"    大小: {size:.2f} MB")
        
        # 3. 复制到目标位置
        print()
        print("[3/4] 复制到目标位置...")
        
        if not os.path.exists(TARGET_DIR):
            os.makedirs(TARGET_DIR)
        
        target_path = os.path.join(TARGET_DIR, "库存管理系统.exe")
        if os.path.exists(target_path):
            os.remove(target_path)
        
        shutil.copy2(exe_path, target_path)
        print(f"    [OK] 已复制到: {target_path}")
        
        # 复制配置文件
        config_src = os.path.join(BASE_DIR, "inventory_config.json")
        config_dst = os.path.join(TARGET_DIR, "inventory_config.json")
        if os.path.exists(config_src):
            shutil.copy2(config_src, config_dst)
            print(f"    [OK] 已复制配置文件")
        
        # 4. 验证
        print()
        print("[4/4] 验证完整性...")
        
        if os.path.exists(target_path):
            print("    [OK] EXE文件存在")
            file_size = os.path.getsize(target_path) / (1024 * 1024)
            print(f"    [OK] 文件大小: {file_size:.2f} MB")
            
            if os.path.exists(config_dst):
                print("    [OK] 配置文件存在")
            
            print()
            print("=" * 70)
            print("  ✅ 打包完成！")
            print("=" * 70)
            print()
            print(f"EXE文件位置: {target_path}")
            print()
            print("功能包含:")
            print("  ✅ 批量入库")
            print("  ✅ 批量出库")
            print("  ✅ 库存查询")
            print("  ✅ 打印功能")
            print("  ✅ 数据备份")
            print()
            print("使用方法:")
            print("  1. 双击「库存管理系统.exe」启动")
            print("  2. 配置数据库连接（如果需要）")
            print("  3. 开始使用")
            print()
            print("=" * 70)
        else:
            print("[FAIL] EXE文件未复制成功！")
    else:
        print("[FAIL] EXE文件未生成！")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
else:
    print("[FAIL] 打包失败！")
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
