# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil

# 清理旧的构建文件
build_dir = r"d:\yuan\不锈钢网带跟单3.0\build"
dist_dir = r"d:\升级包"

if os.path.exists(build_dir):
    shutil.rmtree(build_dir)
    print(f"已清理: {build_dir}")

# 清理 __pycache__
for root, dirs, files in os.walk(r"d:\yuan\不锈钢网带跟单3.0"):
    if "__pycache__" in dirs:
        pycache = os.path.join(root, "__pycache__")
        shutil.rmtree(pycache)
        print(f"已清理: {pycache}")

os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

cmd = [
    sys.executable,
    r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
    "--onefile",
    "--windowed",
    "--name=订单修复升级包v3",
    "--distpath=d:\\升级包",
    "--workpath=d:\\yuan\\不锈钢网带跟单3.0\\build",
    "--clean",
    "--hidden-import=pymysql",
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.messagebox",
    "--exclude-module=cryptography",
    "--noconfirm",
    "升级包/upgrade_v3_order_fix.py"
]

print("开始打包...")
result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')

if result.returncode == 0:
    print("\n✅ 打包成功!")
    print(f"输出文件: d:\\升级包\\订单修复升级包v3.exe")
else:
    print("\n❌ 打包失败!")
    print("错误输出:")
    print(result.stderr[:2000] if len(result.stderr) > 2000 else result.stderr)