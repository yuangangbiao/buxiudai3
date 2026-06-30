"""
测试漏洞与死测试扫描 — 第二轮深度体检
- 死测试: 无 def test_* / 未被任何 import / conftest 收集
- 空测试: 函数体只有 pass 或 #
- 弱断言: 只有 assert True / assert x is not None / 无断言
- 重名测试函数: 不同文件定义同名 def test_xxx
- 测试但没 mock DB: 直接连真实库
"""
import os
import re
import ast
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
test_dirs = [ROOT / "tests", ROOT / "mobile_api_ai" / "tests", ROOT / "desktop_web" / "tests"]

def scan_py(base):
    for entry in os.scandir(base):
        if entry.is_dir(follow_symlinks=False):
            if entry.name in {'.git', '__pycache__', '.sandbox_pkgs'}:
                continue
            yield from scan_py(entry.path)
        elif entry.is_file() and entry.name.endswith(".py"):
            yield Path(entry.path)

def read_text(p):
    try:
        return p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ""

# 收集所有测试文件
all_test_files = []
for td in test_dirs:
    if td.exists():
        for p in scan_py(td):
            all_test_files.append(p)
# 加上 scripts/test_*.py 散落的
scripts_dir = ROOT / "scripts"
if scripts_dir.exists():
    for p in scan_py(scripts_dir):
        if p.name.startswith("test_"):
            all_test_files.append(p)

print(f"扫描测试文件总数: {len(all_test_files)}")

# ============ 1. 死测试文件 (无任何 test_* 函数/方法) ============
print("\n" + "=" * 70)
print("一、死测试文件 (无任何 def test_*)")
print("=" * 70)

DEAD_TEST_FILES = []
test_func_counter = defaultdict(list)

for p in all_test_files:
    text = read_text(p)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        continue
    # 找出所有 def test_*
    funcs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            funcs.append(node.name)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test_"):
                    funcs.append(f"{node.name}.{item.name}")
    if not funcs:
        DEAD_TEST_FILES.append(p)
    else:
        for fn in funcs:
            test_func_counter[fn].append(p)

print(f"死测试文件: {len(DEAD_TEST_FILES)} 个")
for p in sorted(DEAD_TEST_FILES):
    print(f"  ⚠️ {p.relative_to(ROOT)}")

# ============ 2. pytest 收集路径 (读 pytest.ini / pyproject.toml / conftest.py) ============
print("\n" + "=" * 70)
print("二、pytest 实际收集路径分析")
print("=" * 70)

# 读 pytest.ini
pytest_ini = ROOT / "pytest.ini"
if pytest_ini.exists():
    print(f"\n[pytest.ini]")
    print(pytest_ini.read_text(encoding='utf-8', errors='ignore'))

pyproject = ROOT / "pyproject.toml"
if pyproject.exists():
    print(f"\n[pyproject.toml 摘要]")
    text = pyproject.read_text(encoding='utf-8', errors='ignore')
    # 只打印 pytest 相关部分
    in_pytest = False
    for line in text.split("\n"):
        if "[tool.pytest" in line:
            in_pytest = True
        elif line.startswith("[") and in_pytest and "[tool.pytest" not in line:
            in_pytest = False
        if in_pytest:
            print(f"  {line}")

# ============ 3. 弱断言/空测试 ============
print("\n" + "=" * 70)
print("三、测试漏洞: 空测试 / 弱断言 / 仅 assert True")
print("=" * 70)

WEAK_ASSERT = re.compile(r"^\s*assert\s+True\s*$", re.MULTILINE)
EMPTY_BODY = re.compile(r"def\s+test_\w+\s*\([^)]*\)[^:]*:\s*(?:\n\s*(?:pass|#.*|\"\"\")\s*)+(?:\n|$)")

weak_cases = []
empty_cases = []
no_assert_cases = []

for p in all_test_files:
    text = read_text(p)
    if not text:
        continue
    try:
        tree = ast.parse(text)
    except SyntaxError:
        continue

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            func_text = ast.get_source_segment(text, node)
            if not func_text:
                continue
            # 1) 空测试
            body = node.body
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                empty_cases.append((p, node.name, "body-only-pass"))
                continue
            if len(body) == 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                empty_cases.append((p, node.name, "body-only-string-doc"))
                continue
            # 2) 弱断言: 只 assert True
            if WEAK_ASSERT.search(func_text):
                weak_cases.append((p, node.name, "assert True"))
            # 3) 无任何 assert
            has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(node))
            if not has_assert:
                no_assert_cases.append((p, node.name, "no-assert"))

print(f"空测试(只有 pass/字符串): {len(empty_cases)} 个")
for p, n, reason in empty_cases[:30]:
    print(f"  ⚠️  [{reason}] {p.relative_to(ROOT)} :: {n}()")
if len(empty_cases) > 30:
    print(f"  ...还有 {len(empty_cases) - 30} 个")

print(f"\n弱断言(只有 assert True): {len(weak_cases)} 个")
for p, n, reason in weak_cases[:30]:
    print(f"  ⚠️  [{reason}] {p.relative_to(ROOT)} :: {n}()")
if len(weak_cases) > 30:
    print(f"  ...还有 {len(weak_cases) - 30} 个")

print(f"\n无任何 assert 的测试函数: {len(no_assert_cases)} 个")
for p, n, reason in no_assert_cases[:20]:
    print(f"  ⚠️  [{reason}] {p.relative_to(ROOT)} :: {n}()")
if len(no_assert_cases) > 20:
    print(f"  ...还有 {len(no_assert_cases) - 20} 个")

# ============ 4. 重复测试函数名 (跨文件同名) ============
print("\n" + "=" * 70)
print("四、重复测试函数名 (跨文件同名)")
print("=" * 70)

dups_func = {k: v for k, v in test_func_counter.items() if len(v) > 1}
print(f"重复测试函数名数: {len(dups_func)}")
# 仅展示 Top 20
for fn, files in sorted(dups_func.items(), key=lambda x: -len(x[1]))[:20]:
    print(f"\n  {fn} 出现在 {len(files)} 个文件:")
    for f in files:
        print(f"    {f.relative_to(ROOT)}")
if len(dups_func) > 20:
    print(f"\n  ...还有 {len(dups_func) - 20} 个重复名")

# ============ 5. 数据库连接风险 (测试中直接连真实库) ============
print("\n" + "=" * 70)
print("五、测试中直接连真实数据库风险 (无 @patch)")
print("=" * 70)

# 收集可疑 import：pymysql.connect / MySQLStorage / get_connection 不带 mock
SUSPECT_IMPORT = [
    "from core.db import", "from storage.mysql_storage",
    "from models.database", "pymysql.connect",
]

risk_files = []
for p in all_test_files:
    text = read_text(p)
    # 看是否有 patch / mock / MagicMock
    has_mock = ("patch" in text or "MagicMock" in text or "@mock" in text
                or "monkeypatch" in text or "fixture" in text)
    # 看是否直接 import db 连接
    suspect = any(s in text for s in SUSPECT_IMPORT)
    if suspect and not has_mock:
        risk_files.append(p)

print(f"风险文件数: {len(risk_files)}")
for p in sorted(risk_files)[:30]:
    print(f"  ⚠️  {p.relative_to(ROOT)}")
if len(risk_files) > 30:
    print(f"  ...还有 {len(risk_files) - 30} 个")

# ============ 6. 巨大测试文件 (>500 行) ============
print("\n" + "=" * 70)
print("六、巨型测试文件 (>500 行)")
print("=" * 70)

big_files = []
for p in all_test_files:
    text = read_text(p)
    lines = text.count("\n")
    if lines > 500:
        big_files.append((p, lines))

big_files.sort(key=lambda x: -x[1])
print(f"巨型测试文件数: {len(big_files)}")
for p, n in big_files[:20]:
    print(f"  📏 {n} 行  {p.relative_to(ROOT)}")

# ============ 7. import 业务模块失败的测试 (语法/导入错误) ============
print("\n" + "=" * 70)
print("七、语法错误的测试文件 (无法被 pytest 收集)")
print("=" * 70)

syntax_errors = []
for p in all_test_files:
    text = read_text(p)
    try:
        ast.parse(text)
    except SyntaxError as e:
        syntax_errors.append((p, str(e)))

print(f"语法错误文件数: {len(syntax_errors)}")
for p, err in syntax_errors:
    print(f"  ❌ {p.relative_to(ROOT)} :: {err}")

print("\n=== 漏洞扫描完成 ===")