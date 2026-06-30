# -*- coding: utf-8 -*-
"""
打包inventory_manager_complete.py为完整EXE
"""
import os
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 70)
print("  打包库存管理完整版EXE")
print("=" * 70)
print()

# 清理旧的临时目录
temp_dir = os.path.join(BASE_DIR, "temp_complete_exe")
build_dir = os.path.join(BASE_DIR, "temp_build_complete")

if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
if os.path.exists(build_dir):
    shutil.rmtree(build_dir)

os.makedirs(temp_dir)

# 打包命令 - 使用完整路径
cmd = [
    r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
    "--onefile",
    "--windowed",
    "--name=库存管理系统客户端",
    "--icon=inventory.ico",
    f"--distpath={temp_dir}",
    f"--workpath={build_dir}",
    "--clean",
    "--hidden-import=pymysql",
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.ttk",
    "--hidden-import=tkinter.messagebox",
    "--hidden-import=tkinter.filedialog",
    "inventory_manager_complete.py"
]

print("正在打包，请稍候...")
print(f"命令: {' '.join(cmd)}")
print()

result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')

if result.returncode == 0:
    print("[OK] 打包成功！")
    exe_path = os.path.join(temp_dir, "库存管理系统客户端.exe")
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"    文件: {exe_path}")
        print(f"    大小: {size:.2f} MB")
        
        # 复制到目标位置
        target_dir = r"F:\智能跟单系统\库存管理系统\客户端"
        target_path = os.path.join(target_dir, "库存管理系统客户端.exe")
        
        if os.path.exists(target_path):
            os.remove(target_path)
        
        shutil.copy2(exe_path, target_dir)
        print(f"\n[OK] 已复制到: {target_path}")
        
        # 复制配置文件
        config_src = os.path.join(BASE_DIR, "inventory_config.json")
        config_dst = os.path.join(target_dir, "inventory_config.json")
        if os.path.exists(config_src):
            shutil.copy2(config_src, config_dst)
            print(f"[OK] 已复制配置文件: {config_dst}")
        
        # 验证
        if os.path.exists(target_path):
            print(f"\n[OK] 完整性检查通过！")
            print(f"    客户端EXE: {os.path.getsize(target_path) / (1024 * 1024):.2f} MB")
            if os.path.exists(config_dst):
                print(f"    配置文件: {os.path.getsize(config_dst) / 1024:.2f} KB")
    else:
        print("[FAIL] EXE文件未生成！")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
else:
    print("[FAIL] 打包失败！")
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
