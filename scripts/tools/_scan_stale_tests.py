"""
测试文件体检 — 扫描过期/可疑文件 (限定到测试目录 + 已知过期后缀文件)
"""
import os
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")

# ============ 1. 全仓库过期后缀 ============
print("=" * 70)
print("一、全仓库过期/异常后缀文件扫描")
print("=" * 70)

stats = defaultdict(list)
COMMA_SUFFIXES = ["cover", "bak", "orig", "old", "tmp"]
STALE_SUFFIXES = [".bak", ".orig", ".old", ".tmp", ".v6bak", ".hash"]

# 用 os.walk + os.scandir 替代 rglob 提速
def scan_dir(root):
    for entry in os.scandir(root):
        if entry.is_dir(follow_symlinks=False):
            # 跳过明显不需扫描的目录
            if entry.name in {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.sandbox_pkgs'}:
                continue
            yield from scan_dir(entry.path)
        elif entry.is_file():
            yield Path(entry.path)

count = 0
for p in scan_dir(ROOT):
    name = p.name
    matched = False
    for suf in STALE_SUFFIXES:
        if name.endswith(suf):
            stats[suf].append(p)
            count += 1
            matched = True
            break
    if matched:
        continue
    for suf in COMMA_SUFFIXES:
        if name.endswith("," + suf):
            stats["," + suf].append(p)
            count += 1
            break

for suf, files in stats.items():
    if not files:
        continue
    print(f"\n  后缀 {suf}: {len(files)} 个")
    by_dir = defaultdict(int)
    for f in files:
        rel = str(f.relative_to(ROOT))
        d = rel.rsplit("\\", 1)[0]
        by_dir[d] += 1
    for d, n in sorted(by_dir.items(), key=lambda x: -x[1])[:3]:
        print(f"    [{d}] x{n}")
    if len(by_dir) > 3:
        print(f"    ...还有 {len(by_dir) - 3} 个目录")

print(f"\n过期文件总计: {count} 个")

# ============ 2. 测试目录统计 ============
print("\n" + "=" * 70)
print("二、测试目录分布统计")
print("=" * 70)

test_dirs = [ROOT / "tests", ROOT / "mobile_api_ai" / "tests", ROOT / "desktop_web" / "tests", ROOT / "scripts"]
sub_count = defaultdict(int)
all_test_files = []

def scan_py(base):
    for entry in os.scandir(base):
        if entry.is_dir(follow_symlinks=False):
            if entry.name in {'.git', '__pycache__', '.sandbox_pkgs'}:
                continue
            yield from scan_py(entry.path)
        elif entry.is_file() and entry.name.endswith(".py"):
            yield Path(entry.path)

for td in test_dirs:
    if not td.exists():
        continue
    for p in scan_py(td):
        all_test_files.append(p)
        rel = p.relative_to(ROOT)
        parts = rel.parts
        if len(parts) >= 3:
            key = "/".join(parts[:3])
        elif len(parts) == 2:
            key = "/".join(parts[:2])
        else:
            key = parts[0]
        sub_count[key] += 1

print(f"\n测试文件总数: {len(all_test_files)}")
print("\n按子目录分布 (Top 25):")
for d, n in sorted(sub_count.items(), key=lambda x: -x[1])[:25]:
    print(f"  [{d}] x{n}")

# ============ 3. 以下划线开头 ============
print("\n" + "=" * 70)
print("三、可疑文件: 以下划线开头 (辅助/调试/写入器，非真正测试)")
print("=" * 70)

suspicious = [p for p in all_test_files if p.name.startswith("_")]
print(f"可疑文件数: {len(suspicious)}")
for p in sorted(suspicious):
    print(f"  {p.relative_to(ROOT)}")

# ============ 4. 阶段命名 ============
print("\n" + "=" * 70)
print("四、阶段命名测试文件 (sprint/push/final/gap/batch/quick/depth/complete)")
print("=" * 70)

PATTERNS = ["sprint", "push_5", "push_4", "push_3", "final_", "gap_filler", "gap_",
            "batch", "quick", "depth", "complete", "more", "bulk"]
flagged = []
for p in all_test_files:
    n = p.name.lower()
    for pat in PATTERNS:
        if pat in n:
            flagged.append((p, pat))
            break

print(f"阶段命名文件数: {len(flagged)}")
pat_counter = Counter([x[1] for x in flagged])
print("\n按模式统计:")
for pat, n in pat_counter.most_common():
    print(f"  {pat}: {n} 个")

# ============ 5. 重名/近似命名 ============
print("\n" + "=" * 70)
print("五、近似命名测试 (同名模块多版本)")
print("=" * 70)

base_groups = defaultdict(list)
for p in all_test_files:
    name = p.name
    if "_complete" in name:
        base = name.replace("_complete.py", "")
    elif "_gaps" in name:
        base = name.replace("_gaps.py", "")
    elif "_depth" in name:
        base = name.replace("_depth.py", "")
    else:
        base = name.replace(".py", "")
    base_groups[base].append(p)

dups = {k: v for k, v in base_groups.items() if len(v) > 1}
print(f"重名/近似命名组数: {len(dups)}")
for k, files in sorted(dups.items()):
    print(f"\n  {k} ({len(files)} 个变体):")
    for f in files:
        print(f"    {f.relative_to(ROOT)}")

# ============ 6. 按测试类别分类 ============
print("\n" + "=" * 70)
print("六、按测试类别分类")
print("=" * 70)

cats = defaultdict(int)
for p in all_test_files:
    rel = p.relative_to(ROOT).as_posix()
    if "/e2e/" in rel or rel.startswith("scripts/e2e"):
        cats["e2e"] += 1
    elif "/integration/" in rel:
        cats["integration"] += 1
    elif "/modular/" in rel:
        cats["modular"] += 1
    elif "/unit/" in rel:
        cats["unit"] += 1
    else:
        cats["其他(顶层或散落)"] += 1

for k, n in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {k}: {n}")

# ============ 7. 散落在 scripts/ 的 test_*.py ============
print("\n" + "=" * 70)
print("七、scripts/ 散落的 test_*.py (非 unittest)")
print("=" * 70)

scripts_tests = [p for p in all_test_files if p.relative_to(ROOT).parts[0] == "scripts"]
print(f"scripts/ 下 test_*.py 共 {len(scripts_tests)} 个")
# 按目录归类
sd = defaultdict(int)
for p in scripts_tests:
    rel = p.relative_to(ROOT)
    parts = rel.parts
    if len(parts) >= 3:
        sd["/".join(parts[:2])] += 1
    else:
        sd[parts[0]] += 1
for d, n in sorted(sd.items(), key=lambda x: -x[1]):
    print(f"  [{d}] x{n}")

print("\n=== 扫描完成 ===")