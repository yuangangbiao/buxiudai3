# DESIGN - v3.6.8 N-1 任务：5005 接管 9 张报表定时任务

> **版本**: v1.0
> **任务编号**: N-1
> **创建时间**: 2026-06-24
> **负责人**: AI 团队

---

## 1. ALIGNMENT（上下文对齐）

### 1.1 问题背景

v3.6.5 将 9 张统计表 APScheduler 定时任务注册在 `standalone_dispatch_server.py:5003` 中，但这个设计有架构缺陷：

**现状（3跳，职责混乱）：**
```
standalone_dispatch_server.py:5003  ← APScheduler 在这里
  → smart_sheet_exporter.py         ← 导出逻辑在这里
    → smart_sheet_client.py         ← 推送客户端在这里（调 localhost:5005）
      → cloud_relay.py:5005         ← 收到后转发到云端
        → cloud_group_bot_service:5004  → 微信智能表格
```

**问题：**
1. 5003 是"调度中心"，不应该管统计表导出
2. 定时器在 5003，导出逻辑在 `stats_smart_sheet/` 模块，推送在 5005——三个地方各管一段
3. `stats_smart_sheet/` 目录有 12 个文件，职责分散

**理想（2跳，职责单一）：**
```
cloud_relay.py:5005
  ├─ APScheduler 定时任务（在这里）
  ├─ 9 张表导出函数（直接调 db_queries）
  └─ 推送逻辑（直接 POST 到云端 5004）
      → 微信智能表格
```

### 1.2 改造目标

| # | 目标 |
|---|------|
| G-1 | 5005 成为"统计报表+智能表格推送"唯一服务 |
| G-2 | APScheduler + 导出 + 推送全部在 5005 内部，5003 不感知统计表 |
| G-3 | 减少服务间 HTTP 跳转，链路从 3 跳→2 跳 |
| G-4 | stats_smart_sheet/ 目录清空或删除 |

---

## 2. CONSENSUS（任务共识）

### 2.1 现有模块清单

| # | 文件 | 职责 | 迁移方向 |
|---|------|------|---------|
| 1 | `stats_smart_sheet/mysql_config.py` | 三库连接池（steel_belt / container_center / inventory） | 移入 cloud_relay.py |
| 2 | `stats_smart_sheet/db_queries.py` | 9 张表 SQL 查询 | 移入 cloud_relay.py |
| 3 | `stats_smart_sheet/config.py` | cron 表达式 / 字段映射 / 阈值配置 | 移入 cloud_relay.py（内嵌） |
| 4 | `stats_smart_sheet/smart_sheet_client.py` | 推送客户端（POST 到 localhost:5005） | 合并入 cloud_relay.py 推送逻辑 |
| 5 | `stats_smart_sheet/smart_sheet_exporter.py` | 导出入口 + APScheduler 注册 | 导出函数移入 cloud_relay.py；APScheduler 改在 cloud_relay.py 启动 |
| 6 | `standalone_dispatch_server.py` | 启动时 `register_scheduler(_stats_scheduler)` | 删除 APScheduler 注册代码 |

### 2.2 推送链路分析

现有推送有两层：
1. `smart_sheet_client.push_with_retry()` → HTTP POST → `cloud_relay.py:5005/api/stats/push`
2. `cloud_relay.stats_push()` → HTTP POST → `cloud_group_bot_service:5004/api/smartsheet/write`

改造后合并为一层：`cloud_relay.py` 内部直接调用 `cloud_group_bot_service:5004`

```
改造后 cloud_relay.py 内部 push_flow():
  db_queries 查询数据
    → field_id 映射（内嵌逻辑）
      → 幂等 batch_id 生成
        → 直接 POST 到 CLOUD_5004_HOST:5004/api/smartsheet/write
```

### 2.3 环境变量依赖

| 环境变量 | 来源 | 用途 | 迁移后 |
|---------|------|------|-------|
| `MYSQL_HOST/PORT/USER/PASSWORD` | .env | container_center 库连接 | cloud_relay.py 直接用 |
| `CONTAINER_MYSQL_*` | .env | container_center 库连接 | cloud_relay.py 直接用 |
| `INVENTORY_MYSQL_*` | .env | inventory 库连接 | cloud_relay.py 直接用 |
| `CLOUD_5004_HOST/PORT/API_KEY` | .env | 云端 5004 转发目标 | cloud_relay.py 直接用 |
| `STATS_API_KEY` | .env | stats push 鉴权 | 保留（外部手动触发用） |

---

## 3. ARCHITECT（方案设计）

### 3.1 cloud_relay.py 改造后的结构

```
cloud_relay.py:5005（改造后）
  ├─ [新增] APScheduler 定时任务（后台启动）
  │     └─ 9 个 cron job → export_table(table_type)
  ├─ [新增] /api/stats/trigger/<table_type> 端点（手动触发）
  ├─ [新增] /api/stats/status 端点（metrics 状态）
  ├─ [保留] /api/stats/push 端点（外部推送，但内部不再调用它）
  ├─ [保留] /api/health 端点
  ├─ [新增] stats 模块（内嵌，无独立文件）
  │     ├─ 9 个 export_* 函数（从 smart_sheet_exporter.py 迁入）
  │     ├─ export_table() 统一入口（带并发锁）
  │     ├─ push_to_cloud() 直接推送云端（从 smart_sheet_client.py 迁入）
  │     ├─ compute_hash() / map_to_field_ids()（保留）
  │     └─ SCHEDULE_CONFIG / FIELD_MAPPING（从 config.py 迁入）
  └─ [新增] db_queries 模块（从 stats_smart_sheet/db_queries.py 迁入）
        └─ 9 个 query_* 函数（SQL 查询，保持原样）
```

### 3.2 新增端点

#### `POST /api/stats/trigger/<table_type>`
手动触发单张表导出（运维用）

```python
@app.route('/api/stats/trigger/<table_type>', methods=['POST'])
def trigger_export(table_type):
    """手动触发单张统计表导出"""
    # 幂等：同一 table_type 不能并发
    with _stats_locks.get(table_type, threading.Lock()):
        result = _export_table(table_type)
    return jsonify(result)
```

#### `GET /api/stats/status`
查看定时任务 metrics

```python
@app.route('/api/stats/status', methods=['GET'])
def stats_status():
    """统计表导出状态"""
    return jsonify({
        'code': 0,
        'scheduler': 'running' if _stats_scheduler and _stats_scheduler.running else 'stopped',
        'metrics': _stats_metrics,
        'jobs': [
            {'table': j.id.replace('stats_', ''), 'next_run': j.next_run_time.isoformat() if j.next_run_time else None}
            for j in _stats_scheduler.get_jobs()
        ] if _stats_scheduler and _stats_scheduler.running else []
    })
```

### 3.3 推送函数改造

原有 `smart_sheet_client.push_with_retry()` 是 HTTP POST 到 localhost:5005/self，改造后改为直接内部调用：

```python
def _push_to_cloud(table_type: str, records: List[Dict],
                    period_key: str = '') -> Dict[str, Any]:
    """直接推送数据到云端 5004（不再经过 localhost:5005 HTTP 中转）"""
    if not records:
        return {'code': 0, 'message': '无数据', 'batch_id': '', 'success_count': 0}

    batch_id = str(uuid.uuid4())
    record_hash = _compute_hash(records)
    payload = {
        'table_type': table_type,
        'period_key': period_key or '',
        'batch_id': batch_id,
        'record_hash': record_hash,
        'records': _map_to_field_ids(table_type, records),
    }
    forward_url = f'http://{CLOUD_5004_HOST}:{CLOUD_5004_PORT}/api/smartsheet/write'
    forward_headers = {
        'Content-Type': 'application/json',
        'X-API-Key': CLOUD_5004_API_KEY,
    }

    # 重试逻辑（指数退避）
    for attempt in range(max_retries):
        try:
            resp = requests.post(forward_url, json=payload,
                                 headers=forward_headers, timeout=60)
            result = resp.json()
            if result.get('code') == 0:
                logger.info(f'[stats/push] {table_type} 推送成功')
                return {'code': 0, 'message': result.get('message'),
                        'batch_id': batch_id, 'success_count': len(records)}
        except Exception as e:
            logger.warning(f'[stats/push] {table_type} 尝试 {attempt+1} 失败: {e}')
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
    return {'code': -1, 'message': '推送失败', 'batch_id': batch_id, 'success_count': 0}
```

### 3.4 9 张表 cron 表达式（从 config.py 迁入）

```python
_SCHEDULE_CONFIG = {
    'production_daily_report':    {'cron': '0 18 * * *',    'enabled': True},
    'production_monthly_report':  {'cron': '0 9 1 * *',     'enabled': True},
    'workshop_capacity':          {'cron': '0 18 * * *',    'enabled': True},
    'workorder_progress':         {'cron': '0 */4 * * *',   'enabled': True},
    'substep_report':             {'cron': '*/30 * * * *',  'enabled': True},
    'inventory_weekly_report':     {'cron': '0 9 * * 1',     'enabled': True},
    'inventory_monthly_summary':   {'cron': '0 9 1 * *',     'enabled': True},
    'inventory_alert':            {'cron': '0 9 * * *',     'enabled': True},
    'inventory_slow_moving':      {'cron': '0 9 * * 1',     'enabled': True},
}
```

### 3.5 APScheduler 启动（cloud_relay.py 的 if __name__ == '__main__' 块中）

```python
if __name__ == '__main__':
    # 原有启动...
    serve(app, host=host, port=port, threads=..., connection_limit=...)
```

改为：

```python
# cloud_relay.py 内部 APScheduler（独立线程）
_stats_scheduler = BackgroundScheduler(
    timezone='Asia/Shanghai',
    job_defaults={'coalesce': True, 'max_instances': 1}
)
# 注册 9 个定时任务
for table_type, cfg in _SCHEDULE_CONFIG.items():
    if not cfg.get('enabled', True):
        continue
    parts = cfg['cron'].split()
    trigger = CronTrigger(minute=parts[0], hour=parts[1],
                          day=parts[2], month=parts[3], day_of_week=parts[4])
    _stats_scheduler.add_job(
        _export_table, trigger, args=[table_type],
        id=f'stats_{table_type}', replace_existing=True
    )
_stats_scheduler.start()
logger.info('[v3.6.8] 9 张统计表定时任务已在 5005 启动')

# 原有 Flask serve...
serve(app, host=host, port=port, ...)
```

### 3.6 5003 侧清理

从 `standalone_dispatch_server.py` 中删除以下代码：

```python
# 删除：stats_smart_sheet APScheduler 注册（约 15 行）
# [v3.6.5 Phase-2] 注册 9 张统计表 APScheduler 定时任务
_stats_scheduler = None
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    _stats_scheduler = BackgroundScheduler(...)
    from stats_smart_sheet.smart_sheet_exporter import register_scheduler
    register_scheduler(_stats_scheduler)
    _stats_scheduler.start()
    logger.info('[v3.6.5] 统计表定时任务已注册并启动 (9张表 APScheduler)')
except ImportError:
    ...
except Exception as e:
    ...
```

### 3.7 stats_smart_sheet/ 目录处理

| 文件 | 处理方式 |
|------|---------|
| `mysql_config.py` | 迁移入 cloud_relay.py |
| `db_queries.py` | 迁移入 cloud_relay.py |
| `config.py` | 迁移入 cloud_relay.py |
| `smart_sheet_client.py` | 迁移入 cloud_relay.py |
| `smart_sheet_exporter.py` | 迁移入 cloud_relay.py |
| `__init__.py` | 删除 |
| `__init__.py.orig` | 删除 |
| 其他 `.py` 文件 | 检查后删除 |

---

## 4. ATOMIZE（原子任务）

| # | 原子任务 | 估算 | 依赖 |
|---|---------|------|------|
| A-1 | 新增 APScheduler + 9 表定时器启动逻辑到 cloud_relay.py | 1h | 无 |
| A-2 | 迁移 9 个 export_* 函数到 cloud_relay.py | 1h | A-1 |
| A-3 | 迁移 db_queries.py（9 个 query_* 函数）到 cloud_relay.py | 1h | A-1 |
| A-4 | 迁移 config.py（SCHEDULE_CONFIG / FIELD_MAPPING）到 cloud_relay.py | 0.5h | A-1 |
| A-5 | 迁移并合并 push_with_retry 为 _push_to_cloud（直接 POST 云端） | 1h | A-2/A-3 |
| A-6 | 新增 /api/stats/trigger/<table_type> 手动触发端点 | 0.5h | A-2 |
| A-7 | 新增 /api/stats/status metrics 状态端点 | 0.5h | A-1 |
| A-8 | 从 standalone_dispatch_server.py 删除 APScheduler 注册代码 | 0.5h | A-1~A-7 全部完成 |
| A-9 | 更新 cloud_relay.py 启动日志（标注 APScheduler 状态） | 0.25h | A-1 |
| A-10 | 更新 ARCHITECTURE_v3.6.md 架构文档（5005 职责说明） | 0.5h | A-8 |
| A-11 | 语法检查 + 简单功能测试 | 0.75h | A-1~A-9 |
| **合计** | **11 个原子任务** | **~8h** | |

---

## 5. TEST（测试计划）

### 5.1 边界矩阵

| # | 测试场景 | 预期结果 |
|---|---------|---------|
| T-1 | 启动 cloud_relay.py，APScheduler 是否正常运行 | 9 个 job 在队列中 |
| T-2 | `POST /api/stats/trigger/production_daily_report` | 返回导出结果，code=0 |
| T-3 | `GET /api/stats/status` | 返回 scheduler 状态 + 9 个 job 列表 |
| T-4 | 两端点同时触发同一 table_type | 第二端被并发锁阻塞（幂等） |
| T-5 | 云端 5004 不可达时推送失败 | 返回 code=-1，有错误日志 |
| T-6 | 无数据时导出（如节假日） | 返回 code=0，message='无数据' |
| T-7 | 9 张表全部手动触发一遍 | 全部返回 code=0 或 code=-1（按实际数据） |

---

## 6. 风险与注意事项

| # | 风险 | 缓解 |
|---|------|------|
| R-1 | db_queries.py 迁移后 MySQL 连接失败 | cloud_relay.py 启动时会加载 .env，mysql_config 要求强环境变量 |
| R-2 | 5003 和 5005 同时运行导致定时任务重复执行 | A-8 清理后 5003 不再注册 APScheduler |
| R-3 | 字段映射 FIELD_MAPPING 为空（未配置） | push 时跳过映射，保留原 key |
| R-4 | cloud_relay.py 作为后台服务长期运行，APScheduler 内存泄漏 | APScheduler 默认用内存调度，无持久化（与原 5003 设计一致） |

---

**更新人**：AI 团队
**版本**: v1.0
