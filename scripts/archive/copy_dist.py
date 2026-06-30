# -*- coding: utf-8 -*-
"""复制打包文件到目标目录"""
import shutil
import os

base_dir = r"d:\yuan\不锈钢网带跟单3.0"
target_dir = r"F:\智能跟单系统\v3.0"

os.makedirs(target_dir, exist_ok=True)

src_exe = os.path.join(base_dir, "dist", "不锈钢网带跟单系统v3.0.exe")
dst_exe = os.path.join(target_dir, "不锈钢网带跟单系统v3.0.exe")

if os.path.exists(src_exe):
    shutil.copy2(src_exe, dst_exe)
    size = os.path.getsize(dst_exe) / (1024 * 1024)
    print(f"[OK] EXE已复制: {dst_exe}")
    print(f"     大小: {size:.2f} MB")
else:
    print(f"[FAIL] 源EXE不存在: {src_exe}")

config_files = ['.env', 'config.py', 'db_config.py', 'version.py']
for cf in config_files:
    src = os.path.join(base_dir, cf)
    if os.path.exists(src):
        dst = os.path.join(target_dir, cf)
        shutil.copy2(src, dst)
        print(f"[OK] 已复制: {cf}")

print()
print(f"完成！所有文件已复制到: {target_dir}")