# -*- coding: utf-8 -*-
import subprocess
import sys
import os

os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

work_dir = r"d:\yuan\不锈钢网带跟单3.0\build_dashboard_run"
if os.path.exists(work_dir):
    import shutil
    shutil.rmtree(work_dir)

pyinstaller_path = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe"
source_file = r"d:\yuan\不锈钢网带跟单3.0\run_dashboard.py"
dist_path = r"d:\yuan\不锈钢网带跟单3.0\dist"

cmd = [
    pyinstaller_path,
    "--onefile",
    "--windowed",
    "--name=大屏服务器",
    f"--distpath={dist_path}",
    f"--workpath={work_dir}",
    "--clean",
    "--exclude-module=cryptography",
    "--noconfirm",
    source_file
]

print("Building dashboard server launcher...")
result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')

if result.returncode == 0:
    print("Build successful!")
    src = os.path.join(dist_path, "大屏服务器.exe")
    if os.path.exists(src):
        print(f"Created: {src}")
else:
    print("Build failed:")
    print(result.stderr[:2000] if result.stderr else result.stdout)
