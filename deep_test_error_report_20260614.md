# 调度中心深度测试 - 完整错误报告

## 测试时间
- 北京时间：2026-06-14 23:55 ~ 00:05
- 测试方式：网页触发所有功能页面

---

## 一、服务器状态

| 端口 | 服务 | 状态 |
|------|------|------|
| 5002 | 容器中心 | ✅ 运行中 |
| 5003 | 调度中心 | ✅ 运行中 |
| 5008 | 报工程序 | ✅ 运行中 |
| 5010 | 库存管理 | ✅ 运行中 |
| 8008 | Sync Bridge | ✅ 运行中 |

---

## 二、测试的功能页面

| 页面 | URL | 结果 |
|------|-----|------|
| 调度中心主页 | /api/dispatch-center/ | ✅ 正常 |
| 排班 | /api/schedule | ❌ 404 |
| 工单 | /api/workorder | ❌ 404 |
| 同步状态 | /api/sync/status | ❌ 404 |
| 可视化配置中心 | /api/config-center | ✅ 正常 |
| 文档 | /api/dispatch-center/documents | ⚠️ 待验证 |
| Dashboard | /api/dispatch-center/dashboard | ❌ 404 |
| 健康检查 | /api/dispatch-center/health | ❌ 404 |
| 同步订单 | /api/sync/orders | ❌ 404 |
| 同步容器 | /api/sync/containers | ❌ 404 |
| 同步生产 | /api/sync/production | ❌ 404 |
| 查询任务 | /api/dispatch-center/query_tasks | ❌ 404 |
| 同步操作员 | /api/sync/operators | ❌ 404 |
| 状态 | /api/dispatch-center/status | ⚠️ 待验证 |

---

## 三、发现的错误（按严重程度）

### 🔴 CRITICAL - 路由未注册 (11个)

| # | 错误 | 影响 |
|---|------|------|
| 1 | `[404] GET /api/schedule` | 排班功能不可用 |
| 2 | `[404] GET /api/workorder` | 工单功能不可用 |
| 3 | `[404] GET /api/sync/status` | 同步状态不可用 |
| 4 | `[404] GET /api/dispatch-center/dashboard` | Dashboard 不可用 |
| 5 | `[404] GET /api/dispatch-center/health` | 健康检查不可用 |
| 6 | `[404] GET /api/sync/orders` | 订单同步不可用 |
| 7 | `[404] GET /api/sync/containers` | 容器同步不可用 |
| 8 | `[404] GET /api/sync/production` | 生产同步不可用 |
| 9 | `[404] GET /api/dispatch-center/query_tasks` | 查询任务不可用 |
| 10 | `[404] GET /api/sync/operators` | 操作员同步不可用 |
| 11 | `[404] GET /api/dispatch-center/list_tasks` | 列表任务不可用 |

### 🟠 HIGH - ETL 本地镜像同步失败 (5个)

| # | 错误 | 影响 |
|---|------|------|
| 1 | `orders → orders_local 连续失败` | 订单同步失败 |
| 2 | `production_orders → production_orders_local 连续失败` | 生产订单同步失败 |
| 3 | `violation_log → violations_local 连续失败` | 违规日志同步失败 |
| 4 | `process_records → process_records_local 连续失败` | 工序记录同步失败 |
| 5 | `work_orders → work_orders_local 连续失败` | 工单同步失败 |

**根本原因**：`cannot import name 'STEELBELT_MYSQL_CFG' from 'core.config'`

### 🟡 MEDIUM - 审计日志写入失败

| # | 错误 | 影响 |
|---|------|------|
| 1 | `[G2 硬删除] orders → orders_local 失败: No module named 'utils.trace'` | 硬删除审计失败 |
| 2 | `[G2 硬删除] violation_log → violations_local 失败: No module named 'utils.trace'` | 违规日志审计失败 |
| 3 | `[G2 硬删除] production_orders → production_orders_local 失败: No module named 'utils.trace'` | 生产订单审计失败 |
| 4 | `[G2 硬删除] process_records → process_records_local 失败: No module named 'utils.trace'` | 工序记录审计失败 |
| 5 | `[G2 硬删除] work_orders → work_orders_local 失败: No module named 'utils.trace'` | 工单审计失败 |
| 6 | `[OUTBOX] 处理失败: No module named 'utils.trace'` | OUTBOX 处理失败 |

### 🟢 LOW - 警告（不影响核心功能）

| # | 警告 | 说明 |
|---|------|------|
| 1 | `[TRACE] 5003 注册中间件失败: No module named 'utils.trace'` | trace 中间件注册失败 |
| 2 | `[ETL] violation_log → violations_local 失败 (连续 N 次)` | ETL 同步重试中 |

---

## 四、错误根因分析

### 4.1 404 路由问题

**原因**：蓝图中注册了路由，但 Flask 应用没有正确注册蓝图

**检查**：
- `dispatch_server.py` 中是否注册了 `schedule_bp`、`workorder_bp`、`sync_bp`
- 检查蓝图注册顺序

### 4.2 STEELBELT_MYSQL_CFG 问题

**原因**：
1. 配置已添加到 `core/_config_infra.py`
2. 但 5002 容器中心服务器可能没有重启
3. 或者导入路径不正确

### 4.3 utils.trace 问题

**原因**：
1. `mobile_api_ai/utils/trace.py` 存在
2. 但导入时找不到模块
3. sys.path 设置问题

---

## 五、修复建议

### 5.1 路由注册问题

**检查文件**：`mobile_api_ai/dispatch_server.py`

```python
# 应该有以下注册代码：
app.register_blueprint(schedule_bp, url_prefix='/api/schedule')
app.register_blueprint(workorder_bp, url_prefix='/api/workorder')
app.register_blueprint(sync_bp, url_prefix='/api/sync')
```

### 5.2 ETL 配置问题

**建议**：重启 5002 容器中心服务器

### 5.3 utils.trace 问题

**建议**：进一步检查导入路径

---

## 六、错误汇总统计

| 错误类型 | 数量 | 严重程度 |
|---------|------|---------|
| 404 路由未注册 | 11 | 🔴 CRITICAL |
| ETL 同步失败 | 5 | 🟠 HIGH |
| 审计日志失败 | 6 | 🟡 MEDIUM |
| trace 中间件 | 1 | 🟢 LOW |
| **总计** | **23** | |

---

## 七、修复优先级

| 优先级 | 问题 | 操作 |
|--------|------|------|
| P0 | 404 路由 | 检查蓝图注册 |
| P0 | ETL 配置 | 重启 5002 服务器 |
| P1 | utils.trace | 检查导入路径 |
| P2 | 审计日志 | 修复 trace 后自动恢复 |

---

## 八、测试截图

- `dispatch_01_main.png` - 调度中心主页
- `dispatch_center_main.png` - 操作员列表
- `tasks_page.png` - 任务页面

