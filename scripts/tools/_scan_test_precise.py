"""
复核 433 个"其他"无断言：是不是 unittest.TestCase 类（self.assertEqual）
"""
import os
import ast
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
test_dirs = [ROOT / "tests", ROOT / "mobile_api_ai" / "tests", ROOT / "desktop_web" / "tests", ROOT / "scripts"]

def scan_py(base):
    for entry in os.scandir(base):
        if entry.is_dir(follow_symlinks=False):
            if entry.name in {'.git', '__pycache__', '.sandbox_pkgs'}:
                continue
            yield from scan_py(base) if False else scan_py(entry.path)
        elif entry.is_file() and entry.name.endswith(".py"):
            yield Path(entry.path)

# 递归修复
def scan_py2(base):
    for entry in os.scandir(base):
        if entry.is_dir(follow_symlinks=False):
            if entry.name in {'.git', '__pycache__', '.sandbox_pkgs'}:
                continue
            yield from scan_py2(entry.path)
        elif entry.is_file() and entry.name.endswith(".py"):
            yield Path(entry.path)

all_test_files = []
for td in test_dirs:
    if td.exists():
        for p in scan_py2(td):
            all_test_files.append(p)

# 统计
STATS = Counter()
no_assert_funcs = []

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

    # 找出所有 TestCase 子类
    unittest_classes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = ""
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr
                if base_name in ("TestCase", "unittest.TestCase"):
                    unittest_classes.add(node.name)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(node))
            if has_assert:
                continue

            func_text = ast.get_source_segment(text, node) or ""

            # 检查是否调用 self.assertXxx / self.fail
            has_unittest_assert = bool(ast.walk(node) and any(
                isinstance(n, ast.Attribute) and n.attr.startswith(("assert", "fail", "assertEqual", "assertRaises"))
                for n in ast.walk(node)
            ))
            # 实际更精确：检查 self.assertEqual / self.assertXxx / self.fail
            unittest_assert_calls = False
            for n in ast.walk(node):
                if isinstance(n, ast.Call):
                    func = n.func
                    if isinstance(func, ast.Attribute) and func.attr.startswith(("assert", "fail")):
                        # 检查 receiver 是 self 或 cls
                        if isinstance(func.value, ast.Name) and func.value.id in ("self", "cls"):
                            unittest_assert_calls = True
                            break

            if "pytest.skip" in func_text:
                STATS["skip"] += 1
            elif "raise " in func_text:
                STATS["raise"] += 1
            elif "print(" in func_text:
                STATS["print-only"] += 1
            elif unittest_assert_calls:
                STATS["unittest-assert"] += 1
            else:
                STATS["other"] += 1
                no_assert_funcs.append((p, node.name))

print("最终分类:")
for k, v in STATS.most_common():
    print(f"  {k}: {v}")

print("\n真正的反模式 (print-only + other):")
print(f"  {STATS['print-only'] + STATS['other']} 个")

# 看"other"的真实内容
print("\n" + "=" * 70)
print("⚠️  'other' 真无任何验证的测试 (Top 30)")
print("=" * 70)
for p, n in no_assert_funcs[:30]:
    print(f"  {p.relative_to(ROOT)} :: {n}()")
if len(no_assert_funcs) > 30:
    print(f"  ...还有 {len(no_assert_funcs) - 30} 个")

# 按文件聚合
print("\n按文件分布 (other 类):")
by_file = Counter()
for p, n in no_assert_funcs:
    by_file[str(p.relative_to(ROOT))] += 1
for f, c in by_file.most_common(20):
    print(f"  {c} 个 - {f}")