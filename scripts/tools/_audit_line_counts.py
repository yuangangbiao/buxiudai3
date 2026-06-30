"""审计：验证巨型测试行数真实性 + 重名函数冲突"""
import os
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")

# D4: 巨型测试文件行数验证
print("=== D4: 巨型测试文件行数验证 ===")
GOLDEN_FILES = [
    (r"mobile_api_ai\tests\integration\test_cc_aux.py", 1344),
    (r"mobile_api_ai\tests\integration\test_cc_core.py", 1282),
    (r"tests\unit\services\test_schedule_dispatch_service.py", 1277),
    (r"tests\unit\services\test_wechat_report_service.py", 1012),
    (r"mobile_api_ai\tests\unit\test_dao.py", 855),
    (r"tests\unit\models\test_order_dao.py", 847),
]

all_match = True
for rel, claimed in GOLDEN_FILES:
    full = ROOT / rel
    if full.exists():
        lines = full.read_text(encoding='utf-8', errors='ignore').count('\n')
        match = "✅" if abs(lines - claimed) <= 50 else "❌"
        print(f"  {match} {rel}: 报告={claimed} 实际={lines}")
        if abs(lines - claimed) > 50:
            all_match = False
    else:
        print(f"  ❌ 文件不存在: {rel}")

print(f"\n  行数一致性: {'全部✅' if all_match else '有差异❌'}")

# D5: 重名函数 pytest 收集冲突验证
print("\n=== D5: 重名函数 pytest 收集冲突验证 ===")
# 找 testpaths 内有多少 test_get_all
import subprocess
result = subprocess.run(
    ['C:\\Users\\lenovo\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe',
     '-m', 'pytest', str(ROOT / 'tests/unit'), '--collect-only', '-q'],
    capture_output=True, text=True, cwd=str(ROOT)
)
lines = result.stdout.split('\n')
get_all_count = sum(1 for l in lines if 'test_get_all' in l)
print(f"  pytest 收集 test_get_all 实例数: {get_all_count}")
print(f"  pytest 收集总行数(去空): {len([l for l in lines if l.strip()])}")
# 找几个典型重名
for name in ['test_create', 'test_get_by_id', 'test_update_success']:
    cnt = sum(1 for l in lines if name in l)
    print(f"  test_{name}: {cnt} 个实例")

# 验证实际测试总数
total_tests = sum(1 for l in lines if l.strip() and not l.startswith('=') and '::test_' in l)
print(f"  实际测试函数总数(估算): {total_tests}")
print(f"  pytest stdout 最后3行:")
for l in lines[-3:]:
    print(f"    {l}")