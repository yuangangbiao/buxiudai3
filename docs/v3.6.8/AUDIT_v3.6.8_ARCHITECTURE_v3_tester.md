# 第三轮审计报告（测试工程师视角） - ARCHITECTURE_v3.6.md v3.6.8

> **审计范围**：ARCHITECTURE_v3.6.md（v3.6.8，N-1 改造后状态）
> **审计视角**：资深测试工程师（关注测试覆盖度、边界条件、可测试性）
> **审计日期**：2026-06-24
> **前置状态**：第一轮 6 项已修复（25→19）+ 第二轮 8 项新增（共 27 项），其中 S-1/S-2/D-1/T-1/T-2 多数已闭环，本轮验证修复 + 找新盲点

---

## 一、总结

| 维度 | 评分 | 关键问题数 |
|------|:----:|:---------:|
| **测试覆盖度** | 25/100 | 9 |
| **边界条件覆盖** | 30/100 | 6 |
| **可测试性（接口设计）** | 70/100 | 3 |
| **失败处理可测试性** | 50/100 | 4 |

> **核心结论**：v3.6.8 N-1 改造引入了 873 行新代码（cloud_relay.py），但**零单元测试、零集成测试、零端到端测试**。所有 4 个 HTTP 端点（`/api/stats/push`、`/api/stats/trigger/<table_type>`、`/api/stats/status`、`/api/health`）均无测试覆盖。这是最严重的问题。

---

## 二、已修复项确认（第一轮/第二轮 6 项）

| # | 修复项 | 状态 | 证据 |
|---|--------|:----:|------|
| S-1 | CLOUD_5004_HOST 空值 fail-fast | ✅ 已修复 | cloud_relay.py:683-684 `raise RuntimeError(...)` |
| S-2 | API_KEY 强制要求 + 全端点鉴权 | ✅ 已修复 | cloud_relay.py:41-43 fail-fast + line 815/833/844 全部 `@require_api_key` |
| D-1 | CASE WHEN 14点边界重叠 | ✅ 已修复 | 14 已从早班移除（6-13 早班 / 14-22 中班）|
| T-1 | 统计表推送失败降级文档 | ✅ 已修复 | 文档行 116-126 新增"统计表推送失败处理策略"段 |
| T-2 | 9 表 Job 独立 metrics（by_table）| ✅ 已修复 | cloud_relay.py:198-205 `by_table` 字典已实现；端点 844-862 暴露 metrics |
| T-3 | /api/stats/trigger 幂等文档 | ✅ 已修复 | 文档行 112 "幂等：同一 table_type 不能并发执行（threading.Lock）" |
| N-8 | APScheduler graceful shutdown | ✅ 已修复 | cloud_relay.py:809 `wait=True, cancel_running=False` |

---

## 三、仍存在的测试盲点（第二轮遗留未完全闭环）

### 🔴 盲点 B-1：cloud_relay.py 全部 4 个端点零测试覆盖（🔴 高）

**位置**：tests/ 目录 vs cloud_relay.py 端点

**证据**：
- `grep -rn "cloud_relay" tests/` → **0 命中**
- `grep -rn "/api/stats/push" tests/` → **0 命中**
- `grep -rn "/api/stats/trigger" tests/` → **0 命中**
- `grep -rn "/api/stats/status" tests/` → **0 命中**
- `grep -rn "/api/health" tests/`（5005 health，非 5008）→ **0 命中**

**风险**：
- 873 行新代码（cloud_relay.py v3.6.8 N-1）**完全无测试覆盖**
- `TODO_v3.6.8.md` 中明确提到 `P0-T2: 9 统计表单测 ~6h` 标注为 🟡 P1，**至今未启动**
- 一旦 _push_to_cloud / _export_table / _stats_metrics 行为变更（已变更过 2 次），无任何回归网

**修复建议**（按 6A 工作流）：
```python
# tests/unit/test_cloud_relay.py 应包含：
# 1. /api/stats/push - 鉴权（无/正确/错误 key）、参数（缺 table_type/records 非数组）、空 records 短路、push 成功/失败重试
# 2. /api/stats/trigger/<table_type> - 鉴权、未知 table_type 404、并发幂等（threading.Lock 验证）、metrics 计数 +1
# 3. /api/stats/status - 鉴权、jobs 列表（无 scheduler / 运行时）、metrics 暴露
# 4. /api/health - 无鉴权可访问、scheduler 状态字段
# 5. _push_to_cloud - 指数退避验证（1s→2s→4s，但实际是 2s→4s→8s，见 B-3）、最大重试、空 records
# 6. _export_table - 锁释放（异常时）、metrics 异常分支、未知表类型
```

---

### 🔴 盲点 B-2：_stats_metrics 全局字典无线程安全（🔴 高）

**位置**：cloud_relay.py:198-205

```python
_stats_metrics = {
    'by_table': {t: {'success': 0, 'failed': 0, 'last_time': ''} for t in _SCHEDULE_CONFIG},
    'total_push': 0,
    'success_push': 0,
    'failed_push': 0,
    'last_push_time': '',
    'last_result': {},
}
```

**问题**：
1. `_stats_locks[table_type]` 只保护**同一 table_type** 的并发
2. 不同 table_type 之间的 metrics 修改（如 `total_push += 1`、`success_push += 1`）**完全无锁**
3. `last_result` 字典赋值不是原子操作（多步写）

**测试场景**：
- 并发触发 9 个不同 table_type（各 100 次）→ `total_push` 应为 900，但可能因 race condition 漏计数
- `last_result` 字段可能被部分写入

**修复建议**：
```python
# 加 metrics 专用锁
_stats_metrics_lock = threading.Lock()

def _increment_metrics(table_type, success):
    with _stats_metrics_lock:
        _stats_metrics['total_push'] += 1
        if success:
            _stats_metrics['success_push'] += 1
            _stats_metrics['by_table'][table_type]['success'] += 1
        else:
            _stats_metrics['failed_push'] += 1
            _stats_metrics['by_table'][table_type]['failed'] += 1
        _stats_metrics['by_table'][table_type]['last_time'] = datetime.now().isoformat()
```

---

### 🔴 盲点 B-3：指数退避实际间隔与文档不符（🔴 高）

**位置**：cloud_relay.py:715-718 vs ARCHITECTURE 行 122

**文档说**：
> 指数退避重试 3 次（1s→2s→4s），3 次失败后返回 code=-1

**实际代码**：
```python
for attempt in range(max_retries):  # max_retries=3, attempt=0,1,2
    ...
    if attempt < max_retries - 1:  # attempt < 2 时等待
        wait = 2 ** (attempt + 1)  # attempt=0: 2s, attempt=1: 4s
        time.sleep(wait)
```

**实际退避序列**：`2s → 4s`（共 6s），**不是 1s→2s→4s（7s）**

**问题**：
- 文档与代码不一致，误导运维
- 实际等待时间比文档少 1s（首次重试前少 1 秒）

**测试场景**：
- 启动 mock 服务（5004）返回 500
- 调用 `/api/stats/push` 计时
- 验证实际退避间隔 ≈ 2s + 4s = 6s（不是 7s）

---

### 🔴 盲点 B-4：_stats_locks 无超时，永久阻塞（🟡 中）

**位置**：cloud_relay.py:731

```python
with _stats_locks[table_type]:
    start = time.time()
    ...
```

**问题**：
- `threading.Lock()` 不带 timeout，永久等待
- 如果第一次触发 hang 住（如 MySQL 慢查询），第二次触发会**永久阻塞**直到 Flask 客户端 timeout
- 文档行 112 只说"同一 table_type 不能并发执行"，**未说明是否会永久阻塞**

**测试场景**：
- Mock _export_table 内部 sleep 60s
- 同时发起两个 trigger 请求
- 第二个请求 5s 后被 Flask 客户端 timeout 取消，但服务端**仍然在等锁**
- 这会导致 worker 线程泄漏

**修复建议**：
- 使用 `lock.acquire(timeout=N)` 并 fallback 到"上一批未完成"状态码
- 或文档明确说明"不保证响应时间上限"

---

### 🟡 盲点 B-5：/api/health 不检查 MySQL 连接池（🟡 中）

**位置**：cloud_relay.py:865-873

```python
@app.route('/api/health')
def health():
    return jsonify({
        'code': 0,
        'service': 'cloud-relay-stats',
        'role': 'stats-only',
        'time': datetime.now().isoformat(),
        'scheduler': 'running' if (_stats_scheduler and _stats_scheduler.running) else 'stopped',
    })
```

**问题**：
- 端点仅检查 Flask 进程 + scheduler 状态
- 不验证 MySQL 连接池可用性
- 不验证 CLOUD_5004_HOST 可达性
- 第二轮审计 T-5 提到此问题，**已部分修复**（`_start_scheduler()` 有预检）但 `/api/health` 端点**未复用**预检结果

**测试场景**：
- 启动 5005 服务后立刻断网
- `/api/health` 返回 200
- 但下一次 cron 触发必失败

**修复建议**：
```python
@app.route('/api/health')
def health():
    mysql_status = {}
    for cfg_key in ['container_center', 'inventory']:
        try:
            conn = _get_conn(cfg_key)
            conn.ping(reconnect=True)
            conn.close()
            mysql_status[cfg_key] = 'ok'
        except Exception as e:
            mysql_status[cfg_key] = f'error: {e}'
    return jsonify({
        'code': 0,
        'service': 'cloud-relay-stats',
        'role': 'stats-only',
        'time': datetime.now().isoformat(),
        'scheduler': 'running' if (_stats_scheduler and _stats_scheduler.running) else 'stopped',
        'mysql': mysql_status,
    })
```

---

### 🟡 盲点 B-6：_export_table 异常路径 metrics 不完整（🟡 中）

**位置**：cloud_relay.py:752-757

```python
except Exception as e:
    logger.exception(f"[{table_type}] 导出异常: {e}")
    _stats_metrics['failed_push'] += 1
    _stats_metrics['by_table'][table_type]['failed'] += 1
    _stats_metrics['by_table'][table_type]['last_time'] = datetime.now().isoformat()
    return {'code': -1, 'message': f'异常: {e}'}
```

**问题**：
- 异常路径**未更新** `last_push_time` 和 `last_result`（成功路径行 746-748 更新了）
- 导致监控看 `last_push_time` 还停留在"上次成功"的时间，运维误以为"当前任务还在跑"

**测试场景**：
- Mock MySQL 查询抛 `pymysql.err.OperationalError`
- 调用 `_export_table('production_daily_report')`
- 验证 `last_push_time` 仍为之前成功时间，**未更新**

---

### 🟡 盲点 B-7：空 records 短路时 metrics 不更新（🟡 中）

**位置**：cloud_relay.py:669-670 + 736-748

```python
def _push_to_cloud(table_type, records, period_key=''):
    if not records:
        return {'code': 0, 'message': '无数据', 'batch_id': '', 'success_count': 0}
```

**问题**：
- `_push_to_cloud` 返回 `code=0` 视为"成功"
- 但 `_export_table` 仍然将 `success_push += 1`，`by_table[table_type]['success'] += 1`
- 监控看 success 计数会增加，但实际**没有数据被推送**到云端
- 业务方"今天有几条推送成功"统计会失真

**测试场景**：
- 配置空数据库（某 9 张表均无数据）
- 触发 cron 9 次
- `metrics.success_push` = 9，但云端 5004 未收到任何 batch_id

**修复建议**：
- 区分 `success` 与 `no_data` 两种状态
- 或在 _export_table 中检查 push_result.get('batch_id') 是否为空

---

### 🟡 盲点 B-8：9 表 cron 时间表缺测试方法（🟡 中）

**位置**：ARCHITECTURE 行 95-105

**问题**：
- 9 张表的 cron 时间表已补充（第二轮审计 T-4 已修复）
- 但**没有描述**如何测试定时任务行为
- 缺少以下测试维度：
  1. 如何验证 cron 表达式被正确解析（`CronTrigger` 实例化）
  2. 如何模拟"今天 18:00"以触发 production_daily_report
  3. 如何验证跨时区（`Asia/Shanghai`）的正确性
  4. 如何测试 DST 切换 / 闰秒等边界

**修复建议**：
```markdown
#### 9 张表 cron 测试方法（v3.6.8 补充）

**单元测试**：
```python
def test_cron_trigger_parsing():
    for table_type, cfg in _SCHEDULE_CONFIG.items():
        parts = cfg['cron'].split()
        assert len(parts) == 5
        trigger = CronTrigger(minute=parts[0], hour=parts[1], ...)
        # 验证可解析
```

**集成测试**：
- `freeze_time("2026-06-24 17:59:30")` → 验证 18:00:00 触发
- 验证 `next_run_time` 字段
- 跨时区：mock `pytz.timezone('Asia/Shanghai')` 验证
```

---

### 🔵 盲点 B-9：_map_to_field_ids 静默保留未映射字段（🔵 低）

**位置**：cloud_relay.py:654-664

```python
def _map_to_field_ids(table_type, records):
    mapping = FIELD_MAPPING.get(table_type, {})
    if not mapping:
        return records
    mapped = []
    for r in records:
        new_r = {}
        for k, v in r.items():
            new_r[mapping.get(k, k)] = v  # ❌ 静默保留
        mapped.append(new_r)
    return mapped
```

**问题**：
- 字段不在 mapping 中时，`mapping.get(k, k)` 返回原 key
- 不报警告/错误
- 数据库 schema 变更后，新字段会被推送到云端但云端可能不认识
- 调试困难

**测试场景**：
- 9 张表的所有字段都已在 FIELD_MAPPING 中吗？（手工核对 vs 实际）
- 新增字段时（数据库 schema 变化）能否被发现

---

### 🔵 盲点 B-10：API_KEY 失败响应无统一格式（🔵 低）

**位置**：cloud_relay.py:50-53

```python
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get('X-API-Key', '')
        if not key or key != API_KEY:
            return jsonify({'code': 403, 'message': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated
```

**问题**：
- 错误响应格式 `{'code': 403, 'message': 'Forbidden'}` 与项目统一格式 `{'code': int, 'message': str, 'data': ...}` 不一致
- 缺少 `data` 字段
- 与 standalone_dispatch_server.py 的鉴权失败响应可能不同

**测试场景**：
- 调用 `/api/stats/push` 不带 X-API-Key
- 验证响应格式是否符合项目 R-090 规范

---

## 四、新发现的测试问题（本轮新增）

### 🔴 新问题 N-T1：未覆盖性能测试（🔴 高）

**位置**：ARCHITECTURE 行 95-105 + 116-126

**问题**：
- 9 张表 cron 频率从 `*/30`（每 30 分钟）到 `0 9 1 * *`（每月一次）
- 高频表（`*/30 * * * *`）每天 48 次触发
- 没有性能基准测试：
  - 单次 _export_table 耗时（典型 5s？30s？）
  - 5004 不可达时 3 次重试总耗时（6s + forward_timeout × 3）
  - 100 并发 trigger 时的 P99 响应时间
  - MySQL 连接池（maxconnections=10）是否足够

**修复建议**：
- 添加 `tests/performance/test_cloud_relay_perf.py`
- 基准：单次 push < 5s，3 次重试总耗时 < 90s
- 负载：100 并发 trigger 同一 table_type → 1 个成功 + 99 个 503（锁超时）

---

### 🔴 新问题 N-T2：/api/health 端点存在信息泄露（🔴 中）

**位置**：cloud_relay.py:865-873

**问题**：
- `/api/health` 无鉴权（可接受，业界惯例）
- 但泄露了 `scheduler` 状态（running/stopped）和 `time`
- 攻击者可通过持续探测 `/api/health` 推断服务运行规律
- 建议：仅返回 `code: 0`（存活），详细信息需鉴权端点 `/api/stats/status` 才有

**测试场景**：
- 不带 API key 访问 `/api/health` → 200
- 验证响应是否泄露内部状态

---

### 🟡 新问题 N-T3：缺少故障注入测试（🟡 中）

**位置**：ARCHITECTURE 整体

**问题**：
- 失败处理策略（行 116-126）描述了"云端 5004 不可达"、"幂等保证"等场景
- 但没有故障注入测试：
  - 模拟 5004 返回 500 → 验证 3 次重试 + 最终失败 metrics
  - 模拟 5004 返回 200 但 `code != 0` → 验证同样重试
  - 模拟网络断开（连接拒绝）→ 验证异常处理
  - 模拟 MySQL 慢查询（30s+）→ 验证锁阻塞行为

**修复建议**：
- 使用 `responses` 或 `httpretty` mock 5004 响应
- 编写 `test_push_to_cloud_retry_scenarios.py`

---

### 🟡 新问题 N-T4：行号引用陈旧风险（🟡 中）

**位置**：ARCHITECTURE 行 77, 80, 82, 88, 90, 91 等

**问题**：
- 文档大量引用 cloud_relay.py 行号（如 "行 700-870"）
- 但 cloud_relay.py 后续会被修改（已修改过 2 次）
- 行号漂移会导致读者找不到代码
- 测试工程师按文档指引检查代码时容易困惑

**测试场景**：
- 验证文档中所有行号引用是否准确（与当前代码 grep 对比）

---

## 五、9 张表 cron 时间表测试覆盖

| 序号 | 业务流 | 中文名称 | table_type | 频率 | 端点测试 | _export_table 单元测试 |
|:----:|--------|---------|-----------|------|:--------:|:-------------------:|
| 1 | 生产 | 生产日报 | production_daily_report | 每天 18:00 | ❌ | ❌ |
| 2 | 生产 | 生产月报 | production_monthly_report | 每月 1 日 09:00 | ❌ | ❌ |
| 3 | 生产 | 车间产能分析 | workshop_capacity | 每天 18:00 | ❌ | ❌ |
| 4 | 生产 | 工单进度跟踪 | workorder_progress | 每 4 小时 | ❌ | ❌ |
| 5 | 工序 | 工序报工汇总 | substep_report | 每 30 分钟 | ❌ | ❌ |
| 6 | 库存 | 库存周报 | inventory_weekly_report | 每周一 09:00 | ❌ | ❌ |
| 7 | 库存 | 物料收发存汇总 | inventory_monthly_summary | 每月 1 日 09:00 | ❌ | ❌ |
| 8 | 库存 | 库存预警 | inventory_alert | 每天 09:00 | ❌ | ❌ |
| 9 | 库存 | 呆滞料分析 | inventory_slow_moving | 每周一 09:00 | ❌ | ❌ |

**结论**：9/9 张表均无测试覆盖（D-2 工单进度跟踪的 JSON 函数也无单测）

---

## 六、4 个端点测试覆盖矩阵

| 端点 | 方法 | 鉴权 | 鉴权测试 | 正常路径 | 异常路径 | 边界条件 | 并发测试 | 性能测试 |
|------|:----:|:----:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|
| `/api/stats/push` | POST | X-API-Key | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `/api/stats/trigger/<table_type>` | POST | X-API-Key | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `/api/stats/status` | GET | X-API-Key | ❌ | ❌ | — | ❌ | — | ❌ |
| `/api/health` | GET | 无 | — | ❌ | — | ❌ | — | ❌ |

**覆盖率**：**0%**（所有端点所有维度均无测试）

---

## 七、_stats_metrics 监控完整性评估

| 字段 | 类型 | 文档说明 | 实际暴露 | 测试覆盖 |
|------|------|---------|:--------:|:--------:|
| `total_push` | int | ✅ | ✅ (行 861) | ❌ |
| `success_push` | int | ✅ | ✅ | ❌ |
| `failed_push` | int | ✅ | ✅ | ❌ |
| `last_push_time` | str | ✅ | ✅ | ❌ |
| `last_result` | dict | ✅ | ✅ | ❌ |
| `by_table.<table>.success` | int | ✅ (T-2 修复) | ✅ (行 861) | ❌ |
| `by_table.<table>.failed` | int | ✅ (T-2 修复) | ✅ | ❌ |
| `by_table.<table>.last_time` | str | ✅ (T-2 修复) | ✅ | ❌ |
| `by_table.<table>.last_elapsed` | float | ❌ 文档未提 | ❌ 未记录 | ❌ |
| `by_table.<table>.last_error` | str | ❌ 文档未提 | ❌ 未记录 | ❌ |
| `by_table.<table>.last_batch_id` | str | ❌ 文档未提 | ❌ 未记录 | ❌ |

**缺失监控字段**：
- `last_elapsed`（单次耗时）— 当前只在日志中，无 metrics
- `last_error`（最后一次错误信息）— 失败时无法定位
- `last_batch_id`（最后推送的 batch_id）— 调试时无法关联云端

**建议**（监控完整性 ≥ 90%）：
```python
# _stats_metrics 应记录：
'by_table': {
    t: {
        'success': 0,
        'failed': 0,
        'last_time': '',
        'last_elapsed': 0.0,        # ← 新增
        'last_error': '',            # ← 新增
        'last_batch_id': '',         # ← 新增
    } for t in _SCHEDULE_CONFIG
},
```

---

## 八、_stats_locks 幂等性测试评估

| 维度 | 实现状态 | 测试覆盖 | 风险 |
|------|:--------:|:--------:|------|
| 同一 table_type 锁互斥 | ✅ | ❌ | 🟡 中 - 无并发测试 |
| 不同 table_type 不互斥 | ✅ | ❌ | 🟢 低 - 设计如此 |
| 异常时锁释放 | ✅ (with 语句) | ❌ | 🟡 中 - 异常路径未验证 |
| 锁等待无 timeout | ⚠️ 设计缺陷 | ❌ | 🟡 中 - 永久阻塞 |
| 锁计数清理（无残留）| ✅ | ❌ | 🟢 低 |
| metrics 与锁独立 | ✅ | ❌ | 🔴 高 - B-2 揭示的 race |

**测试场景建议**（使用 threading + concurrent.futures）：
```python
def test_lock_idempotency():
    """并发触发同一 table_type，验证 1 成功 + 1 等待锁"""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(trigger_export, 'production_daily_report')
        time.sleep(0.1)  # 确保 f1 先获得锁
        f2 = ex.submit(trigger_export, 'production_daily_report')
        r1 = f1.result()
        r2 = f2.result()
    # 验证 r1 和 r2 都成功，但 elapsed 累加

def test_lock_release_on_exception():
    """异常后锁必须释放"""
    with mock.patch('cloud_relay._q_production_daily', side_effect=Exception):
        r1 = trigger_export('production_daily_report')  # 失败
    # 第二次应能获得锁
    r2 = trigger_export('production_daily_report')  # 应不阻塞
```

---

## 九、边界条件覆盖评估

| 边界场景 | 文档说明 | 代码实现 | 测试覆盖 | 风险 |
|---------|---------|---------|---------|------|
| 空 records 列表 | ✅ 行 121 | ✅ 行 669-670 | ❌ | 🟡 中 (B-7) |
| 5004 不可达 | ✅ 行 122 | ✅ 行 711-713 | ❌ | 🟡 中 |
| 5004 返回 200 但 code != 0 | ❌ 文档未提 | ✅ 行 701-708 | ❌ | 🟢 低 |
| 5004 返回空 body | ❌ 文档未提 | ✅ 行 700 `resp.content` 检查 | ❌ | 🟢 低 |
| 5004 超时 | ❌ 文档未提 | ✅ `timeout=forward_timeout` | ❌ | 🟢 低 |
| MySQL 连接失败 | ❌ 文档未提 | ⚠️ 预检但不阻止 | ❌ | 🟡 中 |
| MySQL 查询慢查询 | ❌ 文档未提 | ❌ 无超时 | ❌ | 🟡 中 |
| records 含 None 值 | ❌ 文档未提 | ⚠️ 直接传递，云端处理 | ❌ | 🟢 低 |
| records 含非法 JSON 字段 | ❌ 文档未提 | ⚠️ 无序列化检查 | ❌ | 🟢 低 |
| period_key 缺失 | ❌ 文档未提 | ✅ 默认为空 | ❌ | 🟢 低 |
| table_type 大小写 | ❌ 文档未提 | ⚠️ 大小写敏感 | ❌ | 🟢 低 |
| X-API-Key 含特殊字符 | ❌ 文档未提 | ⚠️ 直接 `==` 比较 | ❌ | 🟢 低 |

---

## 十、优先级修复顺序（测试工程师建议）

```
🔴 P0 - 立即修复（数据正确性 + 安全）
  1. B-1  补充 cloud_relay.py 4 端点单元测试            （~6h，按 6A 工作流）
  2. B-2  _stats_metrics 加 metrics_lock                （~1h）
  3. B-3  修正文档"1s→2s→4s"为"2s→4s"                  （~10min）
  4. N-T1 性能基准测试                                  （~4h）

🟡 P1 - 下一迭代
  5. B-4  _stats_locks 加 timeout 或文档明确阻塞行为   （~2h）
  6. B-5  /api/health 增加 MySQL 检查                  （~1h）
  7. B-6  _export_table 异常路径补全 metrics           （~30min）
  8. B-7  空 records 区分 success/no_data              （~1h）
  9. B-8  补充 9 表 cron 测试方法                       （~1h）
  10. N-T2 /api/health 信息泄露评估                     （~30min）
  11. N-T3 故障注入测试                                 （~4h）

🔵 P2 - 下下迭代
  12. B-9  _map_to_field_ids 加 warning                  （~30min）
  13. B-10 API_KEY 失败响应统一格式                    （~15min）
  14. N-T4 行号引用稳定性（建议改用锚点 `cloud_relay.py:_push_to_cloud`）（~2h）
  15. 7 个 _q_* 函数单测                              （~6h）
```

---

## 十一、测试工程师独立意见

> v3.6.8 N-1 改造引入了 873 行新代码（cloud_relay.py），但**所有 4 个 HTTP 端点、9 张表导出函数、5 个工具函数（_push_to_cloud/_export_table/_map_to_field_ids/_compute_hash/_calc_pct）均无单元测试**。这是 v3.6.6-v3.6.8 三个版本累计的测试债务，最严重。
>
> 第二轮审计中我提出"补充 by_table metrics"和"幂等文档"已修复，但**核心问题（测试覆盖）未被触及**。`TODO_v3.6.8.md` 中 `P0-T2: 9 统计表单测 ~6h` 已标记 🟡 P1 但未启动。
>
> **最高优先级**：
> 1. **B-1（零测试覆盖）** — 必须按 6A 工作流启动测试编写，先单元测试再集成测试
> 2. **B-2（_stats_metrics 无锁）** — 真实生产中并发触发 9 张表会触发 race condition，导致监控数据失真
> 3. **B-3（文档与代码不一致）** — 1s→2s→4s vs 2s→4s 的差异会让运维误判故障时长
>
> **测试策略建议**：
> - **单元测试**（`tests/unit/test_cloud_relay.py`）：mock requests.post + mock MySQL，覆盖 4 端点 + 5 函数
> - **集成测试**（`tests/integration/test_stats_push_e2e.py`）：起一个 mock 5004 服务，验证完整推送链路
> - **故障注入测试**（`tests/chaos/test_cloud_relay_chaos.py`）：用 toxiproxy 模拟网络延迟 / 断开
> - **性能测试**（`tests/perf/test_cloud_relay_bench.py`）：locust/vegeta 跑 100 并发 trigger
>
> **风险预警**：
> - 当前 `last_push_time` 和 `last_result` 在异常路径（B-6）下不更新 → 监控告警可能误判
> - `_stats_metrics` 无锁（B-2）→ 9 张表并发触发时计数会丢
> - `_stats_locks` 无 timeout（B-4）→ 慢查询时所有 worker 线程堆积，最终服务 hang
>
> 🔴 **总体评估**：测试覆盖度 25/100（v3.6.8 N-1 之前是 100/100，引入新代码后跌至 25/100）。**必须立即补充测试，否则 v3.6.8 实际上线后没有回归保障**。

---

**报告结束**
