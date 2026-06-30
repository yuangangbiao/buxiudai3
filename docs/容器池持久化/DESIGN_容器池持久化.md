# DESIGN_容器池持久化.md

## 任务名称
容器池持久化

---

## 一、整体架构图

### 1.1 架构演进

**改造前（内存存储）**：
```
┌─────────────────────────────────────────┐
│       container_api_server.py           │
│                                         │
│   task_pool = TaskPool()  ← 内存存储    │
│   ├── tasks: Dict[str, Task]           │
│   └── task_index: Dict                  │
│          ↓                               │
│      服务重启 → 数据丢失 ❌               │
└─────────────────────────────────────────┘
```

**改造后（SQLite持久化）**：
```
┌─────────────────────────────────────────┐
│       container_api_server.py           │
│                                         │
│   task_pool = TaskPool()                │
│   ├── tasks: Dict[str, Task]  ← 内存缓存 │
│   ├── task_index: Dict      ← 内存索引   │
│   └── storage: BaseStorage   ← SQLite   │
│          ↓                               │
│      ┌───────────────────┐              │
│      │  SQLiteStorage    │              │
│      │  (storage_layer)  │              │
│      │  task_pool.db     │              │
│      └───────────────────┘              │
│          ↓                               │
│      服务重启 → 数据恢复 ✅               │
└─────────────────────────────────────────┘
```

### 1.2 数据流向图

```
┌────────────────────────────────────────────────────────────────────┐
│                         TaskPool 持久化数据流                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 初始化 (load_from_storage)                                      │
│  ┌──────────────┐      ┌─────────────────┐      ┌──────────────┐ │
│  │  task_pool.db │ ───→ │  SQLiteStorage  │ ───→ │  self.tasks  │ │
│  │  (持久化)      │      │  (load_packages)│      │  (内存)       │ │
│  └──────────────┘      └─────────────────┘      └──────────────┘ │
│                                                                     │
│  2. 添加任务 (add_task)                                            │
│  ┌──────────────┐      ┌─────────────────┐                        │
│  │  Task 对象   │ ───→ │  self.tasks[id] │                        │
│  │              │      │  save_package()  │ ────→ task_pool.db     │
│  └──────────────┘      └─────────────────┘                        │
│                                                                     │
│  3. 状态变更 (assign/start/complete/cancel)                        │
│  ┌──────────────┐      ┌─────────────────┐                        │
│  │  task.status │ ───→ │  save_package() │ ────→ task_pool.db     │
│  └──────────────┘      └─────────────────┘                        │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 二、分层设计和核心组件

### 2.1 组件关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                      container/task_pool.py                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    TaskPool                              │   │
│   │  ┌─────────────────────────────────────────────────┐    │   │
│   │  │  __init__(storage_config)                        │    │   │
│   │  │  ├── self.storage = create_storage(config)       │    │   │
│   │  │  ├── self.tasks = {}        # 内存缓存            │    │   │
│   │  │  ├── self.task_index = {}   # 内存索引            │    │   │
│   │  │  └── load_from_storage()    # 启动时加载          │    │   │
│   │  └─────────────────────────────────────────────────┘    │   │
│   │                                                          │   │
│   │  公共方法:                                                │   │
│   │  ├── add_task(task)          → save_to_storage()        │   │
│   │  ├── assign_task(id, op_id)  → save_to_storage()        │   │
│   │  ├── start_task(id)          → save_to_storage()        │   │
│   │  ├── complete_task(id, result)→ save_to_storage()       │   │
│   │  ├── cancel_task(id, reason)  → save_to_storage()        │   │
│   │  ├── remove_task(id)          → delete_from_storage()    │   │
│   │  └── get_pool_status()        → 返回统计信息             │   │
│   │                                                          │   │
│   │  私有方法:                                                │   │
│   │  ├── _save_task(task)        → 持久化单个任务            │   │
│   │  ├── _load_task(package_id)  → 从存储加载单个任务        │   │
│   │  ├── load_from_storage()      → 启动时加载所有任务        │   │
│   │  └── _package_to_task(pkg)   → 转换存储格式→Task        │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      storage_layer.py                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   create_storage(config) → SQLiteStorage / MemoryStorage         │
│                                                                  │
│   SQLiteStorage 提供:                                            │
│   ├── save_package(package_dict)                                 │
│   ├── get_package(package_id)                                    │
│   ├── get_packages(status, data_type, operator, limit)           │
│   ├── update_package_status(package_id, status, completed_at)     │
│   └── delete_package(package_id)                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、模块依赖关系图

```
┌──────────────────────────────────────────────────────────────────┐
│                        依赖关系图                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌─────────────────────┐                                        │
│   │ container/__init__.py │                                       │
│   └──────────┬──────────┘                                        │
│              │                                                   │
│              │ imports                                           │
│              ▼                                                   │
│   ┌─────────────────────┐      ┌─────────────────────┐          │
│   │   task_pool.py      │──────│   storage_layer.py  │          │
│   │                     │ uses │                     │          │
│   │  TaskPool           │      │  create_storage()    │          │
│   │  Task               │      │  BaseStorage         │          │
│   │  TaskStatus         │      │  SQLiteStorage       │          │
│   │  TaskType           │      └─────────────────────┘          │
│   └──────────┬──────────┘                                        │
│              │                                                   │
│              │ imported by                                       │
│              ▼                                                   │
│   ┌─────────────────────┐                                        │
│   │ container_api_server.py│                                     │
│   │                     │                                        │
│   │  task_pool = TaskPool()                                      │
│   └─────────────────────┘                                        │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 四、接口契约定义

### 4.1 TaskPool 构造函数

```python
class TaskPool:
    def __init__(self, storage_config: Dict = None):
        """
        初始化任务容器池

        Args:
            storage_config: 存储配置，默认 {'type': 'sqlite', 'db_path': 'task_pool.db'}
        """
```

### 4.2 现有接口（保持不变）

| 方法签名 | 返回类型 | 说明 |
|---------|---------|------|
| `add_task(task: Task) -> str` | str | 添加任务，返回task_id |
| `get_task(task_id: str) -> Optional[Task]` | Task | 获取任务 |
| `get_tasks_by_type(task_type, status, operator_id) -> List[Task]` | List[Task] | 按类型获取 |
| `get_pending_tasks(operator_id, task_types) -> List[Task]` | List[Task] | 获取待处理 |
| `assign_task(task_id, operator_id) -> bool` | bool | 分配任务 |
| `start_task(task_id) -> bool` | bool | 开始任务 |
| `complete_task(task_id, result) -> bool` | bool | 完成任务 |
| `cancel_task(task_id, reason) -> bool` | bool | 取消任务 |
| `remove_task(task_id) -> bool` | bool | 删除任务 |
| `get_pool_status() -> Dict` | Dict | 状态统计 |

### 4.3 新增私有接口

| 方法签名 | 返回类型 | 说明 |
|---------|---------|------|
| `_save_task(task: Task) -> bool` | bool | 保存任务到存储 |
| `_load_task(package_id: str) -> Optional[Task]` | Optional[Task] | 从存储加载任务 |
| `load_from_storage() -> int` | int | 从存储加载所有任务，返回数量 |
| `_package_to_task(pkg: Dict) -> Task` | Task | 转换存储格式到Task |

### 4.4 数据转换契约

**Task → data_package 格式**：

```python
def _task_to_package(task: Task) -> Dict:
    """
    将 Task 对象转换为 storage_layer 的 package 格式
    """
    return {
        'id': task.id,
        'data_type': task.task_type,           # report/quality/material/approval/other
        'title': task.title,
        'content': task.content,                # Task.content 是 Dict
        'source': 'task_pool',
        'priority': task.priority,
        'status': task.status,                  # pending/assigned/in_progress/completed/cancelled
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'distributed_at': task.assigned_at.isoformat() if task.assigned_at else None,
        'acknowledged_at': None,                # TaskPool 不使用此状态
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'last_reminded_at': None,
        'target_operator': task.operator_id,
        'target_device': None,
        'tags': task.tags,
        'related_order': task.related_order,
        'related_process': task.related_process
    }
```

**package → Task 格式**：

```python
def _package_to_task(pkg: Dict) -> Task:
    """
    将 storage_layer 的 package 格式转换为 Task 对象
    仅用于从数据库恢复任务到内存
    """
    # 映射 status：storage 的状态值与 TaskStatus 枚举一致
    # pending → PENDING, assigned → ASSIGNED, etc.

    task = Task(
        task_type=pkg['data_type'],
        title=pkg.get('title', ''),
        content=pkg.get('content', {}),
        operator_id=pkg.get('target_operator'),
        priority=pkg.get('priority', 'normal'),
        deadline=None,  # TaskPool 不使用 deadline
        related_order=pkg.get('related_order'),
        related_process=pkg.get('related_process'),
        tags=pkg.get('tags', [])
    )
    task.id = pkg['id']
    task.status = pkg['status']

    # 时间字段
    if pkg.get('created_at'):
        task.created_at = datetime.fromisoformat(pkg['created_at'])
    if pkg.get('distributed_at') or pkg.get('assigned_at'):
        # 兼容 ContainerCenter 的 distributed_at 作为 assigned_at
        task.assigned_at = datetime.fromisoformat(pkg.get('distributed_at') or pkg.get('assigned_at'))
    if pkg.get('started_at'):
        task.started_at = datetime.fromisoformat(pkg['started_at'])
    if pkg.get('completed_at'):
        task.completed_at = datetime.fromisoformat(pkg['completed_at'])

    task.version = pkg.get('version', 1)
    return task
```

---

## 五、数据流向图（详细）

### 5.1 服务启动流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     服务启动 (container_api_server.py)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  task_pool = TaskPool()                                         │
│      │                                                          │
│      ├─→ 1. 创建 self.tasks = {}                                │
│      ├─→ 2. 创建 self.task_index = {...}                        │
│      └─→ 3. self.storage = create_storage(config)                │
│                  │                                              │
│                  ▼                                              │
│          ┌─────────────────┐                                     │
│          │ load_from_storage() │                                 │
│          │  - 查询所有 status != 'completed' 的任务             │
│          │  - 逐个转换为 Task 对象                              │
│          │  - 存入 self.tasks                                   │
│          │  - 更新 self.task_index                              │
│          └─────────────────┘                                     │
│                  │                                              │
│                  ▼                                              │
│          ┌─────────────────┐                                     │
│          │ 返回加载数量     │                                     │
│          └─────────────────┘                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 任务添加流程

```
┌─────────────────────────────────────────────────────────────────┐
│  publisher.publish_report_task(...)                              │
│      │                                                          │
│      ▼                                                          │
│  task_pool.add_task(task)                                        │
│      │                                                          │
│      ├─→ 1. self.tasks[task.id] = task                          │
│      ├─→ 2. self.task_index[task.task_type].append(task.id)     │
│      │                                                          │
│      └─→ 3. _save_task(task)  ← 持久化                          │
│                  │                                              │
│                  ▼                                              │
│          ┌─────────────────┐                                     │
│          │ storage.save_package(                                 │
│          │   _task_to_package(task)                              │
│          │ )                                                    │
│          └─────────────────┘                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 任务状态变更流程

```
┌─────────────────────────────────────────────────────────────────┐
│  assign_task(task_id, operator_id)                              │
│      │                                                          │
│      ├─→ 1. task.operator_id = operator_id                     │
│      ├─→ 2. task.status = ASSIGNED                             │
│      ├─→ 3. task.assigned_at = datetime.now()                  │
│      │                                                          │
│      └─→ 4. _save_task(task)  ← 持久化                          │
│                  │                                              │
│                  ▼                                              │
│          ┌─────────────────┐                                     │
│          │ storage.save_package(                                 │
│          │   _task_to_package(task)                              │
│          │ )                                                    │
│          └─────────────────┘                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、异常处理策略

### 6.1 异常场景

| 场景 | 处理策略 | 日志级别 |
|------|---------|---------|
| 存储连接失败 | 使用内存存储，降级运行 | WARNING |
| 保存失败 | 打印错误，继续内存操作 | ERROR |
| 加载失败 | 跳过损坏数据，继续启动 | ERROR |
| 任务不存在 | 返回 False/None | DEBUG |

### 6.2 降级策略

```python
def __init__(self, storage_config: Dict = None):
    try:
        self.storage = create_storage(storage_config)
        loaded = self.load_from_storage()
        print(f"[TaskPool] 从存储加载了 {loaded} 个任务")
    except Exception as e:
        print(f"[TaskPool] 存储初始化失败，降级到内存存储: {e}")
        self.storage = create_storage({'type': 'memory'})
        self.tasks = {}
        self.task_index = {...}
```

---

## 七、设计原则

### 7.1 遵循原则

| 原则 | 说明 |
|------|------|
| 最小改动 | 只修改 TaskPool 内部实现，不改变外部接口 |
| 立即持久化 | 每次状态变更立即保存，保证数据安全 |
| 内存优先 | 查询操作读内存，保证性能 |
| 复用设施 | 使用现有 storage_layer.py |
| 向后兼容 | 单例 `task_pool = TaskPool()` 无参调用保持兼容 |

### 7.2 不采用方案

| 方案 | 原因 |
|------|------|
| Redis | 增加部署复杂度，当前不需要分布式 |
| WAL模式 | SQLite 默认已足够 |
| 批量写入 | 增加复杂度，立即持久化已满足需求 |
| 定时同步 | 增加复杂度，立即持久化已满足需求 |

---

## 八、数据库表设计

### 8.1 沿用 data_packages 表

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

### 8.2 索引

```sql
-- TaskPool 专用的查询索引
CREATE INDEX IF NOT EXISTS idx_task_pool_status ON data_packages(status);
CREATE INDEX IF NOT EXISTS idx_task_pool_type ON data_packages(data_type);
CREATE INDEX IF NOT EXISTS idx_task_pool_operator ON data_packages(target_operator);
CREATE INDEX IF NOT EXISTS idx_task_pool_created ON data_packages(created_at);
```

---

**文档版本**：v1.0
**创建日期**：2026-05-02
**状态**：待审批
