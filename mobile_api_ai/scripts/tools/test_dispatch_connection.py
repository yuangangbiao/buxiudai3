import sys, json, urllib.request

def test_url(label, url):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        data = r.read().decode()
        print(f"[OK] {label}: HTTP {r.status} ({len(data)} bytes)")
        if r.status == 200 and data:
            parsed = json.loads(data)
            preview = json.dumps(parsed, ensure_ascii=False, indent=2)[:400]
            print(f"  Response: {preview}")
        return True
    except Exception as e:
        print(f"[FAIL] {label}: {e}")
        return False

print("=" * 60)
print("调度中心 ↔ 容器中心 连接测试")
print("=" * 60)

# 1. 测试容器中心直接访问
test_url("容器中心健康检查", "http://localhost:5002/health")

# 2. 测试调度中心页面
test_url("调度中心页面", "http://localhost:5000/api/dispatch-center/")

# 3. 测试调度中心状态 API
test_url("调度中心状态", "http://localhost:5000/api/dispatch-center/status")

# 4. 测试调度中心容器列表 API
test_url("调度中心容器列表", "http://localhost:5000/api/dispatch-center/containers")
