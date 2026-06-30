"""
清理 90 个 ,cover 文件（修正版）
bug: 之前去后缀后又加 .py，导致双后缀
正确: 直接去 ,cover 后缀即可（因为原文件名已包含 .py）
"""
import os
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")

removed = []
kept_missing_src = []
errors = []

SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.sandbox_pkgs'}

for dp, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d not in SKIP_DIRS]
    for fn in fns:
        if not fn.endswith(",cover"):
            continue
        full = Path(dp) / fn
        # 直接去掉 ,cover 后缀即可（.py 已在原文件名）
        src = full.with_name(fn[:-len(",cover")])
        if src.exists():
            try:
                os.remove(full)
                removed.append(str(full.relative_to(ROOT)))
            except Exception as e:
                errors.append((str(full.relative_to(ROOT)), str(e)))
        else:
            kept_missing_src.append(str(full.relative_to(ROOT)))

print("=" * 70)
print(f"✅ 已删除 (源存在): {len(removed)} 个")
for path in removed[:15]:
    print(f"  {path}")
if len(removed) > 15:
    print(f"  ...还有 {len(removed) - 15} 个")

if kept_missing_src:
    print(f"\n⚠️  保留警告 (源文件缺失): {len(kept_missing_src)} 个")
    for path in kept_missing_src:
        print(f"  {path}")

if errors:
    print(f"\n❌ 错误: {len(errors)}")
    for path, e in errors:
        print(f"  {path}: {e}")

print("=" * 70)