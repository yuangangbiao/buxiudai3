# HTTP 客户端调用规范

## 1. 规范目的

统一 `mobile_api_ai` 项目中所有 HTTP 调用方式，避免：
- 混用 `urllib` / `urllib2` / `requests`
- Content-Type 设置不一致导致 400 错误
- 缺少日志记录，问题难以排查
- 异常处理不统一

## 2. 规范要求

### 2.1 禁止的写法

```python
# ❌ 禁止：使用 urllib/urllib2/urllib3
import urllib.request
req = urllib.request.Request(url, data=payload, headers={...})
resp = urllib.request.urlopen(req)

# ❌ 禁止：requests.post 使用 data= 参数发送 JSON
requests.post(url, data=json.dumps(payload),
               headers={'Content-Type': 'application/json'})

# ❌ 禁止：手动拼接 URL 参数
url = base_url + '/' + endpoint + '?token=' + token

# ❌ 禁止：没有超时
requests.post(url, json=payload)

# ❌ 禁止：静默吞掉异常
try:
    requests.post(url, json=payload)
except:
    pass
```

### 2.2 推荐的写法

```python
# ✅ 必须：使用 requests.post(json=...) 自动处理 Content-Type
import requests
resp = requests.post(url, json=payload, timeout=10)

# ✅ 必须：使用 params= 传递 URL 参数
resp = requests.get(url, params={'token': token}, timeout=5)

# ✅ 必须：统一的 HTTP 客户端
from utils.http_client import SyncBridgeClient
SyncBridgeClient.post('/api/sync/sub-step-report', data=payload)
```

## 3. 统一客户端类

### 3.1 文件位置

`mobile_api_ai/utils/http_client.py`

### 3.2 SyncBridgeClient（调用 8008 sync_bridge）

```python
"""
统一调用 sync_bridge (8008) 的客户端
所有调用 8008 的代码必须使用此类，禁止直接使用 requests/urllib
"""

import requests
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class SyncBridgeClient:
    """统一调用 sync_bridge 的客户端"""

    BASE_URL = os.getenv('SYNC_BRIDGE_URL', 'http://127.0.0.1:8008')
    DEFAULT_TIMEOUT = 10  # 秒

    @classmethod
    def post(cls, endpoint: str, data: dict, timeout: Optional[int] = None) -> dict:
        """
        POST 请求

        Args:
            endpoint: API 端点，如 '/api/sync/sub-step-report'
            data: 请求体数据，会自动序列化为 JSON
            timeout: 超时时间（秒），默认 10

        Returns:
            dict: 响应 JSON

        Raises:
            SyncBridgeError: 请求失败时抛出
        """
        url = f"{cls.BASE_URL}{endpoint}"
        timeout = timeout or cls.DEFAULT_TIMEOUT

        try:
            resp = requests.post(
                url,
                json=data,
                timeout=timeout,
                headers={'User-Agent': 'mobile-api-ai/1.0'}
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info('[SyncBridge] POST %s -> %s', endpoint, resp.status_code)
            return result
        except requests.exceptions.Timeout:
            logger.error('[SyncBridge] POST %s 超时(%ds)', endpoint, timeout)
            raise SyncBridgeError(f'请求超时: {endpoint}')
        except requests.exceptions.RequestException as e:
            logger.error('[SyncBridge] POST %s 失败: %s', endpoint, e)
            raise SyncBridgeError(f'请求失败: {e}')

    @classmethod
    def get(cls, endpoint: str, params: Optional[dict] = None, timeout: Optional[int] = None) -> dict:
        """GET 请求"""
        url = f"{cls.BASE_URL}{endpoint}"
        timeout = timeout or cls.DEFAULT_TIMEOUT

        try:
            resp = requests.get(url, params=params, timeout=timeout,
                              headers={'User-Agent': 'mobile-api-ai/1.0'})
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error('[SyncBridge] GET %s 失败: %s', endpoint, e)
            raise SyncBridgeError(f'请求失败: {e}')


class SyncBridgeError(Exception):
    """sync_bridge 调用异常"""
    pass
```

### 3.3 ContainerCenterClient（调用容器中心）

```python
"""
统一调用容器中心 API 的客户端
"""

import requests
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class ContainerCenterClient:
    """统一调用容器中心 API 的客户端"""

    BASE_URL = os.getenv('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')
    DEFAULT_TIMEOUT = 10

    @classmethod
    def post(cls, endpoint: str, data: dict, timeout: Optional[int] = None) -> dict:
        url = f"{cls.BASE_URL}{endpoint}"
        timeout = timeout or cls.DEFAULT_TIMEOUT

        try:
            resp = requests.post(url, json=data, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error('[ContainerCenter] POST %s 失败: %s', endpoint, e)
            raise

    @classmethod
    def get(cls, endpoint: str, params: Optional[dict] = None, timeout: Optional[int] = None) -> dict:
        url = f"{cls.BASE_URL}{endpoint}"
        timeout = timeout or cls.DEFAULT_TIMEOUT

        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error('[ContainerCenter] GET %s 失败: %s', endpoint, e)
            raise
```

## 4. 重构清单

### 4.1 需要重构的文件

| 文件 | 当前写法 | 重构后 |
|------|---------|--------|
| `_sync_bridge_call.py` | `urllib.request` | `SyncBridgeClient.post()` |
| `dispatch_center.py` | `requests.post(json=...)` | `SyncBridgeClient.post()` |
| `container_center_api.py` | `requests.post(json=...)` | `ContainerCenterClient.post()` |
| `app.py` | `requests.post(json=...)` | `ContainerCenterClient.post()` |
| `wechat_work_bot_v2.py` | `requests.post(json=...)` | `SyncBridgeClient.post()` |
| `api/legacy_routes.py` | `requests.post(json=...)` | `SyncBridgeClient.post()` |
| `api/process.py` | `subprocess.Popen` | `SyncBridgeClient.post()` |

### 4.2 重构示例

**Before:**
```python
# _sync_bridge_call.py
import urllib.request, json, sys
payload = json.loads(sys.argv[1])
data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
req = urllib.request.Request(
    'http://127.0.0.1:8008/api/sync/sub-step-report',
    data=data,
    headers={'Content-Type': 'application/json; charset=utf-8'}
)
resp = urllib.request.urlopen(req)
```

**After:**
```python
# _sync_bridge_call.py
import sys
sys.path.insert(0, __file__)
from utils.http_client import SyncBridgeClient, SyncBridgeError
payload = json.loads(sys.argv[1])
try:
    result = SyncBridgeClient.post('/api/sync/sub-step-report', data=payload)
except SyncBridgeError as e:
    logger.error('同步失败: %s', e)
    sys.exit(1)
```

## 5. 日志规范

每次 HTTP 调用必须记录：
- 请求的端点
- 状态码（成功/失败）
- 响应体前 200 字符（失败时）
- 超时/异常信息

```python
# 标准日志格式
logger.info('[ServiceName] POST /endpoint -> 200 OK | response_time: 0.15s')
logger.warning('[ServiceName] POST /endpoint -> 400 | body: {"code": 1201}')
logger.error('[ServiceName] POST /endpoint -> 500 | error: connection timeout')
```

## 6. 错误处理规范

```python
# ✅ 正确：记录错误并重新抛出
try:
    result = SyncBridgeClient.post('/api/sync/sub-step-report', data=payload)
except SyncBridgeError as e:
    logger.error('同步失败: %s', e)
    raise  # 或者 return error_response

# ✅ 正确：非关键调用，吞掉异常但记录
try:
    SyncBridgeClient.post('/api/sync/log', data=payload)
except SyncBridgeError:
    logger.warning('日志同步失败（忽略）: %s', payload)  # 必须记录！

# ❌ 错误：静默吞掉
try:
    requests.post(url, json=data)
except:
    pass  # 不知道有没有成功，也无法排查问题
```

## 7. 验证检查

### 7.1 代码审查检查点

```bash
# 搜索禁止的模式
grep -rn "urllib.request\|urllib2\|urllib3" --include="*.py" mobile_api_ai/
grep -rn "requests.post.*data=" --include="*.py" mobile_api_ai/
grep -rn "Content-Type.*application/json" --include="*.py" mobile_api_ai/

# 搜索可疑的裸 except
grep -rn "except:" --include="*.py" mobile_api_ai/ | grep -v "except Exception"
```

### 7.2 冒烟测试

每次重构后执行：
```bash
# 测试 8008 连通性
curl -X POST http://127.0.0.1:8008/api/sync/sub-step-report \
  -H "Content-Type: application/json" \
  -d '{"order_no":"TEST","step_name":"测试","quantity":1}'

# 期望返回: {"code": 1001, "message": "..."} 或 {"code": 0, ...}
```

## 8. 相关文档

- [全流程架构图](docs/全流程架构图.md)
- [sync_bridge.py](../sync_bridge.py) - 8008 服务端实现
- [sync_bridge_server.py](../sync_bridge_server.py) - 8008 服务启动入口
