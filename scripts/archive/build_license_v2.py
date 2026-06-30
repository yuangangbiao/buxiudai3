# -*- coding: utf-8 -*-
"""
不锈钢输送网带跟单系统 - 带机器指纹加密版打包脚本(直接命令版)
"""
import subprocess
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYINSTALLER_PATH = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe"

# 清理旧的临时目录
temp_dir = os.path.join(BASE_DIR, "temp_license_build")
build_dir = os.path.join(BASE_DIR, "build_license_temp")

for td in [temp_dir, build_dir]:
    if os.path.exists(td):
        shutil.rmtree(td)

os.makedirs(temp_dir)

# 完整打包命令 - 包含所有模块
cmd = [
    PYINSTALLER_PATH,
    "--onefile",
    "--windowed",
    "--name=不锈钢网带跟单系统(加密版)",
    f"--distpath={temp_dir}",
    f"--workpath={build_dir}",
    "--clean",
    # 数据库
    "--collect-all=pymysql",
    # tkinter
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.ttk",
    "--hidden-import=tkinter.messagebox",
    "--hidden-import=tkinter.filedialog",
    "--hidden-import=tkinter.colorchooser",
    "--hidden-import=tkinter.commondialog",
    # dotenv
    "--collect-all=dotenv",
    # 图像处理
    "--collect-submodules=PIL",
    "--collect-submodules=cv2",
    # numpy
    "--collect-submodules=numpy",
    # pandas
    "--collect-submodules=pandas",
    # openpyxl
    "--collect-all=openpyxl",
    # 日期时间
    "--collect-all=python-dateutil",
    # 安全模块 - 机器指纹加密
    "--hidden-import=security",
    "--hidden-import=security.machine_fingerprint",
    "--hidden-import=security.license_binding",
    "--hidden-import=security.license_manager",
    "--hidden-import=security.license_tool",
    "--hidden-import=security.fingerprint_tool",
    # 添加security目录
    "--add-data=security;security",
    "main.py"
]

print("=" * 70)
print("  Stainless Steel Belt Tracking System (License Encrypted) Packer")
print("=" * 70)
print()
print("Security Features:")
print("   - Machine Fingerprint (CPU+Disk+Motherboard+BIOS)")
print("   - SHA-256 Hash")
print("   - License Binding Encrypted Storage")
print("   - One-machine-one-code Verification")
print()
print("Packing in progress, please wait...")
print()

result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')

if result.returncode == 0:
    print("[OK] 打包成功！")
    exe_path = os.path.join(temp_dir, "不锈钢网带跟单系统(加密版).exe")
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"    文件: {exe_path}")
        print(f"    大小: {size:.2f} MB")

        # 复制到dist目录
        dist_dir = os.path.join(BASE_DIR, "dist")
        os.makedirs(dist_dir, exist_ok=True)
        target_exe = os.path.join(dist_dir, "不锈钢网带跟单系统(加密版).exe")
        shutil.copy2(exe_path, target_exe)
        print(f"    已复制到: {target_exe}")

        # 检查警告
        if "missing module" in result.stderr.lower():
            print()
            print("WARNING: Missing modules:")
            lines = result.stderr.split('\n')
            for line in lines:
                if "missing module" in line.lower():
                    print(f"   {line.strip()}")
    else:
        print("[FAIL] EXE文件未生成！")
        print("STDERR:", result.stderr[-2000:])
else:
    print("[FAIL] 打包失败！")
    print("STDOUT:", result.stdout[-2000:])
    print("STDERR:", result.stderr[-2000:])

input("\n按回车键退出...")