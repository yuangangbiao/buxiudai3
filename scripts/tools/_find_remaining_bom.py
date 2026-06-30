"""
找出仍含 BOM 的 .py 文件
"""
import os
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
BOM = b'\xef\xbb\xbf'
SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.sandbox_pkgs'}

bom_files = []
for dp, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d not in SKIP_DIRS]
    for fn in fns:
        if fn.endswith(('.py', '.pyi')):
            full = Path(dp) / fn
            try:
                with open(full, 'rb') as f:
                    head = f.read(3)
                if head == BOM:
                    bom_files.append(full)
            except Exception:
                pass

print(f"仍含 BOM 的 .py 文件: {len(bom_files)} 个")
for f in bom_files:
    print(f"  {f.relative_to(ROOT)}")