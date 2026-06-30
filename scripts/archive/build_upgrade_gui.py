# -*- coding: utf-8 -*-
"""
打包数据库修复升级包（带GUI）
"""
import os
import subprocess
import sys

OUTPUT_DIR = r"d:\升级包"
BUILD_DIR = r"d:\yuan\不锈钢网带跟单3.0\build"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

cmd = [
    r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
    "--onefile",
    "--windowed",
    "--name=订单修复升级包v3",
    f"--distpath={OUTPUT_DIR}",
    f"--workpath={BUILD_DIR}",
    "--clean",
    "--add-data=.env;.",
    "--hidden-import=pymysql",
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.messagebox",
    "升级包/upgrade_v3_order_fix.py"
]

print("开始打包...")
result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')

if result.returncode == 0:
    print("\n✅ 打包成功!")
    print(f"输出文件: {OUTPUT_DIR}\\订单修复升级包v3.exe")
else:
    print("\n❌ 打包失败!")
    print("错误输出:")
    print(result.stderr)
    print(result.stdout)
