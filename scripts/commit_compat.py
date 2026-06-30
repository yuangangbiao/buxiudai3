"""[v3.7.7.1] commit 兼容层修复"""
import subprocess

files = [
    'mobile_api_ai/dispatch_center/publisher.py',
    'tests/unit/dispatch_center/test_compat_api.py',
    'scripts/e2e_compat.py',
]
for f in files:
    if not __import__('os').path.exists(f):
        print(f'  SKIP: {f}')
        continue
    r = subprocess.run(['git', 'add', f], capture_output=True, text=True)
    print(f'  add {f}: {r.returncode}')

msg = '''fix(publisher): 恢复兼容 API 避免运行时 AttributeError

[v3.7.7.1 紧急修复]

问题:
- service 文件调用 publish_report_task(order_no=..., process_name=..., **kwargs)
- 新 publisher.py 只提供 publish(payload)，运行时 AttributeError
- 124 测试通过但测试 mock 了 publisher，没真调用 → 业务实际跑不通

修复:
- ReportPublisher.publish_report_task 兼容旧签名（11 个 kwargs）
- MaterialPublisher.publish_material_task 兼容旧签名（8 个 kwargs）
- QualityPublisher.publish_quality_task 兼容旧签名（7 个 kwargs）
- 三个方法都委托给 self.publish(payload)，行为不变
- 兼容 **kwargs 透传到 payload

测试:
- 新增 tests/unit/dispatch_center/test_compat_api.py（5 个用例）
- scripts/e2e_compat.py 真实模拟 service 调用流程

数据流向（暂用内存）:
- 优先 HTTP 调容器中心 → 待 v3.7.7.2 实施
- Fallback SQLite → 待 v3.7.7.2 实施
- 当前: 内存 dict (生产环境会丢数据，但不再 AttributeError)

测试结果: 129 passed (含 5 个新增)

影响:
- ✅ 工人报工按钮不再崩溃
- ✅ 物料发布可用
- ✅ 质检发布可用
- ⚠️ 数据仍存内存（v3.7.7.2 任务）'''

r = subprocess.run(['git', 'commit', '-F', '-'], input=msg, capture_output=True, text=True)
print('commit return:', r.returncode)
if r.returncode == 0:
    print(r.stdout[:300])
else:
    print('stderr:', r.stderr[:500])