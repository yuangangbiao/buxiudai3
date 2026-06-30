# dispatch_center.py 变更清单 — 云端同步指引

## 同步范围

以下变更为 `dispatch_center.py` 中针对 **操作员ID与工时单位统一改造** 的所有修改，需同步到云端的 `wechat_server.py`。

---

## 变更清单

### 1. 新增 import

| 文件 | 行号 | 内容 |
|------|------|------|
| dispatch_center.py | L79 | `from sync.event_bus import EventBus` |

### 2. TASK-01: list_operators() 补充 wechat_userid

**位置**: `list_operators()` 函数

**变更**: 在返回字典中添加 `wechat_userid` 字段：
```python
'wechat_userid': op.get('wechat_userid', ''),
```

### 3. TASK-02: create_operator() 接收 wechat_userid

**位置**: `create_operator()` 函数

**变更**: OperatorConfig 参数添加 wechat_userid：
```python
wechat_userid=body.get('wechat_userid', ''),
```

### 4. TASK-07: EventBus + MySQL 同步（核心，约120行）

插入位置：`sync_operators_from_wechat()` 函数附近

#### 4.1 `_ensure_operators_table()` — 自动建表

```python
def _ensure_operators_table():
    try:
        with get_db_cursor() as (cursor, conn):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dispatch_operators (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    operator_id VARCHAR(100) NOT NULL UNIQUE,
                    name VARCHAR(100) NOT NULL,
                    wechat_userid VARCHAR(100) DEFAULT '',
                    role VARCHAR(50) DEFAULT '操作员',
                    department VARCHAR(200) DEFAULT '',
                    enabled TINYINT(1) DEFAULT 1,
                    resigned_at DATETIME DEFAULT NULL,
                    notify_enabled TINYINT(1) DEFAULT 1,
                    max_tasks INT DEFAULT 10,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
    except Exception as e:
        logger.warning('创建 dispatch_operators 表失败(非致命): %s', e)
```

#### 4.2 `_sync_operator_to_mysql()` — 通用同步函数

```python
def _sync_operator_to_mysql(op_data, action='upsert'):
    try:
        _ensure_operators_table()
        with get_db_cursor() as (cursor, conn):
            if action == 'delete':
                cursor.execute(
                    "UPDATE dispatch_operators SET enabled=0, resigned_at=NOW() WHERE operator_id = %s",
                    (op_data['id'],)
                )
            elif action == 'reactivate':
                cursor.execute("""
                    UPDATE dispatch_operators SET name=%s, wechat_userid=%s, role=%s, department=%s,
                        enabled=1, resigned_at=NULL WHERE operator_id=%s
                """, (...略...))
            else:
                cursor.execute("""
                    INSERT INTO dispatch_operators (...) VALUES (...)
                    ON DUPLICATE KEY UPDATE ...
                """, (...略...))
            conn.commit()
    except Exception as e:
        logger.warning('同步操作员到MySQL失败: %s', e)
```

#### 4.3 `_register_operator_event_handlers()` — 注册事件处理器

```python
_subscribers_registered = False

def _register_operator_event_handlers():
    global _subscribers_registered
    if _subscribers_registered:
        return
    _subscribers_registered = True

    bus = EventBus.get()

    def _on_operator_created(data):
        _sync_operator_to_mysql(data, 'upsert')

    def _on_operator_updated(data):
        if 'enabled' in data and not data['enabled']:
            _sync_operator_to_mysql(data, 'delete')
        else:
            _sync_operator_to_mysql(data, 'upsert')

    def _on_operator_deleted(data):
        _sync_operator_to_mysql(data, 'delete')

    bus.subscribe('operator.created', _on_operator_created)
    bus.subscribe('operator.updated', _on_operator_updated)
    bus.subscribe('operator.deleted', _on_operator_deleted)
```

#### 4.4 `_migrate_operators_to_mysql()` — 历史数据迁移

```python
def _migrate_operators_to_mysql():
    try:
        from container_config import container_config
        operators = container_config.get_all_operators()
        for op in operators:
            _sync_operator_to_mysql({
                'id': op.id, 'name': op.name, 'wechat_userid': op.wechat_userid,
                'role': op.role, 'department': op.department,
                'enabled': op.enabled, 'notify_enabled': op.notify_enabled,
                'max_tasks': op.max_tasks,
            }, 'upsert')
    except Exception as e:
        logger.warning('迁移操作员到MySQL失败(非致命): %s', e)
```

### 5. TASK-09: 离职访问控制

#### 5.1 `_check_operator_enabled()` 函数

```python
def _check_operator_enabled(operator_id):
    if not operator_id:
        return True
    try:
        from container_config import container_config
        op = container_config.get_operator(operator_id)
        if op is None:
            return True
        return getattr(op, 'enabled', True)
    except Exception:
        pass
    return True
```

#### 5.2 `create_process_sub_step()` 注入检查

在写入前添加（约 L7613-L7615）：
```python
check_id = operator_id or wechat_userid
if check_id and not _check_operator_enabled(check_id):
    return jsonify({'code': 403, 'message': '操作员已离职，无法报工'}), 403
```

#### 5.3 字段补充

`create_process_sub_step()` 写入字段新增：
- `wechat_userid`
- `overtime_hours`（替代 `overtime_minutes`）
- `remark`

### 6. TASK-10: list_operators() include_disabled 支持

```python
def list_operators():
    include_disabled = request.args.get('include_disabled', '0') == '1'
    operators = DispatchContext.get_instance().get_cached_operators() or []
    operators_list = [{
        'id': op.get('id') or op.get('operator_id', ''),
        'name': op.get('name', ''),
        'role': op.get('role', ''),
        'department': op.get('department', ''),
        'enabled': op.get('enabled', True),
        'notify_enabled': op.get('notify_enabled', True),
        'max_tasks': op.get('max_tasks', 0),
        'wechat_userid': op.get('wechat_userid', ''),
    } for op in operators if include_disabled or op.get('enabled', True)]
    return jsonify({'code': 0, 'data': operators_list})
```

### 7. `__main__` 启动块新增

```python
try:
    _register_operator_event_handlers()
    logger.info("[OK] 操作员事件MySQL同步处理器已注册")
except Exception as e:
    logger.warning("[WARN] 操作员事件注册失败: %s", e)

try:
    _migrate_operators_to_mysql()
except Exception as e:
    logger.warning("[WARN] 操作员历史数据迁移失败: %s", e)
```

插入位置：`app = create_app()` 之后，`start_background_scheduler()` 之前。

---

## 依赖文件变更（需同步）

| 文件 | 变更内容 |
|------|---------|
| `mobile_api_ai/sync/event_bus.py` | L48: `handler(event_type, data)` → `handler(data)` |
| `mobile_api_ai/api/legacy_routes.py` | 新增 EventBus 事件发布 (`attendance.created`, `sub_step.created`) |
| `mobile_api_ai/container_center_api.py` | `overtime_minutes` → `overtime_hours`，`wechat_userid`，`remark`，`equipment_name` 字段补充 |
| `mobile_api_ai/storage_layer.py` | SQLite 字段 overtime_minutes → overtime_hours |
| `mobile_api_ai/sync/handlers/sub_step_handler.py` | SQLite 字段 overtime_minutes → overtime_hours |
| `mobile_api_ai/schema_auto.py` | DDL 字段 overtime_minutes → overtime_hours |
| `mobile_api_ai/templates/cs_report.html` | 前端 input id: overtime_minutes → overtime_hours |
| `mobile_api_ai/static/js/dispatch_center.js` | 前端操作员管理页增加离职标签、include_disabled 参数 |

---

## 云端部署同步步骤

1. 打开云端仓库中的 `wechat_server.py`
2. 按以上变更清单逐项应用修改
3. 确认 `from sync.event_bus import EventBus` 导入已添加
4. 确认 EventBus handler 参数签名为单参数 `def handler(data):`（已修复）
5. 确认 `__main__` 启动块包含 EventBus 注册和迁移调用
6. 部署前运行语法检查：`python -c "import ast; ast.parse(open('wechat_server.py', encoding='utf-8').read())"`
7. 部署后验证：新建操作员 → 检查 MySQL dispatch_operators 表是否有同步记录

---

> 生成时间：2026-05-26
> 关联文档：`TODO_操作员ID与工时单位统一改造.md` Item 3
> 规范约束：`wechat_server_cloud_only.md` — 云端专用，禁止本地修改
