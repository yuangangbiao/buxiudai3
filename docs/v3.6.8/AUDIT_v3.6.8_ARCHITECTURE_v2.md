# 审计报告 v2 - ARCHITECTURE_v3.6.md（第二轮）

> **审计范围**：ARCHITECTURE_v3.6.md（v3.6.8，第二轮，基于第一轮审计修复后的状态）
> **审计视角**：AI 团队四方审计（架构师 / 测试工程师 / 数据库工程师 / 安全工程师）
> **审计日期**：2026-06-24
> **前置状态**：第一轮审计（25 项问题）已完成，其中 6 项 🔴 高优先级已修复，本轮审计剩余 19 项 + 新增问题

---

## 一、第一轮审计修复状态确认

### ✅ 已修复（6/25）

| # | 问题 | 修复方式 |
|---|------|---------|
| S-1 | CLOUD_5004_HOST 空值静默错误 | ✅ 代码加 fail-fast |
| S-2 | API_KEY 默认空 + 部分端点无鉴权 | ✅ 代码强制要求 + 全端点鉴权 |
| D-1 | CASE WHEN 14点边界重叠 | ✅ 早班改为 6-13 |
| A-3 | Phase-2 表格内容错误 | ✅ 重写为 v3.6.8 N-1 内容 |
| A-6 | R-002 与 5005 直连云端 5004 矛盾 | ✅ 补充"微信相关"限定 + 豁免说明 |
| T-1 | Stats Push 失败无降级方案文档 | ✅ 新增"统计表推送失败处理策略"段落 |

### ⚠️ 未修复（19/25）

| # | 严重度 | 问题 | 所在文件 |
|---|:------:|------|---------|
| A-1 | ⚠️ 中 | 文档头部第4/6行矛盾 | ARCHITECTURE.md |
| A-2 | ⚠️ 轻微 | v3.6.5-proposal 与 v3.6.5 重复 | ARCHITECTURE.md |
| ~~A-4~~ | — | ~~大屏端口 5007 vs 5000~~ | ~~ARCHITECTURE.md~~ |
| A-5 | ⚠️ 轻微 | M-4"完成"描述不准确 | ARCHITECTURE.md |
| A-7 | ⚠️ 轻微 | "9 类/张"数量描述不一致 | ARCHITECTURE.md |
| A-8 | ⚠️ 轻微 | Phase-3 状态表标题风格不统一 | ARCHITECTURE.md |
| T-2 | ⚠️ 中 | 9 表 Job 无独立 metrics | cloud_relay.py |
| T-3 | ⚠️ 中 | /api/stats/trigger 幂等无文档 | ARCHITECTURE.md |
| T-4 | ⚠️ 轻微 | 9 表 cron 时间无文档 | ARCHITECTURE.md |
| T-5 | ⚠️ 轻微 | 启动无 MySQL 预检 | cloud_relay.py |
| T-6 | ⚠️ 轻微 | INVENTORY 环境变量无文档 | ARCHITECTURE.md |
| D-2 | ⚠️ 中 | JSON 函数无容错 | cloud_relay.py |
| D-3 | ⚠️ 中 | inventory_weekly 无 LIMIT | cloud_relay.py |
| D-4 | ⚠️ 中 | substep_recent 默认 limit=100 可能漏数据 | cloud_relay.py |
| D-5 | ⚠️ 中 | R-001 适用范围模糊（批量只读查询） | ARCHITECTURE.md |
| D-6 | ⚠️ 轻微 | 连接池无文档说明 | ARCHITECTURE.md |
| S-3 | ⚠️ 中 | 敏感数据可能写入日志 | cloud_relay.py |
| S-4 | ⚠️ 轻微 | batch_id 无表类型前缀 | cloud_relay.py |
| S-5 | ⚠️ 轻微 | 缺少安全相关环境变量文档 | ARCHITECTURE.md |

> **注**：第一轮审计 A-4（"大屏端口 5007 应为 5000"）为**误判**——实测 `desktop/views/dashboard/dashboard_server.py` 第 502 行：`port = int(os.getenv('PORT', 5007))`，文档 5007 正确。

---

## 二、第一轮遗留问题逐一审视（第二轮新增视角）

### A-1 重新审视：矛盾升级了（架构师）

**位置**：第 3-6 行

第一轮审计指出"第 4 行说包含代码修改，第 6 行说仅修改文档"，但 v3.6.8 恰恰是改动最大的版本（cloud_relay.py 143→873 行）。第 6 行是 v3.6.5 遗留的模板文字，忘了删除，严重误导读者认为 v3.6.8 没改代码。

**修复**：删除第 6 行即可。

---

### A-2 重新审视：修订历史表本身有设计问题（架构师）

**位置**：第 12-13 行

v3.6.5-proposal 和 v3.6.5 是同一个日期（2026-06-24）的两条记录，内容高度重复。这个"提案 + 完成"的双条目模式在历史表中造成大量冗余文本。

**建议**：修订历史表应该只记录"最终状态"，提案过程不单独列条目。"v3.6.5-proposal" 这行应该删除，内容并入 v3.6.5。

---

### A-7 重新审视：文档中"9类报表"的实际数量（架构师）

审计员实测了 `smart_sheet_exporter.py` 和 `cloud_relay.py`，确认有 **9 个**导出函数（_q_production_daily, _q_production_monthly, _q_workshop_capacity, _q_workorder_progress, _q_substep_recent, _q_inventory_weekly, _q_inventory_monthly, _q_inventory_alert, _q_inventory_slow_moving）。

文档标题写"9类报表"是准确的（9 类统计维度），所有其他位置写"9 张表"也没问题。这个不是问题，审计员澄清。

---

### D-4 重新审视：substep_recent 漏数据的风险评估（数据库工程师）

**位置**：cloud_relay.py limit=100

第一轮审计担忧"100 条可能不够"。第二轮重新评估：

- 工序报工频率：车间操作员提交一次工序报工，每小时理论上限约 20-50 条
- 30 分钟内：约 10-25 条新记录
- 100 条上限：完全够用，即使车间满负荷运转
- 极端场景（100+ 条/30分钟）：需要 6+ 人同时操作，概率极低

**结论**：limit=100 在实际业务中够用，但第一轮审计的担忧是合理的防御性编程思维。**建议提高到 500**，留安全余量，但不紧急。

---

## 三、新增问题（第二轮发现）

### N-1：ASCII 架构图标题仍显示 v3.6.5（🔴 高，架构师）

**位置**：第 144 行

```markdown
│                    跟单系统 v3.6.5 架构（v3.6.5-proposal）                  │
```

文档主体已升级到 v3.6.8，但架构图标题仍是 v3.6.5-proposal。

**修复**：改为 `│                    跟单系统 v3.6.8 架构（N-1 改造后）                   │`

---

### N-2：大量作废内容造成文档臃肿（⚠️ 中，架构师）

**位置**：第 106-134 行

v3.6.5 提案相关内容占了近 **30 行**的作废标记：
- 作废标题（3 处）
- 作废说明（3 处）
- 作废方案（M-1~M-7）

这些内容对理解当前架构**毫无帮助**，反而干扰阅读。v3.6.5 提案的所有重要内容已被 v3.6.8 N-1 覆盖。

**修复**：将第 106-134 行整块替换为一行简洁的归档说明：
```markdown
---

> **历史**：v3.6.5 曾提出"5005 合并入 5003"方案（Phase-1/2/3），被 v3.6.8 N-1 替代。具体内容见 ARCHITECTURE_v3.6.md 的更早版本。

---
```

---

### N-3：stats_smart_sheet/ 目录状态未归档（⚠️ 中，架构师）

**现状**：`stats_smart_sheet/` 目录代码已全部迁入 `cloud_relay.py`，但目录本身**未被删除**。

**风险**：
1. 运维人员可能不知道代码已迁移，运行 `python smart_sheet_exporter.py` 或 `smart_sheet_client.py` 得到意外结果
2. cron 定时任务可能还在 `crontab -l` 里注册了旧脚本
3. 后续人员可能修改这个目录而不是 cloud_relay.py

**修复建议**：在 ARCHITECTURE 中明确说明：
```markdown
> **stats_smart_sheet/ 目录状态**：代码已迁移到 cloud_relay.py（v3.6.8 N-1），该目录待删除。请勿使用该目录下的脚本。
```

---

### N-4：Phase-1 代码修改记录与当前架构矛盾（⚠️ 中，架构师）

**位置**：第 73 行

```markdown
| `standalone_dispatch_server.py` | 新增 `/api/stats/push` 端点 |
```

Phase-1 说"/api/stats/push 在 5003"。但 v3.6.8 N-1 后，cloud_relay.py 里也有 `/api/stats/push`（第 790 行）。现在有两处 `/api/stats/push`：
- 5003 的：原来 Phase-1 加的，可能还有
- 5005 的：v3.6.8 新增的，用于外部调用

**需要确认**：5003 的 `/api/stats/push` 还在不在？如果 5003 还保留这个端点，是否与 5005 的产生冲突？

---

### N-5：cloud_relay.py 内部依赖未在文档中说明（⚠️ 中，测试工程师）

**位置**：cloud_relay.py 新增的 MySQL / APScheduler 依赖

文档（Phase-3 说明）中只说"5005 接管 9 张统计表定时任务"，没有说明：
1. **MySQL 连接**：需要配置 `CONTAINER_MYSQL_*`、`INVENTORY_MYSQL_*` 环境变量
2. **APScheduler**：需要安装 `APScheduler` 库（已在第 1 轮审计中提到会 lazy import）
3. **PyMySQL + DBUtils**：连接池依赖
4. **直接连库 vs API 调用**：cloud_relay.py 直连 MySQL，不走 5003 API

这些依赖对运维部署很关键，文档中没有提及。

**修复建议**：在 Phase-3 状态表或服务定义中补充：
```markdown
| `cloud_relay.py` | 使用 dbutils PooledDB 连接池（lazy init）；直连 container_center + inventory 数据库；需要 APScheduler 库 |
```

---

### N-6：文档未记录 5005 需要哪些环境变量（⚠️ 中，安全工程师）

第一轮审计 S-5 提到了这个问题，但还没修复。v3.6.8 N-1 后 5005 新增了大量强制要求的环境变量：

| 环境变量 | 状态 | 说明 |
|---------|------|------|
| `CLOUD_5004_HOST` | 🔴 强制 | 无默认值，不设直接退出 |
| `WECHAT_CLOUD_API_KEY` | 🔴 强制 | 无默认值，不设直接退出 |
| `CLOUD_5004_PORT` | 🟢 可选 | 默认 5004 |
| `CLOUD_5004_API_KEY` | 🟢 可选 | 默认空 |
| `INVENTORY_SAFETY_THRESHOLD` | 🟢 可选 | 默认 10 |
| `INVENTORY_SLOW_MOVING_DAYS` | 🟢 可选 | 默认 90 |
| `STATS_MAX_RETRIES` | 🟢 可选 | 默认 3 |
| `STATS_FORWARD_TIMEOUT` | 🟢 可选 | 默认 60 |

文档中的环境变量表（第 1120 行附近）没有这些。

---

### N-7：5003 内的 /api/stats/push 端点是否还存在（⚠️ 中，数据库工程师）

需要确认：5003 的 standalone_dispatch_server.py 里，Phase-1 新增的 `/api/stats/push` 是否还在？

如果还在，那现在有两套 `/api/stats/push`：
- 5003: 原来的，把数据 POST 到 localhost:5005（v3.6.5 阶段）
- 5005: v3.6.8 新增的，直接 POST 到云端 5004

这会导致数据被推送两次或推送路径混乱。

---

### N-8：APScheduler 后台任务无 graceful shutdown（⚠️ 中，测试工程师）

**位置**：cloud_relay.py `_stop_scheduler()` + `atexit`

```python
_stats_scheduler.shutdown(wait=False)
```

`wait=False` 意味着正在运行的任务会被强制中断。如果一个导出任务正在查询 MySQL，shutdown 会直接杀掉它。下次启动时，这条数据就漏了。

**建议**：改为 `shutdown(wait=True, cancel_running=False)`——等待当前任务完成但不启动新任务。

---

## 四、汇总与优先修复顺序

### 全部问题汇总（第一轮遗留 19 项 + 第二轮新增 8 项 = 27 项）

| ID | 来源 | 严重度 | 问题 | 快速修复 |
|----|------|:------:|------|---------|
| **N-1** | 第二轮新增 | 🔴 高 | ASCII 架构图标题仍是 v3.6.5-proposal | 改标题 |
| **A-1** | 第一轮遗留 | ⚠️ 中 | 文档头部第 6 行与第 4 行矛盾 | 删除第 6 行 |
| **N-2** | 第二轮新增 | ⚠️ 中 | 作废内容占 30 行臃肿文档 | 替换为一行归档说明 |
| **N-3** | 第二轮新增 | ⚠️ 中 | stats_smart_sheet/ 目录状态未归档 | 补充目录状态说明 |
| **N-4** | 第二轮新增 | ⚠️ 中 | Phase-1 说 /api/stats/push 在 5003，与 5005 冲突 | 确认 5003 端点是否还存在 |
| **N-5** | 第二轮新增 | ⚠️ 中 | cloud_relay.py 内部依赖（MySQL/APScheduler）未在文档说明 | 补充服务依赖说明 |
| **A-2** | 第一轮遗留 | ⚠️ 轻微 | v3.6.5-proposal 与 v3.6.5 重复条目 | 合并为一条 |
| **A-5** | 第一轮遗留 | ⚠️ 轻微 | M-4"完成"描述不准确 | 改为"已无意义" |
| **A-7** | 第一轮遗留 | ⚠️ 轻微 | "9 类/张"描述不一致 | 已确认不是问题 |
| **A-8** | 第一轮遗留 | ⚠️ 轻微 | Phase-3 表格标题风格不统一 | 统一为动词短语 |
| **T-2** | 第一轮遗留 | ⚠️ 中 | 9 表 Job 无独立 metrics | 增加 by_table 统计 |
| **T-3** | 第一轮遗留 | ⚠️ 中 | /api/stats/trigger 幂等无文档 | 补充端点说明 |
| **T-4** | 第一轮遗留 | ⚠️ 轻微 | 9 表 cron 时间无文档 | 补充 cron 时间表 |
| **T-5** | 第一轮遗留 | ⚠️ 轻微 | 启动无 MySQL 预检 | 增加连接预检 |
| **T-6** | 第一轮遗留 | ⚠️ 轻微 | INVENTORY 环境变量无文档 | 补充到环境变量表 |
| **D-2** | 第一轮遗留 | ⚠️ 中 | JSON 函数无容错 | 增加 try/except |
| **D-3** | 第一轮遗留 | ⚠️ 中 | inventory_weekly 无 LIMIT | 增加过滤条件 |
| **D-4** | 第一轮遗留 | ⚠️ 中 | substep_recent 默认 limit=100 可能漏数据 | 提高到 500 |
| **D-5** | 第一轮遗留 | ⚠️ 中 | R-001 适用范围模糊 | 补充 R-001 说明 |
| **D-6** | 第一轮遗留 | ⚠️ 轻微 | 连接池无文档说明 | 补充到服务定义 |
| **N-6** | 第二轮新增 | ⚠️ 中 | 5005 新增环境变量未在文档列出 | 补充环境变量表 |
| **N-7** | 第二轮新增 | ⚠️ 中 | 5003 /api/stats/push 是否还存在需确认 | 搜索代码确认 |
| **N-8** | 第二轮新增 | ⚠️ 中 | APScheduler graceful shutdown | 改为 wait=True |
| **S-3** | 第一轮遗留 | ⚠️ 中 | 敏感数据可能写入日志 | 改为只记录统计数字 |
| **S-4** | 第一轮遗留 | ⚠️ 轻微 | batch_id 无表类型前缀 | 改为 table_type_uuid |
| **S-5** | 第一轮遗留 | ⚠️ 轻微 | 缺少安全相关环境变量文档 | 补充到环境变量表 |

### 优先修复顺序

```
🔴 高优先级（立即修复）
  1. N-1   ASCII 架构图标题改为 v3.6.8          （ARCHITECTURE.md）
  2. N-4   确认 5003 /api/stats/push 是否存在    （搜索 standalone_dispatch_server.py）
  3. N-7   同上（N-4 的子任务）

⚠️ 中优先级（下一批次）
  4. A-1   删除矛盾的第 6 行                    （ARCHITECTURE.md）
  5. N-2   精简作废内容段落                     （ARCHITECTURE.md）
  6. N-3   补充 stats_smart_sheet 目录状态      （ARCHITECTURE.md）
  7. N-5   补充 cloud_relay.py 内部依赖说明      （ARCHITECTURE.md）
  8. N-6   补充 5005 新增环境变量到文档         （ARCHITECTURE.md）
  9. T-2   增加 by_table metrics                 （cloud_relay.py）
  10. N-8  APScheduler 改为 graceful shutdown    （cloud_relay.py）
  11. D-4  substep_recent limit 提高到 500       （cloud_relay.py）
  12. D-2  JSON 函数容错                        （cloud_relay.py）
  13. D-3  inventory_weekly 增加过滤            （cloud_relay.py）
  14. S-3  日志脱敏                            （cloud_relay.py）

⚠️ 低优先级（下个迭代）
  15. A-2  合并 v3.6.5-proposal 条目            （ARCHITECTURE.md）
  16. A-5  M-4 描述修正                        （ARCHITECTURE.md）
  17. A-8  Phase-3 标题风格统一                 （ARCHITECTURE.md）
  18. T-3  幂等说明补充                        （ARCHITECTURE.md）
  19. T-4  补充 cron 时间表                     （ARCHITECTURE.md）
  20. T-5  MySQL 启动预检                      （cloud_relay.py）
  21. T-6  INVENTORY 环境变量文档              （ARCHITECTURE.md）
  22. D-5  R-001 适用范围说明                   （ARCHITECTURE.md）
  23. D-6  连接池文档说明                       （ARCHITECTURE.md）
  24. S-4  batch_id 加表类型前缀                （cloud_relay.py）
  25. S-5  补充安全环境变量文档                （ARCHITECTURE.md）
```

---

## 五、审计员独立意见

### 架构师（第二轮）：

> v3.6.5 提案内容（N-2）在文档中堆积了 30 行作废标记，严重干扰阅读。当前文档已经比 v3.6.5 复杂得多，应该及时归档历史。**最优先处理 N-1 和 N-2**——这两项不需要改代码，只改文档，但效果显著。另外 N-4（N-7）是本次审计发现的最高风险问题：如果 5003 和 5005 都有 `/api/stats/push`，数据可能重复推送。

### 测试工程师（第二轮）：

> N-8 的 graceful shutdown 问题值得重视。当前 `shutdown(wait=False)` 意味着如果在推送过程中收到 SIGTERM，任务直接中断，下次 cron 重试可以弥补，但中间的 MySQL 连接可能处于不干净状态。更稳妥的做法是 `shutdown(wait=True, cancel_running=False)`——等当前任务完成才退出。另外 N-5（MySQL/APScheduler 依赖未文档化）对测试环境的搭建影响很大，测试人员不知道需要配哪些环境变量。

### 数据库工程师（第二轮）：

> D-4（substep_recent limit=100）经过业务场景分析，实际够用，但建议提高到 500 留安全余量。另外 N-7（确认 5003 的 `/api/stats/push` 是否存在）很关键——如果两处都有，数据库里可能出现重复的统计表记录。**建议先搜索 standalone_dispatch_server.py 确认端点状态，再决定是否需要删除 5003 端点**。

### 安全工程师（第二轮）：

> S-5（环境变量文档缺失）对安全部署影响最大。运维人员不知道 `WECHAT_CLOUD_API_KEY` 是强制要求，不知道不设会直接退出。如果有人在生产服务器上忘记配置 `.env`，cloud_relay.py 启动时会立即报错——这个 fail-fast 设计本身是好的，但需要配套文档说明。另外 N-6 列出的 8 个新增环境变量需要逐一确认哪个是强制哪个是可选，避免生产部署时遗漏。

---

**审计结论**：第一轮 6 项高优先级全部修复 ✅，但文档质量仍有较大提升空间。**最高优先处理 N-1（ASCII 图标题）和 N-4（确认 5003 端点状态）**——前者是门面问题，后者是数据正确性风险。
