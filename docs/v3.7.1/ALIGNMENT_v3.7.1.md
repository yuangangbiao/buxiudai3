# ALIGNMENT v3.7.1 - DLQ 单元测试 + Q-B6/B7 清理

> **版本**: v3.7.1 | **日期**: 2026-06-25
> **来源**: [v3.7.0 TODO_v3.7.1.md](../v3.7.0/TODO_v3.7.1.md)

---

## 1. 任务范围（明确）

| 任务 | 来源 | 风险 | 价值 | 决策 |
|------|------|:----:|:----:|:----:|
| DLQ retry 单元测试 | P0-2 增强 | 🟢 低 | 🔴 高 | ✅ 实施 |
| Q-B7 清理 40 处裸异常日志 | Q-B7 | 🟡 中 | 🔴 高 | ✅ 实施 |
| Q-B6 迁移 7 引用方 | Q-B6 | 🟠 中高 | 🟡 中 | ✅ 分步实施 |
| Q-B1 路径统一 | Q-B1 | 🔴 高 | 🟡 中 | ⏸️ 延后 |
| Q-B2 R-001 跨库 | Q-B2 | 🔴 高 | 🟡 中 | ⏸️ 延后 |
| L4 业务场景测试 | 路线图 | 🟢 低 | 🟡 中 | ✅ 实施 |

**调整**: Q-B1/Q-B2 涉及业务逻辑改动，本次不实施，避免高风险。

---

## 2. T1 DLQ retry 单元测试

### 输入契约
- 已有 `_dlq_retry.py`（v3.7.0 实现）
- 无前置依赖

### 输出契约
- `tests/unit/dispatch_center/test_dlq_retry.py`
- 覆盖：start/stop、指数退避、poison 标记、消息 sender 注入
- 验收：pytest 100% 通过，0 真实 DB 连接

---

## 3. T2 Q-B7 清理 40 处裸异常日志

### 现状（v3.7.0 收口后）
- 45 处裸异常日志
- 已修 5 处
- 剩余 40 处

### 范围
- 优先级 1: 写入路径（高风险）
- 优先级 2: 对外 API 路径（高曝光）
- 优先级 3: 内部函数

### 验收
- 至少清理 15+ 处
- 全部修改后 grep 验证

---

## 4. T3 Q-B6 迁移 7 引用方

### 7 引用方
1. `auto_publish_service.py`
2. `container_event_listener.py`
3. `manual_publish_service.py`
4. `material_publish_service.py`
5. `task_recall_service.py`
6. `scripts/process_view_integration_example.py`
7. `tests/modular/test_desktop_container.py`

### 迁移策略
- **不一次性删除** `desktop_container_integration.py`
- 每个引用方逐个迁移到 `mobile_api_ai/dispatch_center` 对应 publisher
- 迁移完成后，再删除 `desktop_container_integration.py`

### 验收
- 7 引用方全部迁移
- `desktop_container_integration.py` 删除
- 编译 + 现有测试通过

---

## 5. T4 L4 业务场景测试

### 范围
- 紧急订单（紧急程度 HIGH）
- 多用户并发（同一订单被多人操作）
- 外勤场景（网络不稳定）

### 验收
- 3 个 L4 测试文件
- pytest 可收集 + 全部通过

---

## 6. 时间安排

| 任务 | 工作量 | 计划 |
|------|:------:|------|
| T1 DLQ 单元测试 | 2h | 立即 |
| T2 Q-B7 清理 | 2h | 立即 |
| T3 Q-B6 迁移 | 1天 | 立即 |
| T4 L4 场景 | 1天 | 立即 |
| 文档 + 验收 | 30min | 收尾 |

**总工作量**: 1.5 天

---

**下一阶段**: 实施 T1-T4
