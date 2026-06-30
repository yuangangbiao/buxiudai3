# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil

os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

build_dir = r"d:\yuan\不锈钢网带跟单3.0\build_sync"
if os.path.exists(build_dir):
    shutil.rmtree(build_dir)

cmd = [
    sys.executable,
    r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
    "--onefile",
    "--windowed",
    "--name=数据库表结构同步工具",
    "--distpath=d:\\升级包",
    "--workpath=d:\\yuan\\不锈钢网带跟单3.0\\build_sync",
    "--clean",
    "--exclude-module=cryptography",
    "--noconfirm",
    "d:\\升级包\\数据库表结构同步工具.py"
]

print("打包数据库表结构同步工具...")
result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')

if result.returncode == 0:
    print("✅ 打包成功: d:\\升级包\\数据库表结构同步工具.exe")
else:
    print("❌ 打包失败:")
    print(result.stderr[:1000] if result.stderr else result.stdout)
