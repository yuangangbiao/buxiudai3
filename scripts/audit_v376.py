"""[审计] v3.7.6 声称验证"""
import ast

with open(r'mobile_api_ai/dispatch_center/publisher.py', 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read())

classes = sorted({n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)})
methods = sorted({n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)})

print('=== v3.7.6 publisher.py 实际产出 ===')
print(f'类 ({len(classes)}): {classes}')
print(f'函数/方法 ({len(methods)}): {methods}')
print()

checks = {
    'CircuitBreaker 类': 'CircuitBreaker' in classes,
    'QualityPublisher 类': 'QualityPublisher' in classes,
    'BasePublisher 基类': 'BasePublisher' in classes,
    'ReportPublisher': 'ReportPublisher' in classes,
    'MaterialPublisher': 'MaterialPublisher' in classes,
    'TaskRecallPublisher': 'TaskRecallPublisher' in classes,
    'get_publisher 工厂': 'get_publisher' in methods,
    'get_integration 兼容': 'get_integration' in methods,
    'get_all_tasks 查询': 'get_all_tasks' in methods,
    'get_task_by_id 查询': 'get_task_by_id' in methods,
    'get_task_count 统计': 'get_task_count' in methods,
    'is_available 属性': 'is_available' in methods,
    'get_circuit_breaker_status': 'get_circuit_breaker_status' in methods,
    'CircuitBreaker.call': 'call' in methods,
    'CircuitBreaker.get_status': 'get_status' in methods,
    '_store_task 内部': '_store_task' in methods,
}
print('=== 声称 vs 实际 ===')
ok = 0
for k, v in checks.items():
    status = '✅' if v else '❌'
    print(f'  {status} {k}')
    if v:
        ok += 1
print(f'\n通过: {ok}/{len(checks)}')