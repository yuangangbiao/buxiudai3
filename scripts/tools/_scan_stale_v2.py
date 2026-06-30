"""
全仓库存量扫描 - 确认当前过期文件剩余量
"""
import os
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
SKIP = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.sandbox_pkgs'}
BOM = b'\xef\xbb\xbf'

def scan(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            yield Path(dp) / fn

# 过期后缀
stats = {}
bom_files = []
for p in scan(ROOT):
    n = p.name
    for s in ('.bak', '.orig', '.old', '.tmp', '.v6bak', '.hash', ',cover'):
        if n.endswith(s):
            stats[s] = stats.get(s, 0) + 1
            break
    if p.suffix in ('.py', '.pyi'):
        try:
            with open(p, 'rb') as f:
                if f.read(3) == BOM:
                    bom_files.append(p)
        except:
            pass

print("=" * 70)
print("过期文件存量")
for k, v in sorted(stats.items()):
    print(f"  {k}: {v}")
print(f"\nBOM 文件: {len(bom_files)}")
for f in bom_files:
    print(f"  {f.relative_to(ROOT)}")
print("=" * 70)

# tests/ 目录专项扫描
print("\n【tests/ 目录过期文件】")
test_stale = []
for p in scan(ROOT / 'tests'):
    n = p.name
    for s in ('.bak', '.orig', '.old', '.v6bak', ',cover', '.hash'):
        if n.endswith(s):
            test_stale.append(p)
            break
print(f"  tests/ 内过期文件: {len(test_stale)} 个")
for f in test_stale:
    print(f"    {f.relative_to(ROOT)}")
print("=" * 70)