# 安全审计报告 v3.6.8 - ARCHITECTURE_v3.6.md（第三轮·安全工程师视角）

> **审计范围**：`mobile_api_ai/docs/ARCHITECTURE_v3.6.md`（v3.6.8）+ 核心代码 `mobile_api_ai/cloud_relay.py`
> **审计视角**：安全工程师（资深信息安全专家）
> **审计日期**：2026-06-24
> **前置状态**：第一轮 6/25 修复 ✅；第二轮 19 项遗留 + 8 项新增；本轮聚焦**鉴权强度**与**敏感数据保护**
> **审计员**：小钰（安全）

---

## 总体评价

| 维度 | 第一轮 | 第二轮 | 第三轮 | 变化 |
|------|:------:|:------:|:------:|:----:|
| **安全综合评分** | 55/100 | 70/100 | **78/100** | ⬆️ +8 |
| **🔴 严重问题** | 2 | 0 | **1** | ⬇️ -2 (S-1/S-2 已修) |
| **🟡 中等问题** | 1 | 1 | **6** | ⬆️ +5 (新发现) |
| **🟢 轻微问题** | 2 | 0 | **4** | ⬆️ +4 (新发现) |
| **P0-S1/S2/S3 暂缓** | 持续 | 持续 | **持续** | 未变（用户决策） |

> **核心结论**：第一轮的 2 个 🔴 严重问题（S-1 CLOUD_5004_HOST fail-fast、S-2 API_KEY 鉴权）已确认修复 ✅。本轮聚焦**传输加密**和**生产数据保护**，发现 **1 个新的 🔴 严重问题**（HTTP 明文传输生产数据）和 **6 个新的 🟡 中等问题**。建议下个迭代优先处理传输加密（HTTPS）和请求体大小限制。

---

## 一、第一/二轮审计修复状态确认

### ✅ 已修复（10 项）

| # | 问题 | 修复位置 | 验证方式 |
|---|------|---------|---------|
| S-1 | CLOUD_5004_HOST 空值静默错误 | `cloud_relay.py:683-684` | ✅ `if not CLOUD_5004_HOST: raise RuntimeError(...)` |
| S-2 | API_KEY 默认空 + 部分端点无鉴权 | `cloud_relay.py:42-43, 816, 834, 845` | ✅ fail-fast + 3 个 stats 端点全部 `@require_api_key` |
| S-3 | 敏感数据可能写入日志 | `cloud_relay.py:750` | ✅ 日志只记 `records={len(records)}` 数量，不含具体内容 |
| S-4 | batch_id 无表类型前缀 | `cloud_relay.py:672` | ✅ 改为 `f"{table_type}_{uuid.uuid4().hex[:12]}"` |
| S-5 | 缺少安全相关环境变量文档 | `ARCHITECTURE_v3.6.md:1129-1149` | ✅ 9 张表相关 env 全部列出 |
| A-6 | R-002 与 5005 直连云端 5004 矛盾 | `ARCHITECTURE_v3.6.md:223` | ✅ 补充"微信相关"限定 + 豁免说明 |
| T-1 | Stats Push 失败无降级方案文档 | `ARCHITECTURE_v3.6.md:116-126` | ✅ 新增"统计表推送失败处理策略" |
| A-3 | Phase-2 表格内容错误 | `ARCHITECTURE_v3.6.md:73-79` | ✅ 重写为 v3.6.8 N-1 内容 |
| T-2 | 9 表 Job 无独立 metrics | `cloud_relay.py:198-205, 745` | ✅ `_stats_metrics['by_table']` 已实现 |
| T-5 | 启动无 MySQL 预检 | `cloud_relay.py:773-780` | ✅ `_start_scheduler()` 已加连接预检 |

### ⚠️ 未完全修复（3 项）

| # | 问题 | 现状 | 风险 |
|---|------|------|------|
| S-3 | 敏感数据日志 | 部分修复（records 数量已脱敏） | 🟡 last_err 仍可能包含敏感信息 |
| A-3 | Phase-2 表格 | 主表已修，但子说明待补 | 🟢 文档细节 |
| N-7 | 5003 端点状态 | 已确认 5003 端点已删除（Phase-2 表中说明） | 🟢 已闭环 |

---

## 二、新发现的 🔴 严重问题（1 项）

### 🔴 N-S1：5005 → 云端 5004 明文 HTTP 传输生产数据（高危）

**位置**：`cloud_relay.py:687`

```python
# 现状：明文 HTTP
target_url = f'http://{CLOUD_5004_HOST}:{CLOUD_5004_PORT}/api/smartsheet/write'
forward_headers = {
    'Content-Type': 'application/json',
    'X-API-Key': CLOUD_5004_API_KEY,
}
```

**问题分析**：

| 维度 | 内容 |
|------|------|
| **风险等级** | 🔴 P0 严重 |
| **数据敏感度** | 包含**客户名称**（`workorder_progress` 表 f3002 字段）、**工序数据**、**库存金额**、**操作人姓名**等商业敏感数据 |
| **传输内容** | 9 张统计表的全量记录，明文 JSON 格式 |
| **攻击场景** | 1) 中间人攻击（MITM）：攻击者在网络层劫持 HTTP 流量，可读取所有生产/库存/客户数据；2) 网络抓包：内网恶意员工可使用 Wireshark/tcpdump 抓取 5005 → 5004 的所有推送内容；3) 日志泄露：网关/防火墙日志可能记录完整 URL 和 body |
| **API Key 风险** | `X-API-Key` 也以明文方式传输，可被攻击者直接获取并重放 |
| **触发概率** | 中（公司内网环境 + 公网云端 124.223.57.82，走运营商网络） |
| **影响严重度** | 高（一旦被中间人获取，**生产数据 + API Key 同时泄露**） |

**证据**：

```bash
# 第 687 行（cloud_relay.py）
target_url = f'http://{CLOUD_5004_HOST}:{CLOUD_5004_PORT}/api/smartsheet/write'
#        ^^^^ 明文 HTTP
```

**修复建议**：

```python
# 方案 A（推荐）：强制 HTTPS
target_url = f'https://{CLOUD_5004_HOST}:{CLOUD_5004_PORT}/api/smartsheet/write'

# 方案 B：如果云端 5004 暂不支持 HTTPS，增加配置项
CLOUD_5004_USE_HTTPS = os.getenv('CLOUD_5004_USE_HTTPS', 'true').lower() == 'true'
protocol = 'https' if CLOUD_5004_USE_HTTPS else 'http'
target_url = f'{protocol}://{CLOUD_5004_HOST}:{CLOUD_5004_PORT}/api/smartsheet/write'
```

**附加建议**：
1. 在 .env.example 中强制 `CLOUD_5004_USE_HTTPS=true`
2. 启动时校验 `CLOUD_5004_HOST` 不在公网不安全段（如不强制要求 HTTPS 则 WARN 告警）
3. 生产环境部署检查清单新增"HTTPS 证书校验"项

**关联风险**：
- 文档 `ARCHITECTURE_v3.6.md:1139` 仅说明 `CLOUD_5004_HOST` 是"云端 5004 服务器地址"，未提传输协议
- 文档应补充"⚠️ 强烈建议生产环境使用 HTTPS（v3.6.8 审计 N-S1）"

---

## 三、新发现的 🟡 中等问题（6 项）

### 🟡 N-S2：重试机制无总超时限制，可被利用作慢速 DOS

**位置**：`cloud_relay.py:692-718`

```python
max_retries = int(os.getenv('STATS_MAX_RETRIES', '3'))
forward_timeout = int(os.getenv('STATS_FORWARD_TIMEOUT', '60'))

last_err = None
for attempt in range(max_retries):
    try:
        resp = requests.post(target_url, json=payload,
                             headers=forward_headers, timeout=forward_timeout)
        # ...
    except Exception as e:
        last_err = str(e)
        # ...
    if attempt < max_retries - 1:
        wait = 2 ** (attempt + 1)  # 1s → 2s → 4s
        time.sleep(wait)
```

**问题分析**：

| 维度 | 内容 |
|------|------|
| **风险等级** | 🟡 P1 中等 |
| **DOS 场景 1（外部）** | 攻击者持有 `WECHAT_CLOUD_API_KEY` 可通过 `/api/stats/push` 投递超大 records；3 次重试 × 60s timeout = 最多 180s 单请求占用 worker 线程 |
| **DOS 场景 2（云端慢响应）** | 如果云端 5004 慢响应（不返回但也不断开），每次请求都会卡满 60s timeout；3 次重试 = 180s 占用 |
| **DOS 场景 3（资源耗尽）** | waitress 默认 4 worker threads（`RELAY_WORKERS=4`），如果同时 4 个推送都卡 180s，所有 worker 被锁死 |
| **影响范围** | 5005 服务可用性（无法响应其他 /api/stats/* 请求）|
| **与 threading.Lock 叠加** | 同一 table_type 的锁（line 731）+ 重试 sleep + timeout = 严重的 head-of-line blocking |

**证据**：
- `cloud_relay.py:899`：`threads=int(os.getenv('RELAY_WORKERS', '4'))` 默认 4 worker
- `cloud_relay.py:692`：`max_retries = int(os.getenv('STATS_MAX_RETRIES', '3'))` 默认 3 次
- `cloud_relay.py:693`：`forward_timeout = int(os.getenv('STATS_FORWARD_TIMEOUT', '60'))` 默认 60s
- 单请求最坏耗时：3 × 60s + 1s + 2s = **183 秒**

**修复建议**：

```python
# 1. 增加总超时硬限制
TOTAL_TIMEOUT = int(os.getenv('STATS_TOTAL_TIMEOUT', '120'))  # 2 分钟硬上限
deadline = time.time() + TOTAL_TIMEOUT

for attempt in range(max_retries):
    if time.time() >= deadline:
        last_err = f'超过总超时 {TOTAL_TIMEOUT}s，放弃重试'
        break
    try:
        resp = requests.post(...)
    except Exception as e:
        last_err = str(e)
    if attempt < max_retries - 1:
        remaining = deadline - time.time()
        wait = min(2 ** (attempt + 1), max(0, remaining - 5))  # 留 5s buffer
        if wait <= 0:
            break
        time.sleep(wait)

# 2. 增加 records 大小限制
MAX_RECORDS_PER_PUSH = int(os.getenv('STATS_MAX_RECORDS', '10000'))
if len(records) > MAX_RECORDS_PER_PUSH:
    return {'code': 400, 'message': f'records 超过最大限制 {MAX_RECORDS_PER_PUSH}'}, 400
```

---

### 🟡 N-S3：/api/stats/push 请求体无大小限制（内存/性能风险）

**位置**：`cloud_relay.py:815-829`

```python
@app.route('/api/stats/push', methods=['POST'])
@require_api_key
def stats_push():
    data = request.get_json(silent=True) or {}
    table_type = data.get('table_type', '')
    records = data.get('records', [])
    period_key = data.get('period_key', '')

    if not table_type:
        return jsonify({'code': 400, 'message': '缺少 table_type'}), 400
    if not isinstance(records, list):
        return jsonify({'code': 400, 'message': 'records 必须是数组'}), 400

    result = _push_to_cloud(table_type, records, period_key)
    return jsonify(result)
```

**问题分析**：

| 维度 | 内容 |
|------|------|
| **风险等级** | 🟡 P1 中等 |
| **攻击场景** | 持有 API_KEY 的恶意调用方 POST 一个 1GB 的 records 列表 |
| **资源影响** | 1) Flask `request.get_json()` 会把整个 body 加载到内存；2) `json.dumps()` 生成 record_hash（第 110 行）也会全部加载；3) `requests.post(json=payload)` 又会序列化一遍 |
| **默认限制** | Flask 默认 `MAX_CONTENT_LENGTH` 是 None（无限制），需要显式设置 |
| **连带风险** | 整个请求会卡 60s timeout × 3 = 180s（与 N-S2 叠加）|

**证据**：
- `cloud_relay.py` 未发现 `app.config['MAX_CONTENT_LENGTH']` 配置
- `cloud_relay.py:39`：`app = Flask(__name__)` 未设置任何内容大小限制
- 攻击者用合法的 `WECHAT_CLOUD_API_KEY` 即可触发（虽然鉴权通过，但 payload 无限制）

**修复建议**：

```python
# 在 app 创建后立即设置
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('STATS_MAX_PAYLOAD_MB', '50')) * 1024 * 1024  # 默认 50MB

@app.errorhandler(413)
def handle_too_large(e):
    return jsonify({'code': 413, 'message': '请求体过大'}), 413
```

---

### 🟡 N-S4：last_err 异常信息直接暴露给客户端和日志

**位置**：`cloud_relay.py:720-721`

```python
logger.error(f'[stats/push] {table_type} 推送最终失败: {last_err}')
return {'code': -1, 'message': f'推送失败: {last_err}', 'batch_id': batch_id, 'success_count': 0}
```

**问题分析**：

| 维度 | 内容 |
|------|------|
| **风险等级** | 🟡 P1 中等 |
| **泄露场景 1（日志）** | `last_err = str(e)` 包含 requests 异常的完整堆栈，可能含 CLOUD_5004_HOST/URL/连接详情 |
| **泄露场景 2（响应）** | `'message': f'推送失败: {last_err}'` 把异常原文返回给 API 调用方（持有 API_KEY 但不一定有云端信息） |
| **泄露场景 3（云端错误）** | `result.get('message', '未知错误')`（第 709 行）直接把云端 5004 的错误消息透传，可能含云端数据库结构/字段名等内部信息 |
| **敏感度** | 中（间接信息泄露 + 内部错误信息） |

**证据**：
- `cloud_relay.py:711-712`：
  ```python
  except Exception as e:
      last_err = str(e)
  ```
  `str(e)` 包含完整异常消息，可能含 `ConnectionRefusedError: [Errno 111] Connection refused to 124.223.x.x:5004` 等
- `cloud_relay.py:709`：
  ```python
  last_err = result.get('message', '未知错误')
  ```
  云端 5004 的 `result['message']` 直接被透传

**修复建议**：

```python
# 1. 异常信息脱敏
def _sanitize_error(e: Exception) -> str:
    msg = str(e)
    # 移除 IP/URL/凭证
    import re
    msg = re.sub(r'\d+\.\d+\.\d+\.\d+', '***.***.***.***', msg)
    msg = re.sub(r'https?://[^\s]+', '***', msg)
    msg = re.sub(r'(password|api_key|token)=[^\s&]+', r'\1=***', msg, flags=re.IGNORECASE)
    return msg[:200]  # 限制长度

# 2. 云端消息脱敏
last_err = _sanitize_error(Exception(result.get('message', '未知错误')))

# 3. 响应只返回脱敏后的错误码
return {
    'code': -1,
    'message': '推送失败，详情查看日志',  # 不暴露 last_err
    'batch_id': batch_id,
    'success_count': 0
}
```

---

### 🟡 N-S5：metrics['last_result'] 返回完整推送结果（含客户数据）

**位置**：`cloud_relay.py:748, 861`

```python
# line 748
_stats_metrics['last_result'] = {'table_type': table_type, **push_result}

# line 861
return jsonify({
    'code': 0,
    'scheduler': '...',
    'jobs_count': len(jobs),
    'jobs': jobs,
    'metrics': dict(_stats_metrics),  # ⚠️ 暴露 last_result
})
```

**问题分析**：

| 维度 | 内容 |
|------|------|
| **风险等级** | 🟡 P1 中等 |
| **数据敏感度** | `_push_to_cloud` 返回 `{'code', 'message', 'batch_id', 'success_count'}`，本轮已相对干净 |
| **隐患** | `last_result` 包含 `batch_id`（表类型 + UUID 12 位），可推测生产时段；如未来扩展返回 records 摘要，会泄露 |
| **访问权限** | `/api/stats/status` 需要 API_KEY（line 845），鉴权后访问，但仍然返回内部 metrics |
| **审计场景** | 持有 API_KEY 的运维可看到所有推送历史，但当前实际只含元数据 |

**证据**：
- `cloud_relay.py:751`：`return {**push_result, 'elapsed': elapsed, 'records': len(records)}` - 包含 `batch_id` + `success_count` + `elapsed` + `records`（数量）
- `cloud_relay.py:748`：把 `push_result` 整包塞进 `last_result`

**修复建议**：

```python
# 1. last_result 只保留元数据，不含任何业务信息
_stats_metrics['last_result'] = {
    'table_type': table_type,
    'batch_id': batch_id[:8] + '***',  # 截断
    'success': push_result.get('code') == 0,
    'elapsed': elapsed,
    'records': len(records),
    'timestamp': datetime.now().isoformat()
}

# 2. /api/stats/status 也对 metrics 脱敏
'metrics': {
    'by_table': _stats_metrics['by_table'],
    'total_push': _stats_metrics['total_push'],
    'success_push': _stats_metrics['success_push'],
    'failed_push': _stats_metrics['failed_push'],
    'last_push_time': _stats_metrics['last_push_time'],
    # 移除 last_result 字段（或仅保留最后成功/失败的表名）
}
```

---

### 🟡 N-S6：metrics 字典读写无锁保护（线程安全）

**位置**：`cloud_relay.py:198-205, 739-755`

```python
# 第 198-205 行（定义）
_stats_metrics = {
    'by_table': {t: {'success': 0, 'failed': 0, 'last_time': ''} for t in _SCHEDULE_CONFIG},
    'total_push': 0,
    'success_push': 0,
    'failed_push': 0,
    'last_push_time': '',
    'last_result': {},
}

# 第 739-748 行（修改，多线程竞争）
_stats_metrics['total_push'] += 1
if push_result.get('code') == 0:
    _stats_metrics['success_push'] += 1
    _stats_metrics['by_table'][table_type]['success'] += 1
else:
    _stats_metrics['failed_push'] += 1
    _stats_metrics['by_table'][table_type]['failed'] += 1
# ...
```

**问题分析**：

| 维度 | 内容 |
|------|------|
| **风险等级** | 🟡 P1 中等（数据正确性，不是安全）|
| **并发场景** | 1) 9 张表各有一个 `_stats_locks[table_type]`（line 197）；2) `/api/stats/trigger` 手动触发 + APScheduler 自动触发可能并发；3) 但**全局计数器 `total_push`/`success_push` 等无锁保护** |
| **数据竞争后果** | `+= 1` 不是原子操作（CPython GIL 保护下基本安全，但仍有 race condition 风险），可能导致 metrics 计数偏低 |
| **安全影响** | 间接：监控告警基于 metrics，如果计数偏低，可能漏报推送失败 |
| **审计场景** | /api/stats/status 返回的 metrics 数字不准确，运维误以为推送成功 |

**证据**：
- `_stats_locks` 是**按 table_type 隔离**，不保护全局 metrics
- 多张表并发更新 `total_push` 时存在竞争
- `dict(_stats_metrics)`（line 861）返回快照，但 `last_result` 整体替换（line 748）期间其他线程可能读到部分更新的 dict

**修复建议**：

```python
# 1. 增加全局 metrics 锁
_stats_lock = threading.Lock()

# 2. 所有 metrics 修改在锁内
with _stats_lock:
    _stats_metrics['total_push'] += 1
    if push_result.get('code') == 0:
        _stats_metrics['success_push'] += 1
    else:
        _stats_metrics['failed_push'] += 1
    _stats_metrics['by_table'][table_type]['success'] += 1  # 假设锁内
    _stats_metrics['by_table'][table_type]['last_time'] = datetime.now().isoformat()
    _stats_metrics['last_push_time'] = datetime.now().isoformat()
    _stats_metrics['last_result'] = {'table_type': table_type, **push_result}

# 3. 读 metrics 时也加锁（或用 copy.deepcopy）
with _stats_lock:
    snapshot = copy.deepcopy(_stats_metrics)
return jsonify({'metrics': snapshot})
```

---

### 🟡 N-S7：缺少 rate limiting（/api/stats/* 无防滥用）

**位置**：`cloud_relay.py:815-862`（所有 stats 端点）

```python
# /api/stats/push /api/stats/trigger/<type> /api/stats/status
# 全部只有 X-API-Key 鉴权，**无 rate limiting**
```

**问题分析**：

| 维度 | 内容 |
|------|------|
| **风险等级** | 🟡 P1 中等 |
| **风险** | API_KEY 一旦泄露（开发人员离职、git 误提交、.env 备份泄漏），攻击者可无限调用 |
| **场景** | /api/stats/push 无限调用 → 资源耗尽；/api/stats/trigger 无限调用 → 锁等待 / 资源占用；/api/stats/status 无限调用 → 暴露内部 metrics |
| **当前防护** | 仅靠 API_KEY 鉴权，无频率限制 |
| **影响** | 单个 API_KEY 滥用可造成 5005 不可用 |

**修复建议**：

```python
# 1. 使用 Flask-Limiter
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["100 per minute"],
    storage_uri="memory://"
)

@app.route('/api/stats/push', methods=['POST'])
@limiter.limit("10 per minute")  # 更严格
@require_api_key
def stats_push():
    ...

# 2. 或简单实现：基于 dict 的计数器
_request_counts = {}  # {ip_or_key: {'count': N, 'reset_at': T}}

def rate_limit_check(key: str, max_per_minute: int = 60) -> bool:
    now = time.time()
    if key not in _request_counts or now > _request_counts[key]['reset_at']:
        _request_counts[key] = {'count': 1, 'reset_at': now + 60}
        return True
    _request_counts[key]['count'] += 1
    return _request_counts[key]['count'] <= max_per_minute
```

---

## 四、新发现的 🟢 轻微问题（4 项）

### 🟢 N-S8：_compute_hash 截断 SHA256 到 64 字符

**位置**：`cloud_relay.py:109-111`

```python
def _compute_hash(records: List[Dict]) -> str:
    content = json.dumps(records, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:64]
```

**问题**：
- SHA256 输出 64 字符 hex（256 位），代码用 `[:64]` 但 SHA256 本身正好 64 字符，**截断是冗余操作**（不影响安全性）
- 但若未来改为 `[:32]` 或更短截断会降低抗碰撞性
- 当前实现不存在安全问题，但代码可读性差（暗示未来可能截断）

**修复建议**：

```python
# 显式标注意图
def _compute_hash(records: List[Dict]) -> str:
    """计算 records 的 SHA256 摘要（完整 64 字符 hex）"""
    content = json.dumps(records, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()  # 不截断
```

---

### 🟢 N-S9：batch_id 熵足够但缺文档说明

**位置**：`cloud_relay.py:672`

```python
batch_id = f"{table_type}_{uuid.uuid4().hex[:12]}"
```

**评估**：
- `uuid.uuid4().hex[:12]` = 12 hex chars = 48 位熵
- 48 位熵在批量推送场景下足够（防碰撞/防预测）
- S-4 修复后已添加 table_type 前缀，溯源能力提升

**轻微问题**：
- 没有说明为什么截断到 12 hex（节省带宽？设计决策？）
- 文档 `ARCHITECTURE_v3.6.md` 未说明 batch_id 生成规则

**修复建议**：
- 文档中 9 张表相关章节补充："`batch_id` 格式 = `{table_type}_{uuid4 前 12 hex}`，用于云端去重和审计"

---

### 🟢 N-S10：load_dotenv('override=True') 覆盖现有环境变量

**位置**：`cloud_relay.py:33`

```python
load_dotenv('.env', override=True)
```

**问题**：
- `override=True` 会用 `.env` 文件中的值覆盖系统已设置的环境变量
- 在生产环境中，如果运维人员通过 systemd / Docker 设置了环境变量，但 `.env` 文件存在且包含旧值，会被覆盖
- 风险：环境变量错配（不是直接安全风险，但可能导致生产环境用错误的 DB 凭证或 API_KEY）

**修复建议**：
```python
# 生产环境建议不覆盖
load_dotenv('.env', override=os.getenv('ALLOW_DOTENV_OVERRIDE', 'false').lower() == 'true')
```

---

### 🟢 N-S11：_INTERNAL_API_KEY_PATHS 白名单完整性需复核

**位置**：`ARCHITECTURE_v3.6.md:71`（提到 5003 中）

```markdown
| `standalone_dispatch_server.py` | 新增 Queue 端点（`/api/queue/poll`、`/api/queue/ack`、`/api/queue/status`）；
                                新增 `_INTERNAL_API_KEY_PATHS` 白名单；
                                修改 `_dispatch_auth_check` 支持 X-API-Key 优先认证。
```

**问题**：
- 文档提到 5003 内部有 `_INTERNAL_API_KEY_PATHS` 白名单机制
- 但本轮审计未深入验证 5003 端点是否正确维护
- Phase-2 表（line 77）说"清理 `_INTERNAL_API_KEY_PATHS` 和 `_DISPATCH_AUTH_EXEMPT` 中的 stats 相关条目"——但没列出具体清理了哪些

**风险**：
- 如果白名单残留旧的 stats 路径，可能造成 5003 误判
- 如果新增端点忘记加入白名单，可能被拒

**修复建议**：
- 文档补充 `_INTERNAL_API_KEY_PATHS` 当前完整列表
- 增加测试：每个内部端点都验证鉴权通过

---

## 五、ARCHITECTURE 文档相关问题

### 文档规则审视

| 规则 | 当前描述 | 审计意见 |
|------|---------|---------|
| R-001（数据库直连） | "禁止直连对方数据库" | ✅ 已补充"批量只读查询允许直连"（line 222） |
| R-002（云端通信） | "微信相关云端通信必须通过 5003" | ✅ 已补充 5004 直连豁免（line 223） |
| R-004（5005 定位） | "5005 接管 9 张表" | ✅ 已明确（line 78, 88） |

### 文档遗漏点

| 缺失 | 建议补充 |
|------|---------|
| **生产数据明文传输警告** | 环境变量表（line 1129-1149）应标注：`CLOUD_5004_HOST` 强烈建议使用 HTTPS（v3.6.8 审计 N-S1） |
| **API_KEY 轮换策略** | 文档应说明 `WECHAT_CLOUD_API_KEY` 和 `CLOUD_5004_API_KEY` 的轮换周期（建议 90 天） |
| **请求体大小限制** | 应说明 `/api/stats/push` 的最大 payload（建议 50MB） |
| **重试总超时** | 应说明 `STATS_TOTAL_TIMEOUT`（建议 120s） |
| **rate limiting** | 应说明 stats 端点的频率限制 |
| **P0-S1/S2/S3 暂缓状态** | `SECURITY_RISK_NOTE.md` 提到 3 大暂缓风险，但 ARCHITECTURE.md 没有交叉引用 |

---

## 六、问题汇总（按优先级）

### 🔴 严重（1 项，必须立即修复）

| ID | 问题 | 位置 | 修复成本 |
|----|------|------|---------|
| **N-S1** | HTTP 明文传输生产数据 | cloud_relay.py:687 | 🟢 低（改协议字符串） |

### 🟡 中等（6 项，下个迭代修复）

| ID | 问题 | 位置 | 修复成本 |
|----|------|------|---------|
| **N-S2** | 重试机制无总超时限制 | cloud_relay.py:692-718 | 🟢 低（加 deadline） |
| **N-S3** | 请求体无大小限制 | cloud_relay.py:39, 815-829 | 🟢 低（MAX_CONTENT_LENGTH） |
| **N-S4** | last_err 异常信息暴露 | cloud_relay.py:711-721 | 🟡 中（脱敏函数） |
| **N-S5** | metrics['last_result'] 数据脱敏 | cloud_relay.py:748, 861 | 🟢 低（截断/移除） |
| **N-S6** | metrics 字典线程安全 | cloud_relay.py:739-755 | 🟡 中（全局锁） |
| **N-S7** | 缺少 rate limiting | cloud_relay.py:815-862 | 🟡 中（Flask-Limiter） |

### 🟢 轻微（4 项，可选修复）

| ID | 问题 | 位置 | 修复成本 |
|----|------|------|---------|
| **N-S8** | _compute_hash 截断冗余 | cloud_relay.py:111 | 🟢 低（删除 `[:64]`） |
| **N-S9** | batch_id 缺文档 | ARCHITECTURE.md | 🟢 低（补一句说明） |
| **N-S10** | load_dotenv override 风险 | cloud_relay.py:33 | 🟢 低（条件 override） |
| **N-S11** | _INTERNAL_API_KEY_PATHS 需复核 | 5003 standalone_dispatch_server.py | 🟡 中（需要单独审计 5003） |

---

## 七、跨服务鉴权与直连云端审视

### 7.1 跨服务鉴权流程

| 调用方 | 被调方 | 鉴权方式 | 评估 |
|--------|--------|---------|------|
| 5008 → 5003 | JWT Token | ✅ 强鉴权 |
| 5003 → 5005 | 内部 API Key | ✅ X-API-Key（已审计） |
| 5005 → 云端 5004 | X-API-Key + 明文 HTTP | ⚠️ 鉴权 OK 但传输不安全（N-S1） |
| 桌面端 → 5002 | JWT Token | ✅ 强鉴权 |
| 5002 → 5003 | 内部 API Key | ✅ 鉴权机制存在 |

### 7.2 R-002 规则审视（直连云端 5004）

**位置**：`ARCHITECTURE_v3.6.md:223`

```markdown
- **R-002**：所有**微信相关**云端通信必须通过 5003 调度中心转发到云端 5006，
            禁止直连云端。**例外**：5005 统计表推送直接 POST 云端 5004（智能表格 Webhook），
            属于非微信通信，已知风险（v3.6.8 N-1）。
```

**审计意见**：
- ✅ 文档已明确豁免 5004 直连（5004 是非微信通信）
- ⚠️ 但豁免理由"属于非微信通信"在技术层面不充分——5004 仍然是云端地址（124.223.57.82:5004），技术上与 5006 风险等同
- 建议：R-002 豁免应**只豁免"鉴权链路"**（不走 5003 中转），但**不豁免"传输加密"**——即 5004 也应该走 HTTPS
- 文档可补充：R-002 豁免仅指"5003 中转链路"，传输安全要求同等适用

**评估**：5004 直连在架构上可接受（已豁免），但**安全配置上不可接受**（仍需 HTTPS）

---

## 八、环境变量管理审视

### 8.1 API_KEY 强度

| 变量 | 最小长度要求 | 复杂度要求 | 轮换周期 |
|------|:-----------:|:---------:|:-------:|
| `WECHAT_CLOUD_API_KEY` | ❌ 无 | ❌ 无 | ❌ 无文档 |
| `CLOUD_5004_API_KEY` | ❌ 无 | ❌ 无 | ❌ 无文档 |
| `MYSQL_PASSWORD` | ❌ 无 | ❌ 无 | ❌ 无文档 |
| `JWT_SECRET_KEY` | ❌ 无（项目用 24 字符） | ❌ 无 | ❌ 无文档 |

**问题**：
- 文档未规定任何环境变量的最低安全要求
- 运维人员可能设置弱密码（如 6 位纯数字），导致 API_KEY 可被暴力破解
- 暂缓项 P0-S1/S2/S3 影响 JWT_SECRET_KEY 强度（24 字符不足）

**修复建议**：
- 文档新增"环境变量安全配置规范"章节：
  ```markdown
  ## 环境变量安全要求
  
  | 变量类型 | 最小长度 | 复杂度 | 轮换周期 |
  |---------|:-------:|:-----:|:-------:|
  | API_KEY 类 | 32 字符 | 字母+数字+特殊字符 | 90 天 |
  | 数据库密码 | 16 字符 | 字母+数字+特殊字符 | 90 天 |
  | JWT_SECRET | 64 hex | 强随机 | 90 天 |
  ```

### 8.2 密钥传递路径

| 传递路径 | 是否安全 |
|---------|:-------:|
| `.env` 文件 → `os.getenv()` | ✅ 标准做法 |
| `git` 是否忽略 `.env` | ⚠️ 需确认 `.gitignore` |
| `docker run -e` 传递 | ✅ 安全 |
| 系统环境变量继承 | ✅ 安全 |

**建议**：
- 验证 `.gitignore` 包含 `.env`
- 部署文档强调"绝不能将 .env 提交到 git"

---

## 九、安全设计模式建议

### 9.1 已采用的安全模式

| 模式 | 位置 | 评价 |
|------|------|------|
| Fail-fast 启动检查 | `cloud_relay.py:42-43, 683-684` | ✅ 优秀 |
| 装饰器鉴权 | `@require_api_key` | ✅ 优秀 |
| 幂等性（Lock） | `_stats_locks[table_type]` | ✅ 优秀 |
| 批量重试 | 指数退避 1s→2s→4s | ✅ 良好（但缺总超时） |
| SHA256 数据指纹 | `_compute_hash` | ✅ 良好（数据完整性） |
| 字段 ID 映射 | `FIELD_MAPPING` | ✅ 优秀（防注入） |

### 9.2 缺失的安全模式

| 模式 | 建议 |
|------|------|
| **请求体大小限制** | `app.config['MAX_CONTENT_LENGTH']` |
| **Rate limiting** | Flask-Limiter |
| **HTTPS 强制** | 修改 target_url 协议 |
| **CORS 白名单** | Flask-CORS 显式 origin |
| **审计日志** | 记录所有 API 调用（API_KEY、IP、时间）|
| **错误信息脱敏** | 通用脱敏函数 |
| **输入校验** | table_type 白名单校验（目前仅校验 `isinstance(records, list)`） |
| **CSRF Token** | POST 端点需 CSRF（如果将来支持浏览器调用） |
| **完整 metrics 锁** | 线程安全 |

---

## 十、关联风险（来自 SECURITY_RISK_NOTE.md）

> ⚠️ 以下 3 项暂缓风险**持续生效**（v3.6.6 起即存在），不在本轮新审计范围但需在文档中交叉引用：

| 风险 | 来源 | 状态 |
|------|------|------|
| **R-S1：明文/弱哈希密码** | v3.6.6 SECURITY_RISK_NOTE.md | 🟡 P1 持续（用户决策暂缓） |
| **R-S2：JWT 密钥弱 + base64 降级** | v3.6.6 SECURITY_RISK_NOTE.md | 🟡 P1 持续 |
| **R-S3：测试后门 admin/admin123** | v3.6.6 SECURITY_RISK_NOTE.md | 🟡 P1 持续 |

**建议**：
- `ARCHITECTURE_v3.6.md` 头部应交叉引用 `SECURITY_RISK_NOTE.md`
- 让读者知道 3 大暂缓风险持续生效

---

## 十一、优先修复路线图

```
🔴 立即修复（本次迭代）
  1. N-S1   HTTP → HTTPS                 （cloud_relay.py:687，~0.5h）

🟡 下个迭代（建议打包修复）
  2. N-S2   重试总超时 + records 大小限制   （cloud_relay.py，~2h）
  3. N-S3   MAX_CONTENT_LENGTH            （cloud_relay.py:39，~0.5h）
  4. N-S4   异常脱敏函数                  （cloud_relay.py，~1h）
  5. N-S5   metrics 脱敏                  （cloud_relay.py，~0.5h）
  6. N-S6   metrics 全局锁                （cloud_relay.py，~1h）
  7. N-S7   rate limiting                 （cloud_relay.py，~2h）

🟢 可选清理（顺手修复）
  8. N-S8   删除 _compute_hash 截断       （cloud_relay.py:111，~5min）
  9. N-S9   补充 batch_id 文档说明         （ARCHITECTURE.md，~10min）
 10. N-S10  load_dotenv 条件化 override    （cloud_relay.py:33，~5min）
 11. N-S11  复核 _INTERNAL_API_KEY_PATHS  （单独审计 5003，~2h）
```

---

## 十二、总结

### 12.1 关键发现

1. **🔴 紧急**：5005 → 云端 5004 使用明文 HTTP 传输**含客户名称的生产数据**（N-S1）——这是本轮最严重发现，需要优先处理

2. **🟡 系统性**：5 个 🟡 中等问题集中在 `/api/stats/*` 端点的**生产数据保护**和**服务可用性**——表明该端点从"内网管理接口"演变为"对外暴露面"后，安全防护未同步升级

3. **🟢 工程债**：4 个 🟢 轻微问题是工程细节（截断冗余、文档缺失），可在日常维护中顺手清理

### 12.2 一句话总结

> **本轮审计的核心发现：5005 接管 9 张表后已修复鉴权（S-1/S-2），但生产数据明文 HTTP 传输（N-S1）和 5 个端点级安全问题（N-S2~N-S7）仍需在 v3.6.9 优先处理。**

### 12.3 与前两轮对比

| 轮次 | 🔴 | 🟡 | 🟢 | 评分 |
|:----:|:--:|:--:|:--:|:----:|
| 第一轮 | 2 | 1 | 2 | 55/100 |
| 第二轮 | 0 | 1 | 0 | 70/100 |
| **第三轮** | **1** | **6** | **4** | **78/100** |

> 第三轮评分上升但中等问题增加——**这是好事**。因为：
> - 前两轮关注"大颗粒度"问题（鉴权、fail-fast）
> - 本轮深入代码细节，发现更多**精细化问题**（传输加密、metrics 脱敏、线程安全）
> - 这些问题在第一轮时还被更严重的问题"覆盖"

### 12.4 签字

| 角色 | 签字 | 备注 |
|------|------|------|
| 小钰（安全）| ✅ | 第三轮安全审计完成 |
| 运维 | ⏳ | 等待 N-S1 HTTPS 修复决策 |
| 用户 | ⏳ | 等待 P0-S1/S2/S3 暂缓项最终决策 |

---

**审计员**：小钰（安全）
**报告版本**：v1.0
**最后更新**：2026-06-24
**下次更新**：v3.6.9 N-S1 修复后
