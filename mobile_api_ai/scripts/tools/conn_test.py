import json, urllib.request, sys

results = []
def test(url, label):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        data = r.read().decode()
        results.append(f"[OK] {label}: HTTP {r.status} ({len(data)} bytes)")
        if data and label != "调度中心页面":
            parsed = json.loads(data)
            results.append(f"  data: {json.dumps(parsed, ensure_ascii=False, indent=2)[:300]}")
    except Exception as e:
        results.append(f"[FAIL] {label}: {e}")

test("http://localhost:5002/container/", "容器仪表盘")
test("http://localhost:5000/api/dispatch-center/", "调度中心页面")
test("http://localhost:5000/api/dispatch-center/status", "调度中心状态")
test("http://localhost:5000/api/dispatch-center/containers", "调度中心容器列表")

with open(r"d:\yuan\conn_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print("\n".join(results))
