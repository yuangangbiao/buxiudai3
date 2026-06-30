# 审计报告 - ARCHITECTURE_v3.6.md v3.6.8 版本

> **审计范围**：ARCHITECTURE_v3.6.md（v3.6.8 版本，2026-06-24）
> **审计视角**：AI 团队四方审计（架构师 / 测试工程师 / 数据库工程师 / 安全工程师）
> **审计日期**：2026-06-24

---

## 总体评价

| 视角 | 综合评分 | 核心问题数 |
|------|:--------:|:---------:|
| 架构师 | 72/100 | 8 个 |
| 测试工程师 | 65/100 | 6 个 |
| 数据库工程师 | 60/100 | 6 个 |
| 安全工程师 | 55/100 | 5 个 |

---

## 一、架构师视角（评分：72/100）

### 问题 A-1：⚠️ 文档头部自相矛盾（中等）

**位置**：第 3-6 行

```
第3行：> **当前版本：v3.6.8**（2026-06-24 架构重构 - 5005 接管 9 表定时任务）
第4行：> **本版本包含代码修改**，详见"代码修改记录 v3.6.5"段落。
第6行：> **本版本仅修改架构文档，未修改代码**。详见"待修改代码清单 v3.6.5"段落。
```

**问题**：第 4 行说"包含代码修改"，第 6 行说"仅修改文档"，两条互相矛盾。v3.6.8 N-1 确实有代码修改（cloud_relay.py 重写），第 6 行应删除或改为"本版本包含代码修改"。

**修复建议**：删除第 6 行，或将第 4-6 行合并为一条准确描述：
```markdown
> **本版本包含代码修改（v3.6.8 N-1）**：cloud_relay.py 重写 873 行；standalone_dispatch_server.py APScheduler 代码已删除。详见"代码修改记录 v3.6.5 / v3.6.8"段落。
```

---

### 问题 A-2：⚠️ v3.6.5 与 v3.6.5-proposal 修订历史重复（轻微）

**位置**：第 12-13 行

| 版本 | 日期 | 说明 |
|------|------|------|
| v3.6.5-proposal | 2026-06-24 | **5005 合并入 5003 架构提案**...待代码实施。|
| **v3.6.5** | 2026-06-24 | **5005 合并入 5003 完成**（代码实施）：Phase-1... |

**问题**：两条记录日期相同（2026-06-24），内容高度重复（都是描述 5005 合并提案），但一个标注"提案"，一个标注"完成"，容易让读者混淆哪个是最终状态。

**修复建议**：合并为一条，去掉 v3.6.5-proposal：
```markdown
| **v3.6.5** | 2026-06-24 | **5005 合并入 5003 架构提案**（代码实施）：Phase-1 新增 5003 Queue+Stats Push 端点；Phase-2 迁移 APScheduler 定时任务；Phase-3 废弃 5005 端口。详见"代码修改记录 v3.6.5"。|
```

---

### 问题 A-3：🔴 Phase-2 修改记录内容错误（严重）

**位置**：第 78-82 行

```markdown
| `standalone_dispatch_server.py` | 调度中心（v3.6.8 起不再感知统计表）；云端轮询 Poller；Queue + Stats Push 端点 |
| `.env` | 新增 `LOCAL_5005_URL=http://127.0.0.1:5003`（统计推送目标）、`STATS_API_KEY`、`INVENTORY_MYSQL_USER/PASSWORD` |
| `core/_config_infra.py` | 修正 `sync_bridge` 默认 5005→8008；`inventory_api` 默认 5004→5010 |
| `mobile_api_ai/_service_urls.py` | `SYNC_BRIDGE_URL` 默认 5005→8008 |
```

**问题**：Phase-2 的标题是"迁移 APScheduler + 更新调用方"，表格应该描述"代码修改记录"，但表格内容全是"职责描述"而非"修改了什么"。第一条甚至混入了 v3.6.8 的内容（"v3.6.8 起不再感知统计表"）。

**修复建议**：Phase-2 应该描述 v3.6.5 实际代码修改。v3.6.8 的改动需要补充：
```markdown
#### Phase-2: 迁移 APScheduler + 更新调用方（v3.6.5）

| 文件 | 修改内容 |
|------|---------|
| `standalone_dispatch_server.py` | 新增 APScheduler 注册代码（register_scheduler 调用） |
| `smart_sheet_exporter.py` | 新增 register_scheduler() 函数，注册 9 表定时任务 |
| `.env` | 新增 `LOCAL_5005_URL`、`STATS_API_KEY`、`INVENTORY_MYSQL_*` |

#### Phase-2: 5005 接管定时任务（v3.6.8 N-1 补充）

| 文件 | 修改内容 |
|------|---------|
| `standalone_dispatch_server.py` | 删除 APScheduler 注册代码 |
| `cloud_relay.py` | 新增 APScheduler + 9 表导出函数 + MySQL 连接池 + 直接 POST 云端 5004 |
```

---

### 问题 A-4：⚠️ 服务端口定义与 ASCII 图不一致（中等）

**位置**：第 187 行 vs 第 169 行

| 位置 | 大屏服务端口 |
|------|------------|
| 服务端口定义表（第 187 行） | 5007 |
| ASCII 架构图（第 169 行） | 5000 |
| 启动配置（launcher） | 5000 |

**问题**：服务定义表说大屏服务是 5007，但架构图和实际代码都用 5000。5007 在代码里实际是另一个服务（desktop_web 的某个端口），不是大屏。

**修复建议**：将服务端口表第 187 行修正为：
```markdown
| 5000 | 大屏服务 | desktop/views/dashboard/dashboard_server.py | 桌面可视化大屏 |
```

---

### 问题 A-5：⚠️ M-4 状态描述歧义（轻微）

**位置**：第 122 行（废弃列表内）

```
> M-1~M-7 全部被 v3.6.8 N-1 替代执行完成
```

**问题**：M-4 是"更新所有调用 localhost:5005/api/stats/push 的地方改为 5003"，但 v3.6.8 N-1 实际是"把定时任务迁到 5005"，smart_sheet_client.py 里调用 localhost:5005 的代码并没有被改（它在 stats_smart_sheet/ 目录里，没有被迁移也没有被删除）。这意味着 M-4 并未真正"执行完成"，只是被"作废"了。

**修复建议**：改为"M-4 被 v3.6.8 N-1 重新设计（M-4 原任务已无意义）"。

---

### 问题 A-6：⚠️ R-002 约束与代码实现不一致（严重）

**位置**：第 216 行 vs cloud_relay.py:624

```
R-002：所有云端通信必须通过 5003 调度中心转发到云端 5006，禁止直连云端
```

**实际情况**：cloud_relay.py:624 的 `_push_to_cloud()` 直接 `requests.post()` 到 `CLOUD_5004_HOST`，这是一个外部云端地址（不是 5003 → 5006 的路径），违反了 R-002 的字面约束。

**两种可能**：
1. R-002 应改为："所有**微信相关**云端通信必须通过 5003 转发到云端 5006"，智能表格推送作为特例豁免
2. cloud_relay.py 应改为通过 5003 转发到云端 5004（但这会破坏链路设计）

**修复建议**：R-002 增加豁免说明：
```markdown
- **R-002**：所有**微信相关**云端通信必须通过 5003 调度中心转发到云端 5006，禁止直连云端。**例外**：5005 统计表推送直接 POST 云端 5004（智能表格 Webhook），属于非微信通信，已知风险。
```

---

### 问题 A-7：⚠️ 9 类报表数量在多处文档不统一（轻微）

**位置**：第 5-6 行

文档头部描述"5005 接管 9 表定时任务"，但 TODO_v3.6.8.md 里写的是"9 张统计表"，DESIGN_v3.6.8_N1.md 写的是"9 张表"。需要确认是"9 张"还是"9 类"，以及"工序报工"是否算在 9 张里（smart_sheet_exporter.py 有 9 个函数）。

---

### 问题 A-8：ℹ️ Phase-3 状态表行标题重复（轻微）

**位置**：第 84-91 行

Phase-3 表的行标题是"操作"，但表格第一列"操作"和第二列"结果"完全对齐，没有混淆风险。但标题写法不一致——有些用动词（"WeChat Poll/ACK 废弃"），有些用完整句子（"v3.6.7 P0-A5 修复"），建议统一。

---

## 二、测试工程师视角（评分：65/100）

### 问题 T-1：🔴 统计推送失败无降级方案（严重）

**位置**：cloud_relay.py `_push_to_cloud()` + ARCHITECTURE 文档无说明

**问题**：当云端 5004 不可达时，`_push_to_cloud()` 会重试 3 次后返回 `code=-1`，但：
1. 没有写入本地文件作为备份
2. 没有写入 DLQ 队列等待重试
3. APScheduler 不会自动重跑（只在下次 cron 时间触发）
4. 文档中没有描述这个失败场景的降级策略

**修复建议**：在 ARCHITECTURE 中补充 Stats Push 失败处理策略：
```markdown
**统计表推送失败处理**：
- 指数退避重试 3 次（1s→2s→4s）
- 3 次失败后记录错误日志，metrics 记录 failed_push +1
- 不写本地文件（与 DLQ 不同，统计表数据可从 MySQL 重新查询）
- 下一 cron 周期自动重试
- `/api/stats/status` 可查看 `metrics.failed_push` 计数
```

---

### 问题 T-2：⚠️ 9 表 Job 无独立 metrics（中等）

**位置**：cloud_relay.py `_stats_metrics` + `/api/stats/status` 端点

**问题**：`_stats_metrics` 是全局计数器，没有按 table_type 细分。如果 9 张表里有 1 张持续失败，全局 `failed_push` 会增加，但无法从 API 响应中看出是哪张表失败。

**修复建议**：在 `_stats_metrics` 中按 table_type 记录：
```python
_stats_metrics = {
    'by_table': {
        'production_daily_report': {'success': 0, 'failed': 0, 'last_time': ''},
        ...
    },
    'total_push': 0, ...
}
```
`/api/stats/status` 响应中暴露 `metrics.by_table` 供监控使用。

---

### 问题 T-3：⚠️ /api/stats/trigger 无幂等保证文档（中等）

**位置**：cloud_relay.py `trigger_export()` 端点

**问题**：代码中有 `threading.Lock()` 实现幂等，但文档（DESIGN_v3.6.8_N1.md）没有说明"并发触发同一 table_type 时，第二端会被锁阻塞直到第一端完成"，测试人员可能会并发触发导致超时。

**修复建议**：在端点文档中补充：
```
POST /api/stats/trigger/<table_type>
- 幂等：同一 table_type 不能并发执行，第二端被锁阻塞
- 超时：锁等待无超时，依赖客户端 timeout
```

---

### 问题 T-4：⚠️ 9 表 cron 时间无健康检查（轻微）

**位置**：`_SCHEDULE_CONFIG` + `/api/stats/status`

**问题**：9 张表的 cron 时间配置没有在文档中列出完整的时间表（如"生产日报每天 18:00"），运维人员只能读代码才能知道每张表何时运行。`/api/stats/status` 返回 `next_run` 但没有中文名。

**修复建议**：在 ARCHITECTURE 中增加 9 表 cron 时间表：
```markdown
| 生产日报 | production_daily_report | 0 18 * * * | 每天 18:00 |
| 生产月报 | production_monthly_report | 0 9 1 * * | 每月 1 日 09:00 |
| ... | ... | ... | ... |
```

---

### 问题 T-5：⚠️ cloud_relay.py 缺少启动健康检查（轻微）

**位置**：cloud_relay.py 启动脚本

**问题**：cloud_relay.py 启动时没有检查 MySQL 连接是否可用。如果 .env 中数据库凭证错误，APScheduler 会启动但所有 9 表导出都会失败。`/api/health` 只检查 Flask 服务是否在运行，不检查 MySQL 连接池。

**修复建议**：在 `_start_scheduler()` 中加入 MySQL 连接预检：
```python
def _start_scheduler():
    # 预检 MySQL 连接
    for cfg_key in ['container_center', 'inventory']:
        try:
            conn = _get_conn(cfg_key)
            conn.ping(reconnect=True)
            conn.close()
            logger.info(f'[v3.6.8] MySQL {cfg_key} 连接正常')
        except Exception as e:
            logger.error(f'[v3.6.8] MySQL {cfg_key} 连接失败: {e}，定时任务仍会注册但导出可能失败')
```

---

### 问题 T-6：⚠️ INVENTORY 环境变量无默认值说明（轻微）

**位置**：cloud_relay.py 第 71-72 行

```python
' safety_threshold': int(os.getenv('INVENTORY_SAFETY_THRESHOLD', '10')),
' slow_moving_days': int(os.getenv('INVENTORY_SLOW_MOVING_DAYS', '90')),
```

**问题**：这两个参数有默认值，但 ARCHITECTURE 文档中的环境变量表格（第 1120-1132 行）没有列出它们。运维人员不知道可以配置这些参数。

**修复建议**：在 6.7.5 环境变量表中补充：
```markdown
| `INVENTORY_SAFETY_THRESHOLD` | 库存预警安全阈值（默认 10） | 5005 |
| `INVENTORY_SLOW_MOVING_DAYS` | 呆滞库存天数阈值（默认 90） | 5005 |
```

---

## 三、数据库工程师视角（评分：60/100）

### 问题 D-1：🔴 _q_production_daily() 的 CASE WHEN 边界重叠（严重）

**位置**：cloud_relay.py 第 215-217 行

```python
CASE HOUR(created_at)
    WHEN 6,7,8,9,10,11,12,13,14 THEN '早班'
    WHEN 14,15,16,17,18,19,20,21,22 THEN '中班'
```

**问题**：14 同时出现在早班和中班两个区间（边界重叠）。MySQL CASE WHEN 从上到下匹配，14:00 的记录会被归为"早班"而不是"中班"。如果实际业务是 14:00 换班，这会导致数据偏差。

**修复建议**：
```python
# 方案A：严格划分（14:00 归中班）
WHEN 6,7,8,9,10,11,12,13 THEN '早班'
WHEN 14,15,16,17,18,19,20,21,22 THEN '中班'

# 方案B：按实际换班时间（建议先与业务确认换班时间）
WHEN 6,7,8,9,10,11,12,13,14,15 THEN '早班'  # 6:00-15:59
WHEN 16,17,18,19,20,21,22,23 THEN '中班'    # 16:00-23:59
```

---

### 问题 D-2：⚠️ _q_workorder_progress() JSON 函数无容错（中等）

**位置**：cloud_relay.py 第 341-345 行

```python
CASE
    WHEN pr.steps IS NOT NULL
         AND pr.current_step < JSON_LENGTH(pr.steps)
    THEN JSON_UNQUOTE(JSON_EXTRACT(
        pr.steps,
        CONCAT('$[', pr.current_step, '].name')
    ))
    ELSE NULL
END AS 当前工序
```

**问题**：如果 `pr.steps` 字段存储的不是合法 JSON，`JSON_LENGTH` 和 `JSON_EXTRACT` 会返回 NULL 而不报错。数据库中如果某条记录的 steps 字段被意外写入非 JSON 内容（如空字符串 `""`），这条记录会被静默跳过，运维人员不会发现。

**修复建议**：在 SQL 中加 JSON 验证，或在 Python 端捕获异常：
```python
# Python 端处理
try:
    current_step_name = row.get('当前工序') or '未知'
except:
    current_step_name = '未知'
```

---

### 问题 D-3：⚠️ _q_inventory_weekly() 无 LIMIT，存在性能风险（中等）

**位置**：cloud_relay.py 第 447-449 行

```sql
GROUP BY w.id, w.name
```

**问题**：没有 LIMIT 子句，理论上仓库数量不受控制。如果 `warehouses` 表有 1000+ 个仓库（包括已删除/停用的），这个查询可能返回大量数据。架构图中只提到了"主仓库"，但 SQL 里用的是 `w.is_active = 1` 而不是限制仓库数量。

**修复建议**：
```sql
-- 只统计主仓库（排除测试仓/虚拟仓）
WHERE DATE(it.created_at) BETWEEN %s AND %s
  AND w.is_active = 1
  AND w.deleted_at IS NULL
  AND w.name NOT LIKE '测试%'
  AND w.name NOT LIKE 'temp%'
```

---

### 问题 D-4：⚠️ _q_substep_recent() 默认 limit=100 可能漏数据（中等）

**位置**：cloud_relay.py 第 368-369 行

```python
def _q_substep_recent(since: datetime, limit: int = 100) -> List[Dict[str, Any]]:
```

**问题**：cron 表达式是 `*/30 * * * *`（每 30 分钟执行一次），但如果工序报工频率很高（比如车间同时有多人在操作），30 分钟内可能产生超过 100 条新记录，导致部分记录被截断丢失，永远不会被推送到智能表格。

**修复建议**：将 limit 改为 1000 或 5000，或去掉 limit（用 `since` 时间窗口控制）：
```python
def _q_substep_recent(since: datetime, limit: int = 5000) -> List[Dict[str, Any]]:
```

---

### 问题 D-5：⚠️ container_center 数据库直连 vs 5003 API 调用边界模糊（中等）

**位置**：cloud_relay.py 直接连接 container_center 和 inventory 两个库

**问题**：cloud_relay.py 直接连接 `container_center` 和 `inventory` 数据库，绕过了 5003 调度中心。R-001 约束说"禁止直连对方数据库"，但 cloud_relay.py 既不是 container_center 也不是 inventory，这是第三方服务直连数据库。

**分析**：stats 报表属于批量查询场景，直接读库比通过 API 更高效（避免大量 HTTP 请求）。这个做法是合理的，但需要明确 R-001 的适用范围是否包含"批量只读报表查询"。

**修复建议**：在 ARCHITECTURE 中补充 R-001 适用说明：
```markdown
- **R-001 补充说明**：统计表导出（批量只读查询）允许直接连接 container_center / inventory 数据库；涉及写入的操作禁止直连，必须通过对应 API。
```

---

### 问题 D-6：⚠️ MySQL 连接池未在文档中说明（轻微）

**位置**：cloud_relay.py 第 58-76 行（_get_conn）

**问题**：cloud_relay.py 使用 `dbutils.pooled_db.PooledDB` 管理连接池，但 ARCHITECTURE 文档没有说明这一点。如果运维人员重启服务时发现连接池未释放，可能排查方向错误。

**修复建议**：在 Phase-3 状态表或服务定义中补充：
```markdown
| `cloud_relay.py` | 使用 dbutils PooledDB 连接池（maxconnections=10），按需初始化（lazy init） |
```

---

## 四、安全工程师视角（评分：55/100）

### 问题 S-1：🔴 CLOUD_5004_HOST 环境变量无校验（严重）

**位置**：cloud_relay.py 第 606-607 行

```python
CLOUD_5004_HOST = os.getenv('CLOUD_5004_HOST', '')
target_url = f'http://{CLOUD_5004_HOST}:{CLOUD_5004_PORT}/api/smartsheet/write'
```

**问题**：如果 `CLOUD_5004_HOST` 未设置（返回空字符串），`target_url` 变成 `http://:5004`，`requests.post()` 会尝试连接本机端口 5004 而不是报错，容易产生难以追踪的网络错误。应该 fail-fast。

**修复建议**：
```python
CLOUD_5004_HOST = os.getenv('CLOUD_5004_HOST', '')
if not CLOUD_5004_HOST:
    raise RuntimeError("环境变量 CLOUD_5004_HOST 必须设置（无默认值）")
```

---

### 问题 S-2：🔴 API_KEY 鉴权机制不完整（严重）

**位置**：cloud_relay.py 第 41 行 + 第 790-793 行

```python
API_KEY = os.getenv('WECHAT_CLOUD_API_KEY', '')
# ...
@app.route('/api/stats/push', methods=['POST'])
@require_api_key
def stats_push():
```

**问题**：
1. API_KEY 默认为空字符串（不设 `.env` 时），`require_api_key` 装饰器会比较空字符串与请求头，空字符串请求也能通过
2. `/api/stats/trigger/<table_type>` 和 `/api/stats/status` **没有** `@require_api_key`，任何人可以触发 9 张表导出并查看 metrics
3. `/api/health` 无鉴权（可接受），但暴露了 scheduler 运行状态

**修复建议**：
```python
# 所有 stats 端点统一鉴权
@app.route('/api/stats/trigger/<table_type>', methods=['POST'])
@require_api_key
def trigger_export(table_type): ...

@app.route('/api/stats/status', methods=['GET'])
@require_api_key
def stats_status(): ...

# 并将 API_KEY 默认值改为强制要求
API_KEY = os.getenv('WECHAT_CLOUD_API_KEY')
if not API_KEY:
    raise RuntimeError("环境变量 WECHAT_CLOUD_API_KEY 必须设置")
```

---

### 问题 S-3：⚠️ 敏感数据未脱敏写入日志（中等）

**位置**：cloud_relay.py 多处 logger 调用

```python
logger.info(f'[{table_type}] 开始导出 | 显示名={display_name}')
logger.info(f'[stats/trigger] 手动触发: {table_type} ({display_name})')
```

**问题**：如果 records 中包含敏感信息（如客户名称、产品规格），直接用 f-string 写入日志文件，日志文件如果落入未授权人员手中会造成信息泄露。当前 9 张表的数据主要是生产统计，不含个人敏感信息，但 `workorder_progress` 包含客户名称，需要确认。

**修复建议**：对包含客户信息的表，使用脱敏后的 log：
```python
# 只记录表类型和记录数，不记录具体数据
logger.info(f'[{table_type}] 开始导出 | 记录数={len(records)}')
```

---

### 问题 S-4：⚠️ 幂等 batch_id 无加密（轻微）

**位置**：cloud_relay.py 第 609 行

```python
batch_id = str(uuid.uuid4())
```

**问题**：`uuid.uuid4()` 是随机生成的，无法从 batch_id 反推任何业务信息，这是好的。但 `batch_id` 会被发送到外部云端 5004，如果 5004 的日志被攻击者获取，随机 UUID 无法追溯来源。

**修复建议**：batch_id 中嵌入表类型前缀方便追溯：
```python
batch_id = f"{table_type}_{uuid.uuid4().hex[:12]}"
```

---

### 问题 S-5：ℹ️ 缺少安全相关的环境变量文档（轻微）

**位置**：ARCHITECTURE 文档环境变量表（第 1120-1132 行）

**问题**：5005 新增了多个环境变量（CLOUD_5004_HOST / PORT / API_KEY / INVENTORY_SAFETY_THRESHOLD 等），但环境变量表中没有列出，运维人员需要读代码才能知道需要配置哪些变量。

**修复建议**：在 6.7.5 环境变量表中增加 5005 相关变量：
```markdown
| `CLOUD_5004_HOST` | 云端 5004 服务器地址（用于统计表推送） | 5005 |
| `CLOUD_5004_PORT` | 云端 5004 端口（默认 5004） | 5005 |
| `CLOUD_5004_API_KEY` | 云端 5004 API 密钥 | 5005 |
| `WECHAT_CLOUD_API_KEY` | Stats Push 端点鉴权密钥 | 5005 |
| `INVENTORY_MYSQL_USER/PASSWORD` | Inventory 数据库凭证 | 5005 |
| `INVENTORY_SAFETY_THRESHOLD` | 库存预警阈值 | 5005 |
| `INVENTORY_SLOW_MOVING_DAYS` | 呆滞库存天数 | 5005 |
| `STATS_MAX_RETRIES` | 推送重试次数（默认 3） | 5005 |
| `STATS_FORWARD_TIMEOUT` | 推送超时秒数（默认 60） | 5005 |
```

---

## 五、汇总与优先级

### 问题汇总表

| ID | 视角 | 严重度 | 问题 | 快速修复 |
|----|------|:------:|------|---------|
| A-1 | 架构师 | ⚠️ 中 | 文档头部第4/6行矛盾 | 删除第6行 |
| A-2 | 架构师 | ⚠️ 轻微 | v3.6.5-proposal 与 v3.6.5 重复 | 合并为一条 |
| **A-3** | 架构师 | 🔴 高 | Phase-2 表格内容是职责描述而非代码修改记录 | 重写 Phase-2 表格 |
| A-4 | 架构师 | ⚠️ 中 | 大屏端口 5007 vs 5000 不一致 | 改为 5000 |
| A-5 | 架构师 | ⚠️ 轻微 | M-4"完成"描述不准确 | 改为"已无意义" |
| **A-6** | 架构师 | 🔴 高 | R-002 与 5005 直连云端 5004 矛盾 | 补充 R-002 豁免说明 |
| A-7 | 架构师 | ⚠️ 轻微 | "9 类/张"数量描述不一致 | 统一为"9 张表" |
| A-8 | 架构师 | ⚠️ 轻微 | Phase-3 状态表标题风格不统一 | 统一为动词短语 |
| **T-1** | 测试 | 🔴 高 | Stats Push 失败无降级方案 | 补充失败处理策略文档 |
| T-2 | 测试 | ⚠️ 中 | 9 表 Job 无独立 metrics | 增加 by_table 统计 |
| T-3 | 测试 | ⚠️ 中 | /api/stats/trigger 幂等无文档 | 补充端点说明 |
| T-4 | 测试 | ⚠️ 轻微 | 9 表 cron 时间无文档 | 补充 cron 时间表 |
| T-5 | 测试 | ⚠️ 轻微 | 启动无 MySQL 预检 | 增加连接预检 |
| T-6 | 测试 | ⚠️ 轻微 | INVENTORY 环境变量无文档 | 补充到环境变量表 |
| **D-1** | 数据库 | 🔴 高 | CASE WHEN 边界重叠（14点重复） | 修正 hour 区间 |
| D-2 | 数据库 | ⚠️ 中 | JSON 函数无容错 | 增加 try/except |
| D-3 | 数据库 | ⚠️ 中 | inventory_weekly 无 LIMIT | 增加 LIMIT 或过滤 |
| D-4 | 数据库 | ⚠️ 中 | substep_recent 默认 limit=100 可能漏数据 | 提高到 5000 |
| D-5 | 数据库 | ⚠️ 中 | R-001 适用范围模糊 | 补充 R-001 说明 |
| D-6 | 数据库 | ⚠️ 轻微 | 连接池无文档说明 | 补充到服务定义 |
| **S-1** | 安全 | 🔴 高 | CLOUD_5004_HOST 空值导致静默错误 | 加 fail-fast 检查 |
| **S-2** | 安全 | 🔴 高 | API_KEY 默认空 + 部分端点无鉴权 | 强制要求 + 全端点鉴权 |
| S-3 | 安全 | ⚠️ 中 | 敏感数据可能写入日志 | 改为只记录统计数字 |
| S-4 | 安全 | ⚠️ 轻微 | batch_id 无表类型前缀 | 改为 table_type_uuid 格式 |
| S-5 | 安全 | ⚠️ 轻微 | 缺少安全相关环境变量文档 | 补充到环境变量表 |

### 优先修复顺序（建议）

```
🔴 高优先级（立即修复）
  1. S-1  CLOUD_5004_HOST 空值 fail-fast         （cloud_relay.py）
  2. S-2  API_KEY 强制要求 + 全端点鉴权           （cloud_relay.py）
  3. A-3  Phase-2 表格内容修正                   （ARCHITECTURE.md）
  4. A-6  R-002 豁免说明                        （ARCHITECTURE.md）
  5. D-1  CASE WHEN 14点边界重叠                 （cloud_relay.py）
  6. T-1  Stats Push 失败降级文档                 （ARCHITECTURE.md）

⚠️ 中优先级（下一版本）
  7. A-4  大屏端口改为 5000                       （ARCHITECTURE.md）
  8. T-2  增加 by_table metrics                   （cloud_relay.py）
  9. D-4  substep_recent limit 提高到 5000        （cloud_relay.py）
 10. D-5  R-001 适用范围说明                      （ARCHITECTURE.md）
 11. T-3  幂等说明补充                           （ARCHITECTURE.md）
 12. S-3  日志脱敏                               （cloud_relay.py）

⚠️ 低优先级（下个迭代）
 13. A-1  删除矛盾头部第6行                       （ARCHITECTURE.md）
 14. A-2  合并 v3.6.5-proposal                   （ARCHITECTURE.md）
 15. D-2  JSON 函数容错                           （cloud_relay.py）
 16. D-3  inventory_weekly 增加 LIMIT             （cloud_relay.py）
 17. T-4  补充 cron 时间表                        （ARCHITECTURE.md）
 18. S-4  batch_id 加表类型前缀                   （cloud_relay.py）
 19. S-5  补充环境变量文档                       （ARCHITECTURE.md）
 20. T-5  MySQL 启动预检                         （cloud_relay.py）
 21. T-6  INVENTORY 环境变量文档                 （ARCHITECTURE.md）
 22. A-5  M-4 描述修正                           （ARCHITECTURE.md）
 23. A-7  9张表数量描述统一                       （ARCHITECTURE.md）
 24. A-8  Phase-3 标题风格统一                    （ARCHITECTURE.md）
 25. D-6  连接池文档说明                          （ARCHITECTURE.md）
```

---

**审计结论**：文档整体质量较高，架构演进过程记录清晰，但 v3.6.8 N-1 改动后有多处遗留问题需要同步修复。**最高优先修复 6 个 🔴 高优先级问题**，其中 3 个在代码（cloud_relay.py），3 个在文档（ARCHITECTURE.md）。
