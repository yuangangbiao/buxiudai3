"""测试云端企业微信通讯录API"""
import urllib.request, json

# 尝试多个可能的API Key
api_keys = [
    'Wk9Q-8X7Z-3K2M-5P6L',          # wechat_cloud.py 中硬编码的key
    'dev-local-cloud-api-key',        # .env 中的key
]

for key in api_keys:
    try:
        req = urllib.request.Request(
            'http://124.223.57.82:5006/api/wechat/users',
            headers={'X-API-Key': key}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        print(f'Key "{key}": code={data.get("code")}, users={data.get("count", len(data.get("users",[])))}, depts={len(data.get("departments",[]))}')
        if data.get('departments'):
            for d in data['departments'][:5]:
                print(f'  dept: {d.get("name")} (id={d.get("id")}, parentid={d.get("parentid")})')
        break
    except urllib.error.HTTPError as e:
        print(f'Key "{key}": HTTP {e.code} {e.reason}')
    except Exception as e:
        print(f'Key "{key}": {type(e).__name__}: {e}')
