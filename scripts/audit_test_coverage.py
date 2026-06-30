"""[审计 v2] 测试覆盖验证"""
import subprocess

# 总测试数
r = subprocess.run(['python', '-m', 'pytest', '--no-cov', '--collect-only', '-q', '-p', 'no:cacheprovider',
                    'tests/unit/dispatch_center/'], capture_output=True, text=True)
collected = r.stdout.count('::')
print(f'unit/dispatch_center 总测试数: {collected}')

# 各套件测试数
suites = ['test_publisher.py', 'test_publisher_v376.py', 'test_dlq_retry.py', 'test_metrics.py']
total = 0
for s in suites:
    r2 = subprocess.run(['python', '-m', 'pytest', '--no-cov', '--collect-only', '-q', '-p', 'no:cacheprovider',
                         f'tests/unit/dispatch_center/{s}'], capture_output=True, text=True)
    n = r2.stdout.count('::')
    total += n
    print(f'  {s}: {n}')
print(f'小计: {total}')

# v376 测试覆盖检查
v376 = open('tests/unit/dispatch_center/test_publisher_v376.py', 'r', encoding='utf-8').read()
checks = {
    'QualityPublisher': 'QualityPublisher' in v376,
    'quality publish': 'quality' in v376 and 'publish' in v376,
    'CircuitBreaker': 'CircuitBreaker' in v376,
    'is_available': 'is_available' in v376,
    'get_task_count': 'get_task_count' in v376,
    'get_task_by_id': 'get_task_by_id' in v376,
    'get_all_tasks': 'get_all_tasks' in v376,
}
print()
print('=== test_publisher_v376.py 覆盖检查 ===')
for k, v in checks.items():
    print(f'  {k}: {"✅" if v else "❌"}')