# 架构师第三轮审计报告 - ARCHITECTURE_v3.6.md

> **审计对象**: `d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\docs\ARCHITECTURE_v3.6.md`
> **审计轮次**: 第三轮（架构师视角）
> **审计日期**: 2026-06-24
> **审计人**: AI 架构师
> **审计重点**: v3.6.8 N-1 改造相关章节、5005 定位、代码与文档一致性

---

## 0. 审计摘要

| 维度 | 数量 | 备注 |
|------|:----:|------|
| 🔴 高优先级问题 | **3** | 影响代码可读性、可维护性的关键事实错误 |
| 🟡 中优先级问题 | **6** | 章节一致性与交叉引用遗漏 |
| 🔵 低优先级问题 | **4** | 措辞优化与小补充 |
| 已修复项确认 | **5** | 第二轮审计提及的问题已在 v3.6.8 中解决 |

**主线评估**：文档主体结构清晰，v3.6.8 N-1 改造描述基本准确，但存在 1 处关键数字错误（行数）、1 处端点状态错误（`/api/stats/push` "已删除"）、1 处端口号错误（5000 vs 5007），需立即修复。

---

## 1. 已修复项确认（前轮审计遗留）

| # | 修复项 | 证据 | 状态 |
|---|--------|------|:----:|
| 1 | v3.6.5 阶段旧方案已加"已作废"标记 | L128-130 `~~v3.6.5 架构重构提案~~ → ⚠️ 已作废（被 v3.6.8 N-1 替代）` | ✅ |
| 2 | 5005 定位明确为"统计表推送服务" | L90 `**5005 当前定位**：统计表推送服务（stats push + APScheduler 定时任务）` | ✅ |
| 3 | 9 张表 cron 表清晰列出 | L93-105 | ✅ |
| 4 | 端口表 5005 增加了完整描述 | L193 列出全部 6 个关键属性（APScheduler / MySQL / 直连 / 预检 / 鉴权 / 强制变量） | ✅ |
| 5 | R-002 例外条款明确标注 5004 | L223 `例外：5005 统计表推送直接 POST 云端 5004（智能表格 Webhook）` | ✅ |

---

## 2. 🔴 高优先级问题

### P0-1. 【事实错误】`cloud_relay.py` 行数 873 → 实际 775

**位置**:
- L4 `cloud_relay.py 重写 873 行`
- L78 `完全重写（143行→873行）`

**证据**:
```powershell
# 实测
PS> Get-Content cloud_relay.py | Measure-Object -Line
Lines: 775
```

**分析**: 文档两次提及 873 行，实际文件为 775 行，偏差 -98 行（-11%）。"143 行→775 行"才是事实。

**修复建议**: 改为 `完全重写（143行→775行）`，与 L4 一致。

**影响**: 中等。审计员按 873 行查找功能时会找不到对应行号，但代码本身功能正确。

---

### P0-2. 【事实错误】`/api/stats/push` 端点"已在 v3.6.8 N-1 删除" — 实际未删除

**位置**: L71 `**注**：`/api/stats/push` 端点已在 v3.6.8 N-1 删除（见下方）`

**证据**:
```python
# cloud_relay.py:815-829
@app.route('/api/stats/push', methods=['POST'])
@require_api_key
def stats_push():
    data = request.get_json(silent=True) or {}
    table_type = data.get('table_type', '')
    records = data.get('records', [])
    period_key = data.get('period_key', '')
    ...
```

**分析**:
- 文档说"已删除"但 cloud_relay.py:815 仍有该端点（带 X-API-Key 鉴权）。
- 真实情况：**5003 的 `/api/stats/push` 已删除**（standalone_dispatch_server.py:275 注释明确），**5005 的 `/api/stats/push` 仍然存在**（作为外部推送入口）。
- L107-114 端点表中 `/api/stats/push` 也明确列出，说明表与文字描述互相矛盾。

**修复建议**:
- L71 改为 `**注**：5003 端的 `/api/stats/push` 已在 v3.6.8 N-1 删除（迁移至 5005，5005 仍保留此端点供外部推送）`

**影响**: 高。审计员按"已删除"去查代码会得到错误结论。

---

### P0-3. 【端口错误】dashboard_server 端口 5000 vs 5007 自相矛盾

**位置**:
- L1073 `可视化大屏(5000)`（6.7.1 节启动顺序）
- L1080 `5000 | 可视化大屏 | ...`（6.7.2 节端口表）
- L176 `├─ 可视化大屏: 5007 ...`（1.1 节架构图）
- L194 `5007 | dashboard_server | ...`（1.2 节端口表）

**证据**:
```python
# desktop/views/dashboard/dashboard_server.py:502
_port = int(os.getenv('PORT', 5007))  # 默认端口 5007

# L513
port = int(os.getenv('PORT', 5007))
app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

# L8 注释
# Open: http://localhost:5000  ← 注释误导，但实际默认 5007
```

**分析**:
- 代码默认端口是 **5007**（3 处 `os.getenv('PORT', 5007)` 一致）。
- L176 架构图、L194 端口表（1.2 节）= **5007** ✅
- L1073 启动顺序、L1080 端口表（6.7.2 节）= **5000** ❌
- 文档自身在两个章节列出两套不同的端口号，会让部署人员无所适从。

**修复建议**:
- L1073 改为 `可视化大屏(5007)`
- L1080 改为 `5007 | 可视化大屏 | ...`
- 同步修正 L741 `start_dashboard` 启动脚本说明（虽然此处未直接出现 5000，但要确认）
- 备注：dashboard_server.py:8 注释 `Open: http://localhost:5000` 也应改为 5007。

**影响**: 高。端口号错误会导致服务启动冲突或连不上。

---

## 3. 🟡 中优先级问题

### P1-1. 【交叉引用遗漏】`/api/stats/push` 端点描述与 Phase-1/Phase-2 不一致

**位置**:
- L67-71 Phase-1 表：列出 5003 新增的 `/api/queue/*` 端点，注释说明 `/api/stats/push` 已删除
- L73-79 Phase-2 表：列出 5005 cloud_relay.py 重写
- L107-114 端点表：列出 `/api/stats/push | POST | X-API-Key`

**分析**:
- 端点表（L109-114）才是 SSOT，但 Phase-1 L71 的注释与之矛盾。
- 建议统一为"迁移"而非"删除"。

**修复建议**: 同 P0-2 修复 L71 后即可一致。

---

### P1-2. 【数字错误】`standalone_dispatch_server.py` 删除行数 62 vs 实际 64

**位置**:
- L4 `standalone_dispatch_server.py 删除 62 行`
- L77 `删除 /api/stats/push 端点（62行，死代码）`

**证据**:
```python
# standalone_dispatch_server.py:274-275 注释
# [v3.6.8 N-1] /api/stats/push 已迁移到 5005 cloud_relay.py，5003 不再感知统计表
# 原 Phase-1 端点（275-338行）已删除，避免与 5005 端点重复推送
```

**分析**: 注释明确说"275-338行已删除"，实际是 64 行（338-275+1=64），不是 62。

**修复建议**: 改为"删除 64 行"。

---

### P1-3. 【描述模糊】5005 端口"lazy init"与"启动时预检"描述不准确

**位置**: L193 `内嵌 APScheduler + MySQL 连接池（lazy init）；启动时 MySQL 连接预检`

**证据**:
```python
# cloud_relay.py:81-99 _get_conn() 函数
def _get_conn(cfg_key: str):
    if cfg_key not in _MYSQL_POOLS:  # ← lazy init: 首次调用才创建 PooledDB
        ...
        _MYSQL_POOLS[cfg_key] = PooledDB(...)

# cloud_relay.py:773-780 _start_scheduler() 中预检
for cfg_key in ['container_center', 'inventory']:
    try:
        conn = _get_conn(cfg_key)
        conn.ping(reconnect=True)
        conn.close()
        logger.info(f'[v3.6.8] MySQL {cfg_key} 连接正常')
    except Exception as e:
        logger.warning(f'...预检失败: {e}，定时任务仍会注册但导出可能失败')
```

**分析**:
- "lazy init" ✅ 准确（`_get_conn` 首次调用才建 Pool）
- "启动时 MySQL 连接预检" ⚠️ 描述不准确 — 预检失败仅 warning，**不阻止启动**，**不阻止定时任务注册**。建议补"预检失败不阻塞启动"。

**修复建议**: L193 改为 `启动时 MySQL 连接预检（失败仅 warning，不阻塞启动与定时任务注册）`

---

### P1-4. 【链接表述欠妥】"v3.6.5 统计表端点说明"小标题语义重复

**位置**: L107 `#### 统计表端点说明（v3.6.8 N-1）`

**分析**:
- L107 小标题写"v3.6.8 N-1"
- L116 又写"统计表推送失败处理策略（v3.6.8 N-1）"
- L93 又写"9 张统计表 cron 时间表（v3.6.8 N-1）"
- 三处都用 N-1 后缀，但实际 N-1 是相对于 N 方案（v3.6.7 阶段），对读者不友好。

**修复建议**: 在 L65 Phase 段补充一句 `> 本节所有"v3.6.8 N-1"标注指 5005 接管 9 表定时任务的方案`，消除歧义。

---

### P1-5. 【R-004 命名不一致】与 project_rules.md 冲突

**位置**: L224-225 R-003 / R-004 规则

**证据**:
```markdown
# project_rules.md R-001~R-003 是服务架构约束（5003/5004/5005 端口分配）
# 但本文档 L224-225 引入 R-004 描述"5005 cloud_relay 状态"
```

**分析**:
- R-001~R-003 在 project_rules.md 都是"服务间通信"或"服务架构"约束。
- R-004 在本文档变成"5005 cloud_relay 状态"声明，**语义层级不同**。
- 容易让审计员误以为 R-004 也是强制架构约束。

**修复建议**:
- 选项 A：将 R-004 改为"**约束声明**"或"**架构事实**"，与 R-001~R-003 区分。
- 选项 B：R-004 拆分到 1.4 节的"端口状态摘要"或 1.5 节端口对照表。

---

### P1-6. 【环境变量表不完整】缺 RELAY_* / MYSQL_HOST / 数据库名变量

**位置**: L1129-1149 环境变量表

**证据**:
```python
# cloud_relay.py:67-71
'host': os.getenv('MYSQL_HOST', 'localhost'),
'port': int(os.getenv('MYSQL_PORT', '3306')),
'database': os.getenv(database_env, default_db),  # ← 引用 CONTAINER_MYSQL_DATABASE / INVENTORY_DB_NAME

# cloud_relay.py:88
'container_center': _mysql_cfg(
    'CONTAINER_MYSQL_USER', 'CONTAINER_MYSQL_PASSWORD',
    'CONTAINER_MYSQL_DATABASE', 'container_center'),  # ← CONTAINER_MYSQL_DATABASE

# cloud_relay.py:91
'inventory': _mysql_cfg(
    'INVENTORY_MYSQL_USER', 'INVENTORY_MYSQL_PASSWORD',
    'INVENTORY_DB_NAME', 'inventory'),  # ← INVENTORY_DB_NAME

# cloud_relay.py:885-900
host = os.getenv('RELAY_HOST', '0.0.0.0')
port = int(os.getenv('RELAY_PORT', '5005'))
...
threads=int(os.getenv('RELAY_WORKERS', '4')),
connection_limit=int(os.getenv('RELAY_CONN_LIMIT', '100'))
```

**缺失项**:
| 变量 | 用途 | 是否强制 |
|------|------|:--------:|
| `MYSQL_HOST` | MySQL 主机 | 否（默认 localhost）|
| `MYSQL_PORT` | MySQL 端口 | 否（默认 3306）|
| `CONTAINER_MYSQL_DATABASE` | container_center 数据库名 | 否（默认 container_center）|
| `INVENTORY_DB_NAME` | inventory 数据库名 | 否（默认 inventory）|
| `RELAY_HOST` | 5005 监听地址 | 否（默认 0.0.0.0）|
| `RELAY_PORT` | 5005 监听端口 | 否（默认 5005）|
| `RELAY_WORKERS` | waitress 线程数 | 否（默认 4）|
| `RELAY_CONN_LIMIT` | waitress 连接限制 | 否（默认 100）|

**修复建议**: 在 L1149 后增加 1 张子表或 1 段说明，列出上述 8 个非强制可选变量。

---

## 4. 🔵 低优先级问题

### P2-1. 【措辞】L88 "链路从 3 跳→2 跳"未指明哪条链路

**位置**: L88 `5005 接管 9 张统计表定时任务（APScheduler+导出+推送全在 5005 内部）；5003 不再感知统计表；链路从 3 跳→2 跳`

**分析**:
- 3 跳链路：5005 → 5003 转发 → 云端 5004（v3.6.5 阶段）
- 2 跳链路：5005 → 云端 5004（v3.6.8 N-1 阶段）
- 文档未明确哪 3 跳是哪 3 跳，读者需自己推导。

**修复建议**: L88 改为 `原 v3.6.5 阶段: 5005 → 5003 → 云端 5004（3 跳）；v3.6.8 N-1: 5005 → 云端 5004（2 跳）`

---

### P2-2. 【小错】L78 描述"新增 /api/stats/trigger、/api/stats/status 端点"未提及 /api/stats/push

**位置**: L78 `新增 /api/stats/trigger、/api/stats/status 端点`

**分析**: L78 只列了新增的 2 个端点，但 `/api/stats/push` 是从 5003 迁移过来的，文档应说明"迁移 + 新增"。

**修复建议**: L78 改为 `新增 /api/stats/trigger、/api/stats/status 端点；/api/stats/push 从 5003 迁移到 5005`

---

### P2-3. 【不一致】L91 `stats_smart_sheet/ 目录状态` 与实际目录内容不一致

**位置**: L91 `**stats_smart_sheet/ 目录状态**：代码已全部迁移到 cloud_relay.py（v3.6.8 N-1），该目录待删除。请勿使用该目录下的脚本。`

**证据**:
```powershell
# 实测目录
PS> ls mobile_api_ai/stats_smart_sheet/
  - _launch_5005.py
  - _start_5005.bat
  - config.py
  - db_queries.py
  - mysql_config.py
  - production_lines.py
  - setup.py
  - setup_create_smart_sheets.py
  - setup_create_sync_log.py
  - setup_smart_sheets.py
  - smart_sheet_client.py
  - smart_sheet_exporter.py
  - stats_sync_log.sql
  - requirements.txt
  - .env.example
  - __init__.py
  - _r.txt / _r2.txt / _launch_out.txt / check_out.txt / check_out2.txt / _t3.out
```

**分析**:
- 文档说"代码已全部迁移到 cloud_relay.py" ✅
- 文档说"该目录待删除" ⚠️ 目录仍有 17 个文件，包括启动脚本（`_launch_5005.py` / `_start_5005.bat`）、SQL 脚本、env 示例等。
- 建议拆分为"代码已迁移"和"待清理辅助文件"两段。

**修复建议**: L91 改为 `**stats_smart_sheet/ 目录状态**：业务代码（config.py / mysql_config.py / db_queries.py / smart_sheet_*.py）已全部迁移到 cloud_relay.py；但目录仍残留启动脚本（_launch_5005.py / _start_5005.bat）和 SQL 脚本（stats_sync_log.sql / setup_*.py），需 P1 优先级清理。`

---

### P2-4. 【小补充】L8 注释与实际端口不一致（已包含在 P0-3 中提及，但建议单独记录）

**位置**: `dashboard_server.py:8` `Open: http://localhost:5000`

**分析**: 注释误导，应改为 5007。

**修复建议**: 修正代码注释为 5007 或保持 5000 并在文档明确"启动时通过 PORT 环境变量覆盖"。

---

## 5. 跨节引用一致性矩阵

| 主题 | 出现位置 | 一致性 |
|------|----------|:------:|
| 5005 是"统计表推送" | L90 / L130 / L161 / L181 / L192 / L193 / L223 / L225 | ✅ 一致 |
| 5005 WeChat 中继废弃 | L85 / L90 / L161 / L181 / L225 | ✅ 一致 |
| `/api/stats/push` 端点存在 | L109-114（表）/ L71（注释：说"已删除"）/ cloud_relay.py:815（实际存在） | ❌ L71 错误 |
| 9 张表 cron 列表 | L93-105 / cloud_relay.py:166-176 | ✅ 一致 |
| MySQL 数据库（container_center / inventory） | L193 / L222 / L1142-1145 / cloud_relay.py:86-92 | ✅ 一致 |
| 强制环境变量 WECHAT_CLOUD_API_KEY | L1133 / cloud_relay.py:43 | ✅ 一致 |
| 强制环境变量 CLOUD_5004_HOST | L1139 / cloud_relay.py:684 | ✅ 一致 |
| 5005 链路 3 跳→2 跳 | L12 / L88 | ⚠️ 2 处一致但未指明具体链路 |
| dashboard_server 端口 | L176 / L194（5007）vs L1073 / L1080（5000）vs dashboard_server.py:502（5007） | ❌ 端口表自相矛盾 |
| 62 行删除 | L4 / L77（说 62 行）vs L275 注释（说 275-338 = 64 行） | ❌ 数字偏差 2 行 |

---

## 6. 一致性总结

### 已验证的关键事实 ✅
1. cloud_relay.py:815-829 `/api/stats/push` 端点存在
2. cloud_relay.py:833-841 `/api/stats/trigger/<table_type>` 端点存在
3. cloud_relay.py:844-862 `/api/stats/status` 端点存在
4. cloud_relay.py:865-873 `/api/health` 端点存在（无鉴权）
5. cloud_relay.py:41-43 WECHAT_CLOUD_API_KEY 强制
6. cloud_relay.py:682-684 CLOUD_5004_HOST 强制
7. cloud_relay.py:696-721 3 次重试 + 1s→2s→4s 指数退避
8. cloud_relay.py:782-803 APScheduler + 9 张表 cron 注册
9. cloud_relay.py:773-780 MySQL 启动预检（失败仅 warning）
10. standalone_dispatch_server.py:104-108 5003 已不含 `/api/stats/push` 白名单

### 关键事实错误 ❌
1. **行数 873 ≠ 775**（L4 / L78）
2. **`/api/stats/push` 未删除**（L71）
3. **端口 5000 vs 5007 矛盾**（L1073 / L1080 vs L176 / L194）
4. **删除 62 行 ≠ 64 行**（L4 / L77 vs L275 注释）

---

## 7. 下一刀（建议优先级）

1. **🔴 立即修复 P0-3 端口错误**（L1073、L1080 + dashboard_server.py:8 注释）
2. **🔴 立即修复 P0-2 端点描述**（L71 改为"迁移"）
3. **🔴 立即修复 P0-1 行数错误**（L4、L78 改为 775）
4. 🟡 同步修复 P1-2 删除行数（L4、L77 改为 64）
5. 🟡 完善 P1-6 环境变量表（补 8 个非强制变量）
6. 🟡 拆分 P2-3 stats_smart_sheet 描述
7. 🟡 优化 P1-5 R-004 命名

---

## 8. 一句话总结

本文档对 v3.6.8 N-1 改造（5005 接管 9 表定时任务）的整体描述清晰准确，但存在 **3 处事实性错误**（行数 873、端点"已删除"、端口 5000）需要立即修正；**6 处中等问题**（端点描述、删除行数、lazy init 描述、跨节引用）建议同步修正；**4 处低等问题**（措辞优化）可在后续迭代处理。
