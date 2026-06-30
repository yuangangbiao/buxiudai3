"""
全面测试文件审计 - 扫描所有可能的过期形式
"""
import os
import hashlib
import ast
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
BOM = b'\xef\xbb\xbf'
SKIP = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.sandbox_pkgs'}

def scan(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            yield Path(dp) / fn

print("=" * 70)
print("全面测试文件审计")
print("=" * 70)

# === 维度 1: 过期后缀文件 ===
print("\n【维度 1: 过期后缀文件】")
SUFFIXES = ['.bak', '.orig', '.old', '.v6bak', '.hash']
COMMA = ['cover', 'bak', 'orig', 'old']
suffix_stats = defaultdict(list)
for p in scan(ROOT):
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

for k, files in sorted(suffix_stats.items()):
    print(f"  {k}: {len(files)} 个")

# === 维度 2: BOM 文件 ===
print("\n【维度 2: BOM (U+FEFF) 头文件】")
bom = []
for p in scan(ROOT):
    if p.suffix in ('.py', '.pyi'):
        try:
            with open(p, 'rb') as f:
                if f.read(3) == BOM:
                    bom.append(p)
        except:
            pass
print(f"  仍有 BOM 的 .py 文件: {len(bom)}")

# === 维度 3: __pycache__ 与编译缓存 ===
print("\n【维度 3: 编译缓存】")
pycache_count = 0
pycache_size = 0
for dp, dns, fns in os.walk(ROOT):
    for dn in dns:
        if dn == '__pycache__':
            cache_dir = Path(dp) / dn
            for f in scan(cache_dir):
                pycache_count += 1
                pycache_size += f.stat().st_size
print(f"  __pycache__/ 文件: {pycache_count} 个 ({pycache_size/1024:.1f} KB)")

# === 维度 4: 覆盖率/测试报告文件 ===
print("\n【维度 4: 覆盖率/测试报告文件】")
report_files = []
REPORT_PATTERNS = ['coverage.xml', 'coverage_html', 'htmlcov', '.coverage',
                    'order_cov.json', 'test_results', 'pytest_results',
                    'junit.xml', 'test_report']
for p in scan(ROOT):
    n = p.name
    for pat in REPORT_PATTERNS:
        if n == pat or n.startswith(pat + '.') or n == pat + '.json' or n == pat + '.xml':
            report_files.append(p)
            break
    # 也匹配报告目录
    if p.is_dir():
        for pat in REPORT_PATTERNS:
            if n == pat:
                # 收集目录下所有文件
                for f in scan(p):
                    report_files.append(f)
                break
print(f"  报告/覆盖率文件: {len(report_files)} 个")
for f in report_files[:15]:
    print(f"    {f.relative_to(ROOT)}")
if len(report_files) > 15:
    print(f"    ...还有 {len(report_files) - 15} 个")

# === 维度 5: 死测试文件（tests/ 内无 def test_*）===
print("\n【维度 5: tests/ 死测试文件】")
TEST_DIRS = [ROOT / 'tests', ROOT / 'mobile_api_ai' / 'tests', ROOT / 'desktop_web' / 'tests']
dead_tests = []
for td in TEST_DIRS:
    if not td.exists():
        continue
    for p in scan(td):
        if p.suffix != '.py':
            continue
        try:
            tree = ast.parse(p.read_text(encoding='utf-8', errors='ignore'))
        except SyntaxError:
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
print("\n【维度 6: 极小测试文件 (<100 字节)】")
tiny = []
for td in TEST_DIRS:
    if not td.exists():
        continue
    for p in scan(td):
        if p.suffix != '.py':
            continue
        try:
            size = p.stat().st_size
            if size < 100 and p.name != '__init__.py' and p.name != 'conftest.py':
                tiny.append((p, size))
        except:
            pass
print(f"  极小测试文件: {len(tiny)} 个")
for p, s in sorted(tiny, key=lambda x: x[1])[:15]:
    print(f"    {p.relative_to(ROOT)} ({s}B)")
if len(tiny) > 15:
    print(f"    ...还有 {len(tiny) - 15} 个")

# === 维度 7: 源已不存在的测试文件（指向已重构模块）===
print("\n【维度 7: 源文件已不存在的测试】")
import re
broken_imports = []
for td in TEST_DIRS:
    if not td.exists():
        continue
    for p in scan(td):
        if p.suffix != '.py':
            continue
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
        except:
            continue
        # 查找 import core.xxx / import models.xxx / import services.xxx
        imports = re.findall(r'^(?:from|import)\s+(core|models|services|utils|views)\.(\w+)', text, re.M)
        for module_path in set(imports):
            mod_name = module_path[0] + '.' + module_path[1]
            # 检查模块是否在项目根目录
            mod_file = ROOT / (mod_name.replace('.', '/') + '.py')
            mod_dir = ROOT / mod_name.replace('.', '/')
            if not mod_file.exists() and not mod_dir.exists():
                broken_imports.append((p, mod_name))
print(f"  引用不存在模块的测试: {len(broken_imports)} 个")
seen = set()
for p, m in broken_imports[:20]:
    key = (str(p.relative_to(ROOT)), m)
    if key not in seen:
        seen.add(key)
        print(f"    {p.relative_to(ROOT)} -> {m}")
if len(seen) > 20:
    print(f"    ...还有 {len(seen) - 20} 处")

# === 维度 8: 临时目录和 .log/.err 文件 ===
print("\n【维度 8: 临时日志/错误文件】")
temp_files = []
for p in scan(ROOT):
    n = p.name
    if n.endswith(('.log', '.err', '.traceback', '.pid', '.lock')):
        temp_files.append(p)
print(f"  临时日志/错误文件: {len(temp_files)} 个")
for p in temp_files[:15]:
    print(f"    {p.relative_to(ROOT)}")
if len(temp_files) > 15:
    print(f"    ...还有 {len(temp_files) - 15} 个")

# === 维度 9: 空 __pycache__ 中的 .pyc 残留 ===
print("\n【维度 9: .pyc 编译缓存】")
pyc = []
for p in scan(ROOT):
    if p.suffix in ('.pyc', '.pyo'):
        pyc.append(p)
print(f"  .pyc 文件: {len(pyc)} 个")

# === 总览 ===
print("\n" + "=" * 70)
print("【审计总览】")
print(f"  过期后缀文件:  {sum(len(v) for v in suffix_stats.values())} 个")
print(f"  BOM 文件:      {len(bom)} 个")
print(f"  __pycache__:   {pycache_count} 个 ({pycache_size/1024:.1f} KB)")
print(f"  报告/覆盖率:   {len(report_files)} 个")
print(f"  死测试文件:    {len(dead_tests)} 个")
print(f"  极小测试:      {len(tiny)} 个")
print(f"  引用不存在模块: {len(seen)} 处")
print(f"  临时日志:      {len(temp_files)} 个")
print(f"  .pyc 文件:     {len(pyc)} 个")
print("=" * 70)