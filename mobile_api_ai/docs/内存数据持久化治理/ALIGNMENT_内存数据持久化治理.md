# ALIGNMENT - 内存数据持久化治理

## 原始需求

将 `api/quality.py`、`api/approval.py`、`api/message.py`、`api/ai.py` 四个模块中的**内存列表/字典数据**迁移到数据库持久化存储，确保服务重启后数据不丢失，且支持多实例共享数据。

## 项目特性规范对齐

### 技术栈
- **数据库后端**: 同时支持 MySQL 和 SQLite（用 `USE_SQLITE` 环境变量切换）
- **数据库连接**: `from core.database import get_db_cursor` → 返回 `(SafeCursor, conn)`
- **自动建表**: `SafeCursor` 包装类在 INSERT/UPDATE 时自动检测表/列是否存在并自动创建
- **响应格式**: 通过 `api/decorators.py` 的 `success()` / `fail()` 或 `api/auth.py` 的 `success()` / `fail()` 统一返回

### 现有参考模式
`api/process.py` 是已正确使用数据库的参考模块：
1. 用 `bp.record_once()` 注册 `_ensure_tables()` 回调建表
2. 所有数据操作通过 `with get_db_cursor() as (cursor, conn):` 执行
3. 异常用 `logger.exception()` 记录完整 traceback

### 代码约定
- 统一使用 `from core.database import get_db_cursor`（模块级 import）
- 统一使用 `from decorators import success, fail`（quality.py 应改用 decorators.py 而非 auth.py）
- 表名统一以 `mobile_` 为前缀（如 `mobile_quality_records`）

## 各模块现状分析

### 1. quality.py — QUALITY_RECORDS（L14）
- 内存变量：`QUALITY_RECORDS = [...]`、`_next_id = 3`
- 端点：
  - `GET /api/quality/list` → 列出所有质检记录
  - `POST /api/quality/<order_id>/create` → 创建质检记录（联动调度中心）
  - `GET /api/quality/types` → 返回类型枚举（静态数据）
- 联动逻辑：创建质检记录后调用 `dispatch_center.on_quality_record_completed()` 更新流程状态
- 当前问题：使用 `from .auth import success, fail` 而非 `decorators`

### 2. approval.py — APPROVALS（L10）
- 内存变量：`APPROVALS = [...]`
- 端点：
  - `GET /api/approval/pending` → 待审批列表
  - `POST /api/approval/<id>/approve` → 通过审批
  - `POST /api/approval/<id>/reject` → 拒绝审批（含拒绝原因）
  - `GET /api/approval/history` → 审批历史（当前返回空列表）
- 数据字段：{id, type, order_no, reason, requester, request_time, status, approver, approve_time, reject_reason, reject_time}

### 3. message.py — MESSAGES（L10）
- 内存变量：`MESSAGES = [...]`
- 端点：
  - `GET /api/message/list` → 用户消息列表（含未读计数）
  - `GET /api/message/unread-count` → 未读消息数
  - `POST /api/message/<id>/read` → 标记已读
- 数据字段：{id, receiver_id, title, content, type, is_read, create_time}

### 4. ai.py — ORDERS（L12）、PROCESS_RECORDS（L18）
- 内存变量：`ORDERS = [...]`、`PROCESS_RECORDS = [...]`
- 端点：
  - `POST /api/ai/speech-to-report` → 语音解析（纯逻辑，无需持久化）
  - `POST /api/ai/image-analysis` → 图像分析（模拟，无需持久化）
  - `POST /api/ai/chat` → AI 对话（从内存 ORDERS/PROCESS_RECORDS 查询订单进度）
  - `GET /api/ai/chat/history` → 对话历史（当前返回硬编码数据）
- 核心问题：AI 对话查询订单进度从**内存硬编码数据**读取，应改为从真实数据库表（`mobile_orders`、`mobile_task_records`）查询
- 附加问题：chat_history 端点返回硬编码数据，应存储到数据库

## 边界确认

### 纳入范围
- quality.py 的 QUALITY_RECORDS 迁移到 `mobile_quality_records` 表
- approval.py 的 APPROVALS 迁移到 `mobile_approvals` 表
- message.py 的 MESSAGES 迁移到 `mobile_messages` 表
- ai.py 的 ORDERS/PROCESS_RECORDS 替换为从真实数据库查询
- ai.py 新增 `mobile_chat_history` 表存储对话历史

### 不纳入范围
- 不重构响应格式或接口签名
- 不改动现有 API 路由路径
- 不修改 dispatch_center.py 的联动逻辑
- 不涉及前端页面改动
- 不修改 auth.py 的 OPERATORS（内存数据，不属于本任务范围）

## 验收标准

1. 所有 4 个模块的数据 CRUD 操作通过 MySQL/SQLite 双后端均可正常工作
2. 服务重启后之前创建的数据不会丢失
3. 所有异常路径有 `logger.exception()` 记录
4. 现有 API 响应格式（code/message/data）保持不变
5. 每个模块的端点功能与原实现完全一致
6. ai.py 的订单进度查询能正确返回数据（即使数据库为空也应有合理空响应）
