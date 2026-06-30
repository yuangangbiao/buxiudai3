"""
处理 .v6bak / .hash / .bak / .tmp - v2 修复版
"""
import os
import hashlib
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")

def is_stale(name):
    for suf in ('.v6bak', '.hash', '.bak', '.tmp'):
        if name.endswith(suf):
            return suf
    return None

SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.sandbox_pkgs'}

stale_files = []
for dp, dns, fns in os.walk(ROOT):
    dns[:] = [d for d in dns if d not in SKIP_DIRS]
    for fn in fns:
        if is_stale(fn):
            stale_files.append(Path(dp) / fn)

print(f"找到 {len(stale_files)} 个过期后缀文件")
print("=" * 70)

by_suffix = {}
for f in stale_files:
    suf = is_stale(f.name)
    by_suffix.setdefault(suf, []).append(f)

for suf, files in sorted(by_suffix.items()):
    print(f"\n## 后缀 {suf}: {len(files)} 个")
    print("-" * 60)
    for f in files:
        rel = f.relative_to(ROOT)
        # 修复: 只去后缀，不假设原文件后缀
        new_name = f.name[:-len(suf)]
        if not new_name:
            print(f"  {rel}")
            print(f"    🔴 空文件名 → 跳过")
            continue
        src = f.with_name(new_name)
        src_exists = src.exists()
        if src_exists:
            try:
                bak_hash = hashlib.md5(f.read_bytes()).hexdigest()
                src_hash = hashlib.md5(src.read_bytes()).hexdigest()
                same = bak_hash == src_hash
                src_size = src.stat().st_size
                bak_size = f.stat().st_size
            except Exception:
                same = None
                src_size = bak_size = 0
            print(f"  {rel}")
            print(f"    src={src.relative_to(ROOT)} exists=True same={same} (bak={bak_size}B, src={src_size}B)")
            if same is True:
                print(f"    💡 建议: 内容一致 → 可安全删除")
            elif same is False:
                # .hash 文件本身只是 hash 摘要（~50B），不是源码备份
                if suf == '.hash':
                    print(f"    💡 .hash 仅为 hash 摘要（{bak_size}B）→ 可直接删除")
                else:
                    print(f"    ⚠️  内容不同 → 保留待人工确认")
        else:
            print(f"  {rel}")
            print(f"    src={src.relative_to(ROOT)} exists=False")
            print(f"    🔴 源文件不存在 → 建议删除（孤儿备份）")

print("\n" + "=" * 70)