"""
清理剩余过期测试文件（Phase 2）
"""
import os
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")

# === 仅在 tests/ 目录内扫描 ===
print("=" * 70)
print("一、tests/ 目录过期文件清理")
print("=" * 70)

test_stale = []
for dp, dns, fns in os.walk(ROOT / 'tests'):
    dns[:] = [d for d in dns if d not in {'.git', '__pycache__', '.sandbox_pkgs'}]
    for fn in fns:
        for s in ('.bak', '.orig', '.old', '.v6bak', ',cover', '.hash'):
            if fn.endswith(s):
                test_stale.append(Path(dp) / fn)
                break

print(f"发现 tests/ 内过期文件: {len(test_stale)} 个")
deleted_test = []
kept_test = []
for f in test_stale:
    src = f.with_name(f.name[:-(len(f.suffix if '.' in f.name else f.name.split('.')[-1]))])
    # 更精确地去后缀
    name = f.name
    for suf in ('.bak', '.orig', '.old', '.v6bak', ',cover', '.hash'):
        if name.endswith(suf):
            src_name = name[:-len(suf)]
            src = f.parent / src_name
            break
    src_exists = src.exists()
    if not src_exists:
        # 孤儿备份，删
        try:
            os.remove(f)
            deleted_test.append(str(f.relative_to(ROOT)))
            print(f"  ✅ 删孤儿: {f.relative_to(ROOT)}")
        except Exception as e:
            print(f"  ❌ 失败: {f.relative_to(ROOT)} :: {e}")
    else:
        kept_test.append(str(f.relative_to(ROOT)))
        print(f"  ⏭️  保留(有源): {f.relative_to(ROOT)}")

print(f"\n  已删: {len(deleted_test)} | 保留: {len(kept_test)}")

# === 全仓库 orphan ,cover ===
print("\n" + "=" * 70)
print("二、全仓库 orphan ,cover 文件")
print("=" * 70)

orphan_cover = []
for dp, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d not in {'.git', '__pycache__', '.sandbox_pkgs', 'node_modules', '.venv'}]
    for fn in fns:
        if fn.endswith(',cover'):
            p = Path(dp) / fn
            # 推断源
            name = fn[:-len(',cover')]
            src = p.parent / name
            if not src.exists():
                orphan_cover.append(p)

print(f"orphan ,cover 文件: {len(orphan_cover)} 个")
deleted_cover = []
for f in orphan_cover:
    try:
        size = f.stat().st_size
        os.remove(f)
        deleted_cover.append((str(f.relative_to(ROOT)), size))
        print(f"  ✅ 删孤儿: {f.relative_to(ROOT)} ({size}B)")
    except Exception as e:
        print(f"  ❌ 失败: {f.relative_to(ROOT)} :: {e}")

print("\n" + "=" * 70)
total = len(deleted_test) + len(deleted_cover)
print(f"总计清理: {total} 个过期文件")
print(f"  tests/ 内: {len(deleted_test)} 个")
print(f"  orphan ,cover: {len(deleted_cover)} 个")
print("=" * 70)