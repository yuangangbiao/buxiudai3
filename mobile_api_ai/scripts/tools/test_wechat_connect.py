import urllib.request, json, sys

print("=== 容器中心联通测试 ===", flush=True)

# Test 1: 容器中心直连
print("\n[1] 容器中心直连(5002)...", flush=True)
try:
    r = urllib.request.urlopen('http://127.0.0.1:5002/api/v4/health', timeout=5)
    d = json.loads(r.read().decode())
    print(f"    OK: status={d.get('data',{}).get('status')}", flush=True)
except Exception as e:
    print(f"    FAIL: {e}", flush=True)

# Test 2: 容器中心消息API
print("\n[2] 容器中心消息API...", flush=True)
try:
    payload = json.dumps({"content":"test","to":"@all","msg_type":"markdown"}).encode()
    req = urllib.request.Request('http://127.0.0.1:5002/api/v4/messages', data=payload,
                                  headers={'Content-Type': 'application/json'})
    r = urllib.request.urlopen(req, timeout=10)
    d = json.loads(r.read().decode())
    print(f"    OK: code={d.get('code')}, msg={d.get('message')}", flush=True)
except urllib.error.HTTPError as e:
    print(f"    HTTP {e.code}: {e.read().decode()[:300]}", flush=True)
except Exception as e:
    print(f"    FAIL: {e}", flush=True)

# Test 3: 调度中心发送
print("\n[3] 调度中心发送消息...", flush=True)
try:
    payload = json.dumps({"content":"**联通测试**\n调度->容器->微信","channels":["wechat_group"]}).encode()
    req = urllib.request.Request('http://127.0.0.1:5003/api/dispatch-center/messages/send', data=payload,
                                  headers={'Content-Type': 'application/json'})
    r = urllib.request.urlopen(req, timeout=15)
    d = json.loads(r.read().decode())
    print(f"    OK: code={d.get('code')}, msg={d.get('message')}", flush=True)
    print(f"    data: {json.dumps(d.get('data',{}), ensure_ascii=False)}", flush=True)
except urllib.error.HTTPError as e:
    print(f"    HTTP {e.code}: {e.read().decode()[:300]}", flush=True)
except Exception as e:
    print(f"    FAIL: {e}", flush=True)

print("\n=== 测试完成 ===", flush=True)