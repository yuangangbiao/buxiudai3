"""验证调度中心部门查看API"""
import requests, json

LOG = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\re_sync_result.log'

def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')

log("=" * 60)
log("直接用正确路径测试调度中心部门查看API")
log("=" * 60)

# 1. 不强制同步（读取容器中心缓存）
try:
    r = requests.get('http://127.0.0.1:5003/api/dispatch-center/operators/wechat-departments', timeout=10)
    log(f"GET (cache) HTTP {r.status_code}")
    log(json.dumps(r.json(), ensure_ascii=False, indent=2)[:2000])
except Exception as e:
    log(f"失败: {e}")

log("")

# 2. 强制同步（从云端拉取）
try:
    r = requests.get('http://127.0.0.1:5003/api/dispatch-center/operators/wechat-departments?force_cloud=1', timeout=30)
    log(f"GET (force_cloud) HTTP {r.status_code}")
    log(json.dumps(r.json(), ensure_ascii=False, indent=2)[:2000])
except Exception as e:
    log(f"失败: {e}")

log("")
log("完成")
