"""
全面测试文件审计 v2 - 优化版
- 只扫描相关目录（tests/、scripts/、业务目录、coverage/、.workbuddy/）
- 跳过大型跳过目录
"""
import os
import re
import ast
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
BOM = b'\xef\xbb\xbf'

# 只扫描相关目录
SCAN_DIRS = [
    'tests', 'mobile_api_ai', 'desktop_web', 'core', 'models', 'services',
    'utils', 'views', 'controllers', 'dispatch', 'scripts', 'coverage_html',
    '.workbuddy', 'docs', 'reports',
]
# 业务目录根（这些可能直接在 ROOT 下）
BUSINESS_DIRS_AT_ROOT = ['core', 'models', 'services', 'utils', 'views', 'controllers', 'dispatch']

# 跳过目录
SKIP = {'.git', 'node_modules', 'venv', 'dist', 'build', '.tox', '.eggs'}

def safe_scan(root):
    """扫描时跳过 .git/venv/node_modules"""
    if not root.exists():
        return
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP and not d.startswith('.git')]
        for fn in fns:
            yield Path(dp) / fn

print("=" * 70)
print("全面测试文件审计 v2 (优化版)")
print("=" * 70)

# === 维度 1: 过期后缀文件 ===
print("\n【维度 1: 过期后缀文件】")
SUFFIXES = ['.bak', '.orig', '.old', '.v6bak', '.hash']
COMMA = ['cover', 'bak', 'orig', 'old']
suffix_stats = defaultdict(list)
for d in SCAN_DIRS:
    for p in safe_scan(ROOT / d):
        n = p.name
        for s in SUFFIXES:
            if n.endswith(s):
                suffix_stats[s].append(p)
                break
        else:
            for s in COMMA:
                if n.endswith(',' + s):
                    suffix_stats[',' + s].append(p)
                    break

total_suffix = 0
for k, files in sorted(suffix_stats.items()):
    print(f"  {k}: {len(files)} 个")
    total_suffix += len(files)

# === 维度 2: BOM 文件 ===
print("\n【维度 2: BOM (U+FEFF) 头文件】")
bom = []
for d in SCAN_DIRS:
    for p in safe_scan(ROOT / d):
        if p.suffix in ('.py', '.pyi'):
            try:
                with open(p, 'rb') as f:
                    if f.read(3) == BOM:
                        bom.append(p)
            except:
                pass
print(f"  仍有 BOM 的 .py 文件: {len(bom)} 个")
for p in bom[:10]:
    print(f"    {p.relative_to(ROOT)}")

# === 维度 3: __pycache__ 与编译缓存 ===
print("\n【维度 3: 编译缓存】")
pycache_count = 0
pycache_size = 0
for d in SCAN_DIRS:
    base = ROOT / d
    if not base.exists():
        continue
    for dp, dns, fns in os.walk(base):
        for dn in dns:
            if dn == '__pycache__':
                cache_dir = Path(dp) / dn
                for f in cache_dir.iterdir():
                    if f.is_file():
                        pycache_count += 1
                        pycache_size += f.stat().st_size
print(f"  __pycache__/ 文件: {pycache_count} 个 ({pycache_size/1024/1024:.1f} MB)")

# === 维度 4: 覆盖率/测试报告文件 ===
print("\n【维度 4: 覆盖率/测试报告文件】")
report_files = []
REPORT_DIRS = ['coverage_html', 'htmlcov', 'test_results', 'reports', '.pytest_cache']
REPORT_FILES = ['coverage.xml', 'order_cov.json', '.coverage', 'junit.xml']
for d in SCAN_DIRS:
    base = ROOT / d
    if not base.exists():
        continue
    if d in REPORT_DIRS:
        # 整个目录
        for p in safe_scan(base):
            if p.is_file():
                report_files.append(p)
    else:
        for p in safe_scan(base):
            n = p.name
            for pat in REPORT_FILES:
                if n == pat:
                    report_files.append(p)
                    break
            if n == '.pytest_cache' and p.is_dir():
                for f in p.iterdir():
                    if f.is_file():
                        report_files.append(f)
print(f"  报告/覆盖率文件: {len(report_files)} 个")
for p in report_files[:10]:
    print(f"    {p.relative_to(ROOT)}")
if len(report_files) > 10:
    print(f"    ...还有 {len(report_files) - 10} 个")

# === 维度 5: 死测试文件 ===
print("\n【维度 5: tests/ 死测试文件 (无 def test_*)】")
TEST_DIRS = [ROOT / 'tests', ROOT / 'mobile_api_ai' / 'tests', ROOT / 'desktop_web' / 'tests']
dead_tests = []
for td in TEST_DIRS:
    if not td.exists():
        continue
    for p in safe_scan(td):
        if p.suffix != '.py':
            continue
        # 跳过 conftest 和 __init__
        if p.name in ('conftest.py', '__init__.py'):
            continue
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(text)
        except (SyntaxError, UnicodeDecodeError):
            continue
        has_test = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                has_test = True
                break
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith('test_'):
                        has_test = True
                        break
        if not has_test and 'test' in p.name.lower():
            dead_tests.append(p)
print(f"  死测试文件: {len(dead_tests)} 个")
for p in dead_tests[:20]:
    print(f"    {p.relative_to(ROOT)}")
if len(dead_tests) > 20:
    print(f"    ...还有 {len(dead_tests) - 20} 个")

# === 维度 6: 0 字节 / 极小文件 ===
print("\n【维度 6: 极小测试文件 (<200 字节)】")
tiny = []
for td in TEST_DIRS:
    if not td.exists():
        continue
    for p in safe_scan(td):
        if p.suffix != '.py':
            continue
        if p.name in ('__init__.py', 'conftest.py'):
            continue
        try:
            size = p.stat().st_size
            if size < 200:
                tiny.append((p, size))
        except:
            pass
print(f"  极小测试文件: {len(tiny)} 个")
for p, s in sorted(tiny, key=lambda x: x[1])[:15]:
    print(f"    {p.relative_to(ROOT)} ({s}B)")
if len(tiny) > 15:
    print(f"    ...还有 {len(tiny) - 15} 个")

# === 维度 7: 引用不存在模块的测试（取样）===
print("\n【维度 7: 引用不存在模块的测试 (抽 50 个)】")
import_pattern = re.compile(r'^(?:from|import)\s+(core|models|services|utils|views|controllers|dispatch)\.(\w+)', re.M)
broken = set()
checked = 0
for td in TEST_DIRS:
    if not td.exists():
        continue
    for p in safe_scan(td):
        if p.suffix != '.py':
            continue
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
        except:
            continue
        if 'test' not in p.name.lower():
            continue
        checked += 1
        if checked > 200:
            break
        for match in import_pattern.findall(text):
            mod_path = match[0] + '/' + match[1]
            if not (ROOT / (mod_path + '.py')).exists() and not (ROOT / mod_path).exists():
                broken.add((str(p.relative_to(ROOT)), mod_path))
        if checked > 200:
            break
    if checked > 200:
        break
print(f"  抽样 {checked} 个测试文件, 发现 {len(broken)} 处引用不存在模块")
for p, m in list(broken)[:15]:
    print(f"    {p} -> {m}")

# === 维度 8: 临时日志/错误文件 ===
print("\n【维度 8: 临时日志/错误文件】")
temp_files = []
for d in SCAN_DIRS:
    for p in safe_scan(ROOT / d):
        n = p.name
        if n.endswith(('.log', '.err', '.traceback', '.pid', '.lock')):
            temp_files.append(p)
print(f"  临时日志文件: {len(temp_files)} 个")
for p in temp_files[:10]:
    print(f"    {p.relative_to(ROOT)}")
if len(temp_files) > 10:
    print(f"    ...还有 {len(temp_files) - 10} 个")

# === 维度 9: pytest 缓存 ===
print("\n【维度 9: .pytest_cache 缓存】")
pytest_cache = []
for d in SCAN_DIRS:
    base = ROOT / d
    if not base.exists():
        continue
    for p in base.iterdir():
        if p.name == '.pytest_cache' and p.is_dir():
            for f in p.rglob('*'):
                if f.is_file():
                    pytest_cache.append(f)
print(f"  .pytest_cache 文件: {len(pytest_cache)} 个")

# === 总览 ===
print("\n" + "=" * 70)
print("【审计总览】")
print(f"  过期后缀文件:   {total_suffix} 个")
print(f"  BOM 文件:       {len(bom)} 个")
print(f"  __pycache__:    {pycache_count} 个 ({pycache_size/1024/1024:.1f} MB)")
print(f"  报告/覆盖率:    {len(report_files)} 个")
print(f"  死测试文件:     {len(dead_tests)} 个")
print(f"  极小测试:       {len(tiny)} 个")
print(f"  引用不存在模块: {len(broken)} 处 (抽样 {min(checked, 200)})")
print(f"  临时日志:       {len(temp_files)} 个")
print(f"  .pytest_cache:  {len(pytest_cache)} 个")
print("=" * 70)