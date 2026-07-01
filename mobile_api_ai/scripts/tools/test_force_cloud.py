"""测试调度中心 force_cloud=1 完整链路"""
import requests
import json

# 1. 测试容器中心 sync 端点
print("=" * 60)
print("1. 容器中心 sync 端点 (直接测试)")
print("=" * 60)
r = requests.post('http://localhost:5002/api/enterprise/structure/sync', timeout=30)
print(f"HTTP {r.status_code}")
data = r.json()
print(json.dumps(data, ensure_ascii=False, indent=2)[:500])

# 2. 测试调度中心 force_cloud=1
print()
print("=" * 60)
print("2. 调度中心 force_cloud=1")
print("=" * 60)
r2 = requests.get(
    'http://localhost:5003/api/dispatch-center/operators/wechat-departments?force_cloud=1',
    timeout=60
)
print(f"HTTP {r2.status_code}")
data2 = r2.json()
print(json.dumps(data2, ensure_ascii=False, indent=2)[:1000])

# 3. 验证 source 是否为 cloud_sync
dd = data2.get('data', {})
print(f"\n   source={dd.get('source','?')}")
print(f"   departments={len(dd.get('departments',[]))}")
print(f"   flat_count={dd.get('flat_count')}")
