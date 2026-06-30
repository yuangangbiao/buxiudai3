"""
精准复核"无断言"测试：排除 pytest.skip 等合法情况
"""
import os
import ast
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
test_dirs = [ROOT / "tests", ROOT / "mobile_api_ai" / "tests", ROOT / "desktop_web" / "tests", ROOT / "scripts"]

def scan_py(base):
    for entry in os.scandir(base):
        if entry.is_dir(follow_symlinks=False):
            if entry.name in {'.git', '__pycache__', '.sandbox_pkgs'}:
                continue
            yield from scan_py(entry.path)
        elif entry.is_file() and entry.name.endswith(".py"):
            yield Path(entry.path)

all_test_files = []
for td in test_dirs:
    if td.exists():
        for p in scan_py(td):
            all_test_files.append(p)

print(f"扫描测试文件总数: {len(all_test_files)}")

# 分类统计
NO_ASSERT_BUT_SKIP = []  # 有 pytest.skip → 合法
NO_ASSERT_BUT_RAISE = []  # 有 raise → 异常路径合法
NO_ASSERT_BUT_PRINT = []  # 只有 print + 无 assert → 反模式
NO_ASSERT_OTHER = []      # 真的啥都没

NO_ASSERT_TOTAL = 0

for p in all_test_files:
    text = ""
    try:
        text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    try:
        tree = ast.parse(text)
    except SyntaxError:
        continue

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(node))
            if has_assert:
                continue

            NO_ASSERT_TOTAL += 1
            func_text = ast.get_source_segment(text, node) or ""
            if "pytest.skip" in func_text or "pytest.skip(" in func_text:
                NO_ASSERT_BUT_SKIP.append((p, node.name, "skip"))
            elif "raise " in func_text:
                NO_ASSERT_BUT_RAISE.append((p, node.name, "raise"))
            elif "print(" in func_text:
                NO_ASSERT_BUT_PRINT.append((p, node.name, "print-only"))
            else:
                NO_ASSERT_OTHER.append((p, node.name, "other"))

print(f"\n无 assert 的测试函数总数: {NO_ASSERT_TOTAL}")
print(f"  ✅ 含 pytest.skip (合法): {len(NO_ASSERT_BUT_SKIP)}")
print(f"  ✅ 含 raise (异常路径合法): {len(NO_ASSERT_BUT_RAISE)}")
print(f"  🔴 仅 print 无断言 (反模式): {len(NO_ASSERT_BUT_PRINT)}")
print(f"  ⚠️  其他 (空函数/可疑): {len(NO_ASSERT_OTHER)}")

# 列出仅 print 的反模式
print("\n" + "=" * 70)
print("🔴 仅 print 无断言的反模式测试 (Top 50)")
print("=" * 70)
for p, n, r in NO_ASSERT_BUT_PRINT[:50]:
    print(f"  [{r}] {p.relative_to(ROOT)} :: {n}()")
if len(NO_ASSERT_BUT_PRINT) > 50:
    print(f"  ...还有 {len(NO_ASSERT_BUT_PRINT) - 50} 个")

# 按文件聚合
print("\n" + "=" * 70)
print("🔴 反模式测试按文件分布")
print("=" * 70)
by_file = defaultdict(int)
for p, n, r in NO_ASSERT_BUT_PRINT:
    by_file[str(p.relative_to(ROOT))] += 1
for f, c in sorted(by_file.items(), key=lambda x: -x[1])[:20]:
    print(f"  {c} 个 - {f}")

# 列出其他 (可疑)
print("\n" + "=" * 70)
print("⚠️ 可疑 '其他' 类 (无 skip/raise/print 也没 assert) Top 30")
print("=" * 70)
for p, n, r in NO_ASSERT_OTHER[:30]:
    print(f"  [{r}] {p.relative_to(ROOT)} :: {n}()")
if len(NO_ASSERT_OTHER) > 30:
    print(f"  ...还有 {len(NO_ASSERT_OTHER) - 30} 个")