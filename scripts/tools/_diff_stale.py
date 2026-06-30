"""
处理 .v6bak / .hash / .bak / .tmp 备份文件
- diff 源文件判断是否值得保留
- 仅展示，不直接删除（需要用户确认）
"""
import os
import hashlib
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")

# 所有过期后缀
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

# 按后缀分组
by_suffix = {}
for f in stale_files:
    suf = is_stale(f.name)
    by_suffix.setdefault(suf, []).append(f)

for suf, files in sorted(by_suffix.items()):
    print(f"\n## 后缀 {suf}: {len(files)} 个")
    print("-" * 60)
    for f in files:
        rel = f.relative_to(ROOT)
        # 推断源文件
        src = f.with_name(f.name[:-len(suf)])
        src_exists = src.exists()
        # 计算 diff / hash
        if src_exists:
            try:
                bak_hash = hashlib.md5(f.read_bytes()).hexdigest()
                src_hash = hashlib.md5(src.read_bytes()).hexdigest()
                same = bak_hash == src_hash
                src_size = src.stat().st_size
                bak_size = f.stat().st_size
            except Exception as e:
                same = None
                src_size = bak_size = 0
            print(f"  {rel}")
            print(f"    src={src.relative_to(ROOT)} exists={src_exists} same={same} (bak={bak_size}B, src={src_size}B)")
            if same is True:
                print(f"    💡 建议: 内容一致 → 可安全删除")
            elif same is False:
                print(f"    ⚠️  内容不同 → 保留待人工确认")
        else:
            print(f"  {rel}")
            print(f"    src={src.relative_to(ROOT)} exists=False")
            print(f"    🔴 源文件不存在 → 建议删除（孤儿备份）")

print("\n" + "=" * 70)
print("总计:", len(stale_files), "个")