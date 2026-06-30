"""
删除 27 个 .bak_bom 保险备份文件（BOM 修复前的快照）
"""
import os
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.sandbox_pkgs'}

removed = []
errors = []

for dp, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d not in SKIP_DIRS]
    for fn in fns:
        if fn.endswith('.bak_bom'):
            full = Path(dp) / fn
            try:
                size = full.stat().st_size
                os.remove(full)
                removed.append((str(full.relative_to(ROOT)), size))
            except Exception as e:
                errors.append((str(full.relative_to(ROOT)), str(e)))

total = sum(s for _, s in removed)
print("=" * 70)
print(f"✅ 已删除 .bak_bom 备份: {len(removed)} 个")
for path, sz in removed[:20]:
    print(f"  {path} ({sz}B)")
if len(removed) > 20:
    print(f"  ...还有 {len(removed) - 20} 个")
print(f"\n释放空间: {total} 字节 ({total/1024:.1f} KB)")

if errors:
    print(f"\n❌ 错误: {len(errors)}")
    for p, e in errors:
        print(f"  {p}: {e}")

print("=" * 70)