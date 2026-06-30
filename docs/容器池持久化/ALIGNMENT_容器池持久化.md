# ALIGNMENT_容器池持久化.md

## 任务名称
容器池持久化

---

## 一、项目和任务特性规范

### 1.1 项目概述

| 项目 | 内容 |
|------|------|
| 项目名称 | 不锈钢网带跟单系统3.0 - 移动端报工模块 |
| 任务名称 | 容器池持久化 |
| 任务日期 | 2026-05-02 |
| 当前阶段 | 需求对齐 |

### 1.2 系统现状分析

#### 1.2.1 当前容器池实现

项目中存在**两套**容器池实现：

| 实现 | 文件 | 存储方式 | 用途 |
|------|------|---------|------|
| **TaskPool** | [container/tasks_pool.py](file:///d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container\task_pool.py) | **内存存储** | API服务器 (container_api_server.py) 使用 |
| **ContainerCenter** | [container_center_v5.py](file:///d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center_v5.py) | **SQLite持久化** | 企业微信机器人、移动端API使用 |

#### 1.2.2 TaskPool 问题

```python
# container/tasks_pool.py 第238行
task_pool = TaskPool()  # 内存存储，重启后数据丢失！
```

**问题清单**：
1. 任务存储在内存字典 `self.tasks: Dict[str, Task]` 中
2. 服务重启后所有任务丢失
3. 未实现与 storage_layer.py 的集成
4. 无任务索引持久化

#### 1.2.3 ContainerCenter 现状

```python
# container_center_v5.py 第463-473行
class ContainerCenter:
    def __init__(self, storage_config: Dict = None):
        if storage_config is None:
            storage_config = {'type': 'sqlite', 'db_path': 'container_center.db'}
        self.storage = create_storage(storage_config)  # ✅ SQLite持久化
```

**已实现功能**：
- ✅ SQLite持久化
- ✅ 存储抽象层 (storage_layer.py)
- ✅ 数据收集、分发、分析
- ✅ 回写桌面端机制

---

## 二、原始需求

> **用户需求**：完成容器池持久化

**需求解读**：
1. TaskPool 当前使用内存存储，需要改为 SQLite 持久化
2. 确保服务重启后任务数据不丢失
3. 复用现有 storage_layer.py 存储抽象层

---

## 三、边界确认（明确任务范围）

### 3.1 本次任务范围

| 项目 | 说明 |
|------|------|
| **修改文件** | `mobile_api_ai/container/task_pool.py` |
| **新增文件** | 无 |
| **依赖组件** | `storage_layer.py` (已有) |

### 3.2 任务目标

1. **核心目标**：TaskPool 支持 SQLite 持久化
2. **数据不丢失**：服务重启后任务自动恢复
3. **复用设施**：使用已有 `create_storage()` 和 `SQLiteStorage`

### 3.3 边界限制

- 不修改 ContainerCenter (已有持久化)
- 不修改 API 接口契约
- 不修改 Task 数据结构
- 不影响现有 API 服务器运行

---

## 四、需求理解（对现有项目的理解）

### 4.1 架构理解

```
┌─────────────────────────────────────────────────────────────────┐
│                    移动端/企业微信                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│              container_api_server.py (端口5002)                   │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │           TaskPool (内存存储 ❌ 重启丢失)                  │   │
│   │  - add_task()                                           │   │
│   │  - get_task()                                           │   │
│   │  - assign_task() / complete_task()                      │   │
│   └─────────────────────────────────────────────────────────┘   │
│                            ↑                                     │
│                   container/task_pool.py                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
    ┌─────────▼─────────┐       ┌──────────▼──────────┐
    │ ContainerCenter │       │   SQLiteStorage    │
    │ (container_      │       │  (storage_layer.py)│
    │  center_v5.py)   │       │  ✅ 已有持久化       │
    └─────────────────┘       └─────────────────────┘
```

### 4.2 依赖关系

| 组件 | 关系 | 说明 |
|------|------|------|
| `storage_layer.py` | 被依赖 | 提供 SQLiteStorage |
| `container/task_pool.py` | 待修改 | 集成存储层 |
| `container/__init__.py` | 无变更 | 导出接口 |
| `container_api_server.py` | 无变更 | API接口不变 |

---

## 五、技术约束与规范

### 5.1 代码规范遵循

根据 [CODING_STANDARDS.md](file:///d:\yuan\不锈钢网带跟单3.0\CODING_STANDARDS.md)：

| 规范项 | 要求 |
|--------|------|
| 敏感信息 | 不允许硬编码路径、密码 |
| 路径管理 | 使用统一配置获取路径 |
| 异常处理 | 必须使用 `except Exception as e:` 并记录日志 |
| 日志记录 | 必须使用 `logger = logging.getLogger(__name__)` |

### 5.2 数据库表设计

沿用 storage_layer.py 的 `data_packages` 表结构：

```sql
CREATE TABLE IF NOT EXISTS data_packages (
    id TEXT PRIMARY KEY,
    data_type TEXT NOT NULL,
    title TEXT,
    content TEXT,
    source TEXT,
    priority TEXT,
    status TEXT,
    created_at TEXT,
    distributed_at TEXT,
    acknowledged_at TEXT,
    last_reminded_at TEXT,
    completed_at TEXT,
    target_operator TEXT,
    target_device TEXT,
    tags TEXT,
    related_order TEXT,
    related_process TEXT
);
```

### 5.3 接口契约

TaskPool 对外接口保持不变：

| 方法 | 说明 | 变更 |
|------|------|------|
| `add_task(task)` | 添加任务 | 内部持久化 |
| `get_task(task_id)` | 获取任务 | 内部持久化 |
| `get_tasks_by_type(...)` | 获取任务列表 | 内部持久化 |
| `get_pending_tasks(...)` | 获取待处理任务 | 内部持久化 |
| `assign_task(...)` | 分配任务 | 内部持久化 |
| `start_task(...)` | 开始任务 | 内部持久化 |
| `complete_task(...)` | 完成任务 | 内部持久化 |
| `cancel_task(...)` | 取消任务 | 内部持久化 |
| `get_pool_status()` | 获取状态 | 内部持久化 |

---

## 六、实现方案

### 6.1 方案选择

**推荐方案**：改造 TaskPool 使用存储抽象层

**理由**：
1. 最小改动 - 只需修改 TaskPool 内部实现
2. 复用已有 SQLiteStorage
3. 不影响 API 接口
4. 便于未来迁移到 Redis

### 6.2 改造要点

```python
# 修改前
class TaskPool:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}  # 内存存储

# 修改后
class TaskPool:
    def __init__(self, storage: BaseStorage = None):
        self.storage = storage or create_storage({'type': 'sqlite', 'db_path': 'task_pool.db'})
        self.tasks: Dict[str, Task] = {}  # 内存缓存 + 持久化
```

### 6.3 数据加载/保存策略

| 操作 | 策略 |
|------|------|
| 初始化 | 从 SQLite 加载所有任务到内存 |
| add_task | 内存保存 + 立即持久化 |
| 状态变更 | 立即持久化 |
| 查询 | 读内存（快速） |

---

## 七、疑问澄清

### 7.1 已识别问题

| 问题 | 决策 |
|------|------|
| 是否需要迁移已有数据？ | **暂不需要** - TaskPool 当前为内存存储，无历史数据 |
| 是否需要支持 Redis？ | **未来可选** - 当前只实现 SQLite |
| 是否需要修改 container_api_server.py？ | **不需要** - 只需修改 TaskPool 内部实现 |

### 7.2 假设确认

1. ✅ TaskPool 重启后从 SQLite 恢复任务
2. ✅ 任务索引在内存中维护，定期同步
3. ✅ 使用 `task_pool.db` 作为默认数据库名
4. ✅ 沿用 storage_layer.py 的表结构

---

## 八、质量门控

### 8.1 验收标准

| 编号 | 标准 | 测试方法 |
|------|------|---------|
| V1 | TaskPool 初始化时从 SQLite 加载任务 | 重启服务后验证任务存在 |
| V2 | add_task 后任务持久化到 SQLite | 添加任务后查询数据库 |
| V3 | 状态变更后 SQLite 数据同步更新 | 完成/取消任务后查询数据库 |
| V4 | 服务重启后任务数量和状态正确 | 重启前后对比 |
| V5 | 不影响现有 API 接口调用 | 调用现有接口验证 |
| V6 | 异常情况下日志正确记录 | 模拟异常场景 |

### 8.2 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 数据库文件损坏 | 低 | SQLite 有自动恢复机制 |
| 并发写入冲突 | 低 | SQLite 支持 WAL 模式 |
| 迁移间隙数据丢失 | 低 | 立即持久化策略 |

---

## 九、后续迭代建议

本次为**基础持久化**，后续可迭代：

1. **性能优化**：批量写入、定期同步
2. **Redis支持**：使用 Redis 作为分布式存储
3. **监控告警**：任务超时、失败告警
4. **统计分析**：任务完成率、工时统计

---

**文档版本**：v1.0
**创建日期**：2026-05-02
**状态**：待审批
