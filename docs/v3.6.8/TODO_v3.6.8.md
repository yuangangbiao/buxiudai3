# TODO - v3.6.8 架构重构 + 扫尾

> **版本**: v1.0
> **创建时间**: 2026-06-24
> **项目**: 不锈钢网带跟单 3.0 v3.6.8

---

## 1. 新增任务（本会话发现）

| # | 任务 | 描述 | 优先级 | 估算 |
|---|------|------|:------:|------|
| N-1 | 5005 接管 9 张报表定时任务 | 将 APScheduler 定时任务从 5003 迁移到 5005（cloud_relay.py 内部），实现"定时器+导出+推送"全在 5005，5003 不再感知统计表 | 🔴 P0 | ~8h | ✅ 已完成（含 6 项高优先级审计修复：S-1/S-2/D-1/A-3/A-6/T-1） |

**N-1 详细说明**：
- 现状：`standalone_dispatch_server.py:5003` 内 `register_scheduler()` 启动 APScheduler → 调 `smart_sheet_exporter.py` → 调 `smart_sheet_client.py` → 调 `cloud_relay.py:5005`
- 理想：`cloud_relay.py:5005` 内部自己管 APScheduler + 9 张表导出 + 推送，全在一个服务内
- 数据流（改造后 2 跳）：`cloud_relay.py:5005` → 云端 `5004` → 微信智能表格
- 涉及文件：`smart_sheet_exporter.py`、`smart_sheet_client.py`、`stats_smart_sheet/db_queries.py`、`stats_smart_sheet/config.py` 迁移进 `cloud_relay.py`
- 清理项：5003 内 `register_scheduler` 调用可移除（如果不再需要）

---

## 2. 待完成项（来自 v3.6.7 遗留）

### 2.1 2 刀架构遗留（4 项）

| # | 漏洞 | 描述 | 优先级 | 估算 |
|---|------|------|:------:|------|
| P0-A3 | _core.py 10 处直连 | `_core.py` 直连 `container_center` 数据库 → 改为 HTTP 调用 | 🔴 P0 | ~6h |
| P0-A4 | models/order.py 跨库写 | `models/order.py:52-103` 跨库写 `container_center.process_records` → 改为 HTTP | 🔴 P0 | ~4h |
| P0-A6 | cloud_router_service.py | 云端服务代码，不动 | 🟢 无 | — |
| P0-A2 | 删除 3 文件 | cloud_relay.py 已改造；cloud_router_service.py 云端不动；start_cloud_relay.bat 保留 | 🟢 已完成 | — |

**P0-A3 详细说明**：
- 位置：`_core.py` 约 10 处直接 `cursor.execute(sql)` 访问 `container_center` 数据库
- 修复方案：改为调 `container_center_api.py` 的 HTTP 端点
- 涉及端点：`/api/internal/container_center/{table}/query`

### 2.2 3 刀测试遗留（7 项）

| # | 漏洞 | 描述 | 优先级 | 估算 |
|---|------|------|:------:|------|
| P0-T1 | 4 端点单测 | v3.6.5 新增 `/api/container-center/*` 等 4 个端点无单元测试 | 🔴 P0 | ~8h |
| P0-T3 | DLQ retry worker | DLQ retry worker 缺失（从未启动） | 🔴 P0 | ~8h |
| P0-T4 | 告警 11 类 | 告警 11 类检测完全无单元测试 | 🟡 P1 | ~8h |
| P0-T6 | 工序报工对账 | 工序报工"对账兜底"机制（1.5.1）无测试 | 🟡 P1 | ~6h |
| P0-T7 | 企微 3 渠道 | 企业微信 3 类发送渠道无任何测试 | 🟡 P1 | ~4h |
| P0-T9 | 5003 降级 | 5003 不可用时降级无故障注入测试 | 🟡 P1 | ~4h |
| P0-T2 | 9 统计表单测 | 9 张统计表 APScheduler 迁移后无测试 | 🟡 P1 | ~6h |

**P0-T5 和 P0-T8 已在 v3.6.7 完成 ✅**

### 2.3 暂缓包（按用户决策延后）

| # | 漏洞 | 风险等级 | 说明 |
|---|------|:--------:|------|
| P0-S1 | 明文密码 | 🔴 P0 | admin/123456 数据库明文存储 |
| P0-S2 | 密码强度 | 🟡 P1 | 无复杂度要求 |
| P0-S3 | 密码轮换 | 🟡 P1 | 长期不轮换 |

**状态**：DBA 24h 内修改 admin 密码（运维待办）

---

## 3. 汇总

| 分类 | 项数 | 总估算工时 |
|------|:----:|----------:|
| 新增任务 | 1 | ~8h |
| 2 刀架构遗留 | 2 | ~10h |
| 3 刀测试遗留 | 7 | ~36h |
| **合计** | **10** | **~54h** |

---

## 4. 建议执行顺序

```
1. N-1  5005 接管 9 表定时任务（架构重构，~8h）
2. P0-A3 _core.py 直连改 HTTP（~6h）
3. P0-A4 order.py 跨库写改 HTTP（~4h）
4. P0-T1 4 端点单测（~8h）
5. P0-T3 DLQ retry worker（~8h）
6. P0-T2 9 统计表单测（~6h）
7. P0-T4 告警 11 类（~8h）
8. P0-T6 工序报工对账（~6h）
9. P0-T7 企微 3 渠道（~4h）
10. P0-T9 5003 降级（~4h）
```

---

**更新人**：AI 团队
**下次更新**：v3.6.8 启动后
