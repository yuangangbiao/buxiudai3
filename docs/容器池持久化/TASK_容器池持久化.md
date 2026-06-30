# TASK_容器池持久化.md

## 任务概述

| 项目 | 内容 |
|------|------|
| 任务名称 | 容器池持久化 |
| 原子任务数量 | 6 |
| 依赖关系图 | 见下文 |

---

## 任务依赖图

```
┌──────────────────────────────────────────────────────────────────┐
│                      TASK 依赖关系图                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────┐                                                    │
│  │ TASK-1   │  添加存储层集成                                      │
│  │ 添加存储  │ ─────────────────────────────────┐               │
│  └────┬─────┘                                 │                │
│       │                                       │                │
│       │ TASK-2 需要 storage                   │                │
│       ▼                                       │                │
│  ┌──────────┐                                 │                │
│  │ TASK-2   │  实现数据转换                    │                │
│  │ 数据转换  │ ─────────────────────────────────┤                │
│  └────┬─────┘                                 │                │
│       │                                       │                │
│       │ TASK-3 需要 _task_to_package           │                │
│       │              _package_to_task          │                │
│       ▼                                       │                │
│  ┌──────────┐                                 │                │
│  │ TASK-3   │  实现持久化方法                  │                │
│  │ 持久化   │ ─────────────────────────────────┤                │
│  └────┬─────┘                                 │                │
│       │                                       │                │
│       │ TASK-4 需要这些方法                    │                │
│       ▼                                       │                │
│  ┌──────────┐                                 │                │
│  │ TASK-4   │  修改现有方法                    │                │
│  │ 修改方法  │ ─────────────────────────────────┤                │
│  └────┬─────┘                                 │                │
│       │                                       │                │
│       │ TASK-5 需要完整结构                    │                │
│       ▼                                       │                │
│  ┌──────────┐                                 │                │
│  │ TASK-5   │  添加降级处理                    │                │
│  │ 降级处理  │ ─────────────────────────────────┤                │
│  └────┬─────┘                                 │                │
│       │                                       │                │
│       │ TASK-6 需要完整功能                    │                │
│       ▼                                       │                │
│  ┌──────────┐                                 │                │
│  │ TASK-6   │  测试验证                        │                │
│  │ 测试验证  │                                  │                │
│  └──────────┘                                 │                │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## TASK-1: 添加存储层集成

### 1.1 输入契约

| 项目 | 说明 |
|------|------|
| 触发条件 | `task_pool = TaskPool()` 被调用 |
| 依赖组件 | storage_layer.py (已存在) |
| 配置参数 | `storage_config: Dict = None` |

### 1.2 输出契约

| 项目 | 说明 |
|------|------|
| 产出物 | `TaskPool.storage` 属性 |
| 初始化逻辑 | 创建 `self.storage = create_storage(config)` |
| 单例兼容性 | `task_pool = TaskPool()` 无参调用正常工作 |

### 1.3 实现约束

```python
# 修改前
def __init__(self):
    self.tasks: Dict[str, Task] = {}
    self.task_index: Dict[str, List[str]] = {...}

# 修改后
def __init__(self, storage_config: Dict = None):
    if storage_config is None:
        storage_config = {'type': 'sqlite', 'db_path': 'task_pool.db'}
    self.storage = create_storage(storage_config)
    self.tasks: Dict[str, Task] = {}
    self.task_index: Dict[str, List[str]] = {
        'report': [], 'quality': [], 'material': [], 'approval': [], 'other': []
    }
```

### 1.4 依赖关系

| 类型 | 任务ID | 说明 |
|------|--------|------|
| 后置任务 | TASK-2, TASK-3 | 需要 storage 属性 |

---

## TASK-2: 实现数据转换方法

### 2.1 输入契约

| 项目 | 说明 |
|------|------|
| 触发条件 | TASK-1 完成 |
| 输入 | Task 对象 或 storage package Dict |

### 2.2 输出契约

| 项目 | 说明 |
|------|------|
| 方法1 | `_task_to_package(task: Task) -> Dict` |
| 方法2 | `_package_to_task(pkg: Dict) -> Task` |

### 2.3 实现约束

**Task → data_package**：

```python
def _task_to_package(self, task: Task) -> Dict:
    return {
        'id': task.id,
        'data_type': task.task_type,
        'title': task.title,
        'content': task.content,
        'source': 'task_pool',
        'priority': task.priority,
        'status': task.status,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'distributed_at': task.assigned_at.isoformat() if task.assigned_at else None,
        'acknowledged_at': None,
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

**data_package → Task**：

```python
def _package_to_task(self, pkg: Dict) -> Task:
    task = Task(
        task_type=pkg['data_type'],
        title=pkg.get('title', ''),
        content=pkg.get('content', {}),
        operator_id=pkg.get('target_operator'),
        priority=pkg.get('priority', 'normal'),
        deadline=None,
        related_order=pkg.get('related_order'),
        related_process=pkg.get('related_process'),
        tags=pkg.get('tags', [])
    )
    task.id = pkg['id']
    task.status = pkg['status']

    if pkg.get('created_at'):
        task.created_at = datetime.fromisoformat(pkg['created_at'])
    if pkg.get('distributed_at'):
        task.assigned_at = datetime.fromisoformat(pkg['distributed_at'])
    if pkg.get('started_at'):
        task.started_at = datetime.fromisoformat(pkg['started_at'])
    if pkg.get('completed_at'):
        task.completed_at = datetime.fromisoformat(pkg['completed_at'])

    task.version = pkg.get('version', 1)
    return task
```

### 2.4 依赖关系

| 类型 | 任务ID | 说明 |
|------|--------|------|
| 前置任务 | TASK-1 | 需要 storage 属性 |
| 后置任务 | TASK-3 | 被持久化方法使用 |

---

## TASK-3: 实现持久化方法

### 3.1 输入契约

| 项目 | 说明 |
|------|------|
| 触发条件 | TASK-2 完成 |
| 依赖 | `_task_to_package`, `_package_to_task` |

### 3.2 输出契约

| 项目 | 说明 |
|------|------|
| 方法1 | `_save_task(task: Task) -> bool` - 保存单个任务 |
| 方法2 | `_load_task(package_id: str) -> Optional[Task]` - 加载单个任务 |
| 方法3 | `load_from_storage() -> int` - 加载所有任务，返回数量 |

### 3.3 实现约束

**_save_task**：

```python
def _save_task(self, task: Task) -> bool:
    """保存任务到存储"""
    try:
        pkg = self._task_to_package(task)
        return self.storage.save_package(pkg)
    except Exception as e:
        print(f"[TaskPool] 保存任务失败: {e}")
        return False
```

**_load_task**：

```python
def _load_task(self, package_id: str) -> Optional[Task]:
    """从存储加载单个任务"""
    try:
        pkg = self.storage.get_package(package_id)
        if pkg:
            return self._package_to_task(pkg)
        return None
    except Exception as e:
        print(f"[TaskPool] 加载任务失败: {e}")
        return None
```

**load_from_storage**：

```python
def load_from_storage(self) -> int:
    """从存储加载所有任务，返回加载数量"""
    try:
        # 只加载非完成状态的任务
        packages = self.storage.get_packages(limit=10000)
        count = 0
        for pkg in packages:
            if pkg.get('status') == TaskStatus.COMPLETED.value:
                continue  # 跳过已完成任务，减少内存占用
            task = self._package_to_task(pkg)
            self.tasks[task.id] = task
            if task.task_type in self.task_index:
                self.task_index[task.task_type].append(task.id)
            count += 1
        return count
    except Exception as e:
        print(f"[TaskPool] 从存储加载失败: {e}")
        return 0
```

### 3.4 依赖关系

| 类型 | 任务ID | 说明 |
|------|--------|------|
| 前置任务 | TASK-2 | 使用数据转换方法 |
| 后置任务 | TASK-4 | 被现有方法调用 |

---

## TASK-4: 修改现有方法添加持久化

### 4.1 输入契约

| 项目 | 说明 |
|------|------|
| 触发条件 | TASK-3 完成 |
| 修改方法 | add_task, assign_task, start_task, complete_task, cancel_task, remove_task |

### 4.2 输出契约

| 项目 | 说明 |
|------|------|
| 修改后方法 | 所有公共方法内部调用 `_save_task()` |

### 4.3 实现约束

| 方法 | 修改内容 |
|------|---------|
| `add_task(task)` | 添加后调用 `self._save_task(task)` |
| `assign_task(task_id, operator_id)` | 状态变更后调用 `self._save_task(task)` |
| `start_task(task_id)` | 状态变更后调用 `self._save_task(task)` |
| `complete_task(task_id, result)` | 状态变更后调用 `self._save_task(task)` |
| `cancel_task(task_id, reason)` | 状态变更后调用 `self._save_task(task)` |
| `remove_task(task_id)` | 删除时调用 `self.storage.delete_package(task_id)` |

### 4.4 依赖关系

| 类型 | 任务ID | 说明 |
|------|--------|------|
| 前置任务 | TASK-3 | 使用持久化方法 |
| 后置任务 | TASK-5 | 完整结构可测试降级 |

---

## TASK-5: 添加降级处理和错误处理

### 5.1 输入契约

| 项目 | 说明 |
|------|------|
| 触发条件 | TASK-4 完成 |
| 异常场景 | 存储初始化失败、存储操作失败 |

### 5.2 输出契约

| 项目 | 说明 |
|------|------|
| 降级逻辑 | 存储失败时降级到内存存储 |
| 错误日志 | 所有异常记录日志 |
| 服务启动 | 能从存储恢复任务 |

### 5.3 实现约束

```python
def __init__(self, storage_config: Dict = None):
    if storage_config is None:
        storage_config = {'type': 'sqlite', 'db_path': 'task_pool.db'}

    self.storage = None
    self.tasks: Dict[str, Task] = {}
    self.task_index: Dict[str, List[str]] = {
        'report': [], 'quality': [], 'material': [], 'approval': [], 'other': []
    }

    try:
        self.storage = create_storage(storage_config)
        loaded = self.load_from_storage()
        print(f"[TaskPool] 存储初始化成功，加载了 {loaded} 个任务")
    except Exception as e:
        print(f"[TaskPool] 存储初始化失败，降级到内存存储: {e}")
        self.storage = create_storage({'type': 'memory'})
        self.tasks = {}
        self.task_index = {
            'report': [], 'quality': [], 'material': [], 'approval': [], 'other': []
        }
```

### 5.4 依赖关系

| 类型 | 任务ID | 说明 |
|------|--------|------|
| 前置任务 | TASK-4 | 完整结构后可测试 |
| 后置任务 | TASK-6 | 可进行完整测试 |

---

## TASK-6: 测试验证

### 6.1 输入契约

| 项目 | 说明 |
|------|------|
| 触发条件 | 所有原子任务完成 |
| 测试环境 | Python 3.x + SQLite |

### 6.2 输出契约

| 验收标准 | 测试方法 |
|---------|---------|
| V1: TaskPool 初始化时从 SQLite 加载任务 | 添加任务→重启→验证任务存在 |
| V2: add_task 后任务持久化到 SQLite | 添加任务→查询数据库 |
| V3: 状态变更后 SQLite 数据同步更新 | 完成任务→查询数据库状态 |
| V4: 服务重启后任务数量和状态正确 | 重启前后对比 |
| V5: 不影响现有 API 接口调用 | 调用现有接口验证 |
| V6: 异常情况下日志正确记录 | 模拟异常场景 |

### 6.3 测试代码模板

```python
def test_task_pool_persistence():
    """测试任务持久化"""
    import os
    import tempfile

    # 创建临时数据库
    db_path = tempfile.mktemp(suffix='.db')

    try:
        # 1. 创建 TaskPool
        pool = TaskPool({'type': 'sqlite', 'db_path': db_path})

        # 2. 添加任务
        task = Task(
            task_type='report',
            title='测试报工',
            content={'record_id': 1, 'planned_qty': 100},
            operator_id='OP001',
            priority='high'
        )
        task_id = pool.add_task(task)
        assert task_id is not None

        # 3. 验证保存到存储
        saved = pool.storage.get_package(task_id)
        assert saved is not None
        assert saved['status'] == 'pending'

        # 4. 模拟重启 - 创建新实例
        pool2 = TaskPool({'type': 'sqlite', 'db_path': db_path})

        # 5. 验证任务恢复
        restored = pool2.get_task(task_id)
        assert restored is not None
        assert restored.task_type == 'report'
        assert restored.operator_id == 'OP001'

        # 6. 测试状态变更持久化
        pool2.assign_task(task_id, 'OP002')
        pool2.complete_task(task_id, {'completed_qty': 100})

        # 7. 再次重启验证
        pool3 = TaskPool({'type': 'sqlite', 'db_path': db_path})
        task3 = pool3.get_task(task_id)
        assert task3.status == 'completed'
        assert task3.result['completed_qty'] == 100

        print("✅ 所有持久化测试通过")

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
```

### 6.4 依赖关系

| 类型 | 任务ID | 说明 |
|------|--------|------|
| 前置任务 | TASK-5 | 所有功能完成 |

---

## 验收检查清单

### 代码层面

- [ ] TASK-1: `TaskPool.__init__` 包含 `self.storage`
- [ ] TASK-2: 存在 `_task_to_package` 和 `_package_to_task` 方法
- [ ] TASK-3: 存在 `load_from_storage`, `_save_task`, `_load_task` 方法
- [ ] TASK-4: `add_task`, `assign_task`, `start_task`, `complete_task`, `cancel_task`, `remove_task` 都调用持久化
- [ ] TASK-5: `__init__` 包含 try-except 降级逻辑

### 功能层面

- [ ] V1: 初始化时从 SQLite 加载任务
- [ ] V2: add_task 后任务保存到 SQLite
- [ ] V3: 状态变更后 SQLite 同步更新
- [ ] V4: 重启后任务恢复
- [ ] V5: API 接口正常工作
- [ ] V6: 异常有日志记录

---

**文档版本**：v1.0
**创建日期**：2026-05-02
**状态**：待执行
