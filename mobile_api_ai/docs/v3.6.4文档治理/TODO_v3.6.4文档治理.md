# TODO 清单 - v3.6.4 文档治理（代码问题待下一迭代统一处理）

> **生成时间**: 2026-06-23 22:30
> **任务背景**: v3.6.4 仅修改架构文档，未修改代码。所有代码问题已在 ARCHITECTURE_v3.6.md 顶部"待修改代码清单"段落中详细标注，本文件提供独立 TODO 清单便于追踪。

## 优先级 P0（必须修复，3 项待处理）

| # | 任务 | 位置 | 修复方案 | 预估工作量 | 依赖项 |
|---|------|------|----------|:----------:|--------|
| 1 | **修复 SQL 占位符错误** | `models/order.py:688` | `?` → `%s`（PyMySQL 规范） | 5 分钟 | 无 |
| 2 | **新增 DLQ retry worker** | `dispatch_center/_reconcile.py` | 新增 `start_dlq_retry_worker()` 函数，扫描 `dlq` 表 + 文件双写，指数退避（1s→2s→4s→8s→16s） | 4-6 小时 | 无 |
| 3 | **拆分 _core.py 单文件 1441 行** | `dispatch_center/_core.py` | 拆分为 `_core_sync.py`（同步逻辑）+ `_core_emit.py`（事件发射）+ `_core_query.py`（查询路由） | 6-8 小时 | 2（DLQ worker） |
| 4 | **注册 DLQ retry worker 启动钩子** | `dispatch_center/__init__.py` | 在服务启动时调用 `start_dlq_retry_worker()` | 30 分钟 | 2 |

## 优先级 P1（建议修复，4 项待处理）

| # | 任务 | 位置 | 修复方案 | 预估工作量 | 依赖项 |
|---|------|------|----------|:----------:|--------|
| 5 | **统一 1.6 节同步端点路径风格** | ARCHITECTURE_v3.6.md 1.6 节 | `/sync/xxx` → `/api/dispatch-center/sync/xxx`（与 1.8 节保持一致） | 10 分钟（仅文档） | 无 |
| 6 | **为 R-001 违规加 TODO 注释** | `models/order.py` 跨库 JOIN 段 | `# TODO(违反R-001, 待重构): 跨库JOIN应通过API调用, 当前保留以便排查` | 5 分钟 | 无 |
| 7 | **删除废弃文件** | `desktop_container_integration.py` | 删除或重命名为 `desktop_container_integration.py.bak` | 10 分钟 | 需先确认无引用（建议先用 `Grep` 工具扫描） |
| 8 | **修复裸异常日志无堆栈** | `dispatch_center/_core.py` 多个 `except` | `logger.error(...)` → `logger.exception(...)` 或 `logger.error(..., exc_info=True)` | 1-2 小时 | 无 |

## 阻塞项 / 风险点

| # | 风险 | 说明 | 缓解措施 |
|---|------|------|----------|
| 1 | P0-2（DLQ retry worker）实现复杂度 | 需要扫描 MySQL dlq 表 + 文件双写 + 指数退避，建议先小范围测试 | 实现后用 1-2 个真实失效事件验证重试链路 |
| 2 | P0-3（_core.py 拆分）影响面大 | 1441 行代码涉及同步/发射/查询三块，需先梳理函数依赖 | 拆分前用 `Grep` 工具列出所有 import 关系，按依赖图拆分 |
| 3 | P0-4（SQL 占位符）影响范围待评估 | `?` 占位符可能是 SQLAlchemy ORM 调用而非 PyMySQL 原生 | 修改前先确认 line 688 上下文（是 `cursor.execute()` 还是 `session.query()`） |
| 4 | Q-B6（删除废弃文件）需先确认无引用 | `desktop_container_integration.py` 可能被旧代码引用 | 删除前用 `Grep "desktop_container_integration" -r .` 扫描 |

## 待办处理顺序（建议）

```
P0-4 (5min)
   │
   ▼
P0-2 (4-6h) ──► P0 注册 (30min)
   │
   ▼
P0-3 (6-8h)
   │
   ▼
Q-B7 (1-2h) ──► Q-B2 (5min) ──► Q-B6 (10min)
   │
   ▼
Q-B1 (10min, 文档)
   │
   ▼
更新 ARCHITECTURE_v3.6.md 待修改代码清单（标记已闭环）
```

## 处理完代码后必做事项

- [ ] **更新 ARCHITECTURE_v3.6.md 顶部"待修改代码清单"**：将对应行的"⏳ 待处理"改为"✅ 已闭环"
- [ ] **更新修订历史**：从 v3.6.4 升到 v3.6.5，记录代码处理内容
- [ ] **重启所有服务**：5002/5003/5008/8008/桌面端
- [ ] **回归测试**：T11-T14 emit_invalidate 全链路 + 排产同步 + 归档 SLA
- [ ] **生成新的完成度报告**：`docs/v3.6.5代码治理/ACCEPTANCE_v3.6.5代码治理.md`
- [ ] **业务影响报告**：`docs/v3.6.5代码治理/IMPACT_v3.6.5代码治理.md`

## 关联文档

- [ARCHITECTURE_v3.6.md](file:///d:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/docs/ARCHITECTURE_v3.6.md)（v3.6.4 顶部含完整待修改代码清单）
- [ACCEPTANCE_v3.6.4文档治理.md](file:///d:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/docs/v3.6.4%E6%96%87%E6%A1%A3%E6%B2%BB%E7%90%86/ACCEPTANCE_v3.6.4%E6%96%87%E6%A1%A3%E6%B2%BB%E7%90%86.md)
- [IMPACT_v3.6.4文档治理.md](file:///d:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/docs/v3.6.4%E6%96%87%E6%A1%A3%E6%B2%BB%E7%90%86/IMPACT_v3.6.4%E6%96%87%E6%A1%A3%E6%B2%BB%E7%90%86.md)
- [PROJECT_ITERATION_RULES.md](file:///d:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/PROJECT_ITERATION_RULES.md)（R-000 ~ R-243）
- [project_rules.md](file:///d:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/.trae/rules/project_rules.md)（IDE 自动加载版本）

---

**清单维护人**: AI 助手
**最后更新**: 2026-06-23 22:30
**下次更新时机**: 处理完代码问题后，更新 ARCHITECTURE_v3.6.md 顶部清单的"决议"列
