# -*- coding: utf-8 -*-
import subprocess
import sys
import os

base_dir = r"d:\yuan\不锈钢网带跟单3.0"
spec_file = os.path.join(base_dir, "不锈钢网带跟单系统v3.0.spec")

pyinstaller = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe"

cmd = [pyinstaller, "--clean", "--noconfirm", spec_file]

print(f"Running: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=base_dir, encoding="gbk")

print(f"Return code: {result.returncode}")
if result.stdout:
    print("STDOUT:", result.stdout[:2000])
if result.stderr:
    print("STDERR:", result.stderr[:2000])