# -*- coding: utf-8 -*-
"""
打包MySQL版库存管理系统为EXE
"""
import os
import subprocess
import shutil
import sys

print("=" * 70)
print("  打包MySQL版库存管理系统")
print("=" * 70)
print()

BASE_DIR = r"d:\yuan\不锈钢网带跟单3.0"
CLIENT_FILE = os.path.join(BASE_DIR, "inventory_manager_complete.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "完整EXE部署包_MySQL版")
TEMP_DIR = os.path.join(BASE_DIR, "temp_complete_exe")

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

if os.path.exists(TEMP_DIR):
    shutil.rmtree(TEMP_DIR)

print("开始打包...")
print(f"源文件: {CLIENT_FILE}")
print(f"输出目录: {OUTPUT_DIR}")
print()

command = [
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name=库存管理系统_MySQL版",
    "--distpath", TEMP_DIR,
    "--workpath", os.path.join(BASE_DIR, "build_temp"),
    "--specpath", BASE_DIR,
    "--hidden-import=requests",
    "--hidden-import=mysql.connector",
    "--hidden-import=tkinter",
    "--hidden-import=ttk",
    "--hidden-import=json",
    "--hidden-import=threading",
    "--hidden-import=datetime",
    "--hidden-import=os",
    "--hidden-import=sys",
    "--hidden-import=pickle",
    "--hidden-import=hashlib",
    "--collect-all=tkinter",
    CLIENT_FILE
]

print("执行打包命令...")
result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore')

if result.returncode == 0:
    print("[OK] 打包成功!")
    exe_path = os.path.join(TEMP_DIR, "库存管理系统_MySQL版.exe")
    if os.path.exists(exe_path):
        final_path = os.path.join(OUTPUT_DIR, "库存管理系统_MySQL版.exe")
        shutil.copy2(exe_path, final_path)
        print(f"EXE已复制到: {final_path}")
        print(f"文件大小: {os.path.getsize(final_path) / 1024 / 1024:.2f} MB")
    else:
        print("[ERROR] 未找到生成的EXE文件")
else:
    print("[ERROR] 打包失败!")
    print("错误输出:", result.stderr[-1000:] if result.stderr else "无")

print()
print("=" * 70)
