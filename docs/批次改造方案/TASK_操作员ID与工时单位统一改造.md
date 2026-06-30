# 原子任务拆分 — 操作员ID与工时单位统一改造

## 任务依赖关系图

```mermaid
graph TD
    T01["TASK-01: C1 list_operators 补充 wechat_userid"]
    T02["TASK-02: C3+R3 create_operator 接收 wechat_userid + 前端表单"]
    T03["TASK-03: B-01+C2 容器中心工时单位改造 + 补字段"]
    T04["TASK-04: B-02 storage_layer.py 工时单位改造"]
    T05["TASK-05: B-03 sub_step_handler.py 工时单位改造"]
    T06["TASK-06: B-04+B-05 schema_auto + cs_report.html"]
    T07["TASK-07: H1+问题C EventBus + 建表 + MySQL同步"]
    T08["TASK-08: C4+H6 容器中心 OPERATORS 动态加载"]
    T09["TASK-09: 离职访问控制 三入口注入"]
    T10["TASK-10: 前端过滤 dispatch_center.js + include_disabled"]

    T01 --> T07
    T02 --> T07
    T03 --> T08
    T04 --> T06
    T05 --> T06
    T03 --> T06
    T07 --> T09
    T08 --> T09
    T09 --> T10

    subgraph 阶段1_问题B高优先级
        T03
        T04
        T05
    end

    subgraph 阶段2_C1_C3紧急修复
        T01
        T02
    end

    subgraph 阶段3_问题B中优先级
        T06
    end

    subgraph 阶段4_问题C核心
        T07
        T08
    end

    subgraph 阶段5_离职访问控制
        T09
        T10
    end

    linkStyle default stroke-width:2px,fill:none,stroke:#333;
```

---

## 执行顺序策略

根据依赖关系，推荐以下并行策略：

| 批次 | 可并行任务 | 说明 |
|------|-----------|------|
| 批次1 | TASK-01, TASK-02, TASK-03, TASK-04, TASK-05 | 无依赖，可全面铺开 |
| 批次2 | TASK-06 | 依赖TASK-03/04/05确认字段名 |
| 批次3 | TASK-07, TASK-08 | TASK-07依赖TASK-01/02完成；TASK-08依赖TASK-03完成 |
| 批次4 | TASK-09 | 依赖TASK-07(MySQL数据就绪) + TASK-08(容器中心动态加载) |
| 批次5 | TASK-10 | 依赖TASK-09(后端enabled状态可用) |

---

## TASK-01: list_operators() 补充 wechat_userid 返回

### 输入契约

| 前置依赖 | 说明 |
|---------|------|
| 环境 | dispatch_center.py 可正常启动运行 |
| 输入数据 | `get_cached_operators()` 已从 `OperatorConfig` 读取 `wechat_userid`(dispatch_center.py:L638-658) |
| 风险项 | 无 |

### 实现内容

- **文件**: `mobile_api_ai/dispatch_center.py`
- **位置**: L3068-L3076 `list_operators()` 函数
- **修改**: 在 operators_list 字典中添加 `'wechat_userid': op.get('wechat_userid', '')`
- **修改量**: 1行

### 验收标准

| 验收项 | 方法 | 预期 |
|-------|------|------|
| API 响应含 wechat_userid | `GET /operators` 返回 data[0].wechat_userid | 值非空字符串 |
| 前端报工 wechatUserid 不为 undefined | 检查 dispatch_center.js 报工提交 | `wechatUserid` 有正确值 |
| 已有操作员不受影响 | 对比改前改后返回长度和结构 | 仅新增字段，无破坏 |

### 输出契约

- 交付物：dispatch_center.py 已修改并语法验证通过
- 后置任务：TASK-07（需要 wechat_userid 数据流就绪）

---

## TASK-02: create_operator() 接收 wechat_userid + 前端表单增加输入框

### 输入契约

| 前置依赖 | 说明 |
|---------|------|
| 环境 | dispatch_center.py + dispatch_center.js 可正常启动 |
| 风险项 | 前端表单增加 wechat_userid 输入框需考虑 UX |

### 实现内容

#### 后端修改 [dispatch_center.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py)

- **位置**: `create_operator()` L3089-L3097
- **修改**: `OperatorConfig(...)` 参数添加 `wechat_userid=body.get('wechat_userid', '')`
- **修改量**: 1行

#### 前端修改 [dispatch_center.js](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/static/js/dispatch_center.js)

- **位置**: 新建操作员弹窗表单（搜索 `新建操作员` 或 `createOperatorModal` 相关代码）
- **修改**: 在表单中增加"企业微信账号"输入框（`<input name="wechat_userid">`）
- **修改量**: 3-5行（表单HTML + 提交时取值）

### 验收标准

| 验收项 | 方法 | 预期 |
|-------|------|------|
| 后端接收 wechat_userid | POST /operators 传 wechat_userid | 操作员创建成功，wechat_userid 存储 |
| 前端表单有输入框 | 打开新建操作员弹窗 | 可见"企业微信账号"输入框 |
| 提交后 wechat_userid 正确 | 创建后 GET /operators 查看 | wechat_userid 字段有值 |
| 不传 wechat_userid 兼容 | POST /operators 不传该字段 | 默认空字符串，不报错 |

### 输出契约

- 交付物：dispatch_center.py + dispatch_center.js 已修改
- 后置任务：TASK-07（需要 create_operator 的 wechat_userid 数据链路就绪）

---

## TASK-03: 容器中心 api_create_sub_step() 工时单位改造 + 补全同步字段

### 输入契约

| 前置依赖 | 说明 |
|---------|------|
| 环境 | container_center_api.py 可正常运行，晨圣报工链路可用 |
| 输入数据 | cs_report.html 前端当前使用 `overtime_minutes` 提交（兼容期保留） |
| 风险项 | ⚠️ 交叉合并任务，同时涉及问题B(工时)和问题C(补字段) |

### 实现内容

**文件**: [container_center_api.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_api.py)

#### 修改1: 变量读取 (L2491 附近)
```python
# 改前
overtime_minutes = int(data.get('overtime_minutes', 0))
# 改后
overtime_hours = float(data.get('overtime_hours', 0) or 0)
# 兼容旧版 front-end 仍传 overtime_minutes
if not data.get('overtime_hours') and data.get('overtime_minutes'):
    overtime_hours = round(int(data['overtime_minutes']) / 60, 2)
```

#### 修改2: 字典键名 (L2509 附近)
```python
# 改前
'overtime_minutes': overtime_minutes,
# 改后
'overtime_hours': overtime_hours,
```

#### 修改3: 同步到 sync_bridge 补全字段 (L2526-L2531)
```python
# 改前
requests.post(f'{sync_url}/api/sync/sub-step-report', json={
    'order_no': wo_no, 'step_name': step_name,
    'operator': operator, 'quantity': quantity
}, timeout=SHORT_TIMEOUT)

# 改后
requests.post(f'{sync_url}/api/sync/sub-step-report', json={
    'order_no': wo_no,
    'step_name': step_name,
    'operator': operator,
    'quantity': quantity,
    'qualified_qty': data.get('qualified_qty', quantity),
    'overtime_hours': overtime_hours,
    'wechat_userid': data.get('wechat_userid', ''),
    'remark': data.get('remark', ''),
    'equipment_name': data.get('equipment_name', ''),
}, timeout=SHORT_TIMEOUT)
```

#### 修改4: try-except 包裹同步请求 (H2修复)
```python
try:
    requests.post(...)
except Exception as e:
    logger.warning('同步报工到MySQL失败(非致命): %s', e)
```

### 验收标准

| 验收项 | 方法 | 预期 |
|-------|------|------|
| overtime_hours 存储为浮点数 | 容器中心写入 SQLite | 字段名 `overtime_hours`，类型 REAL |
| 旧数据 overtime_minutes 兼容 | 传 overtime_minutes=120 | 自动转为 overtime_hours=2.0 |
| sync_bridge 收到完整字段 | 检查 sync_bridge 日志 | 含 qualified_qty, overtime_hours, wechat_userid, remark, equipment_name |
| 异常时不阻断主流程 | 停止 sync_bridge 后报工 | 报工成功，仅警告日志 |

### 输出契约

- 交付物：container_center_api.py 已修改
- 后置任务：TASK-06(确认字段名)、TASK-08(同一文件继续修改)

---

## TASK-04: storage_layer.py 工时单位改造

### 输入契约

| 前置依赖 | 说明 |
|---------|------|
| 环境 | storage_layer.py 所在 SQLite 数据库 `chengsheng.db` 可读写 |
| 风险项 | SQLite 表结构需同步变更字段 |

### 实现内容

**文件**: [storage_layer.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/storage_layer.py)

| 位置 | 改前 | 改后 |
|------|------|------|
| L2053-2055 (INSERT 字段) | `overtime_minutes, created_at` | `overtime_hours, created_at` |
| L2068 (VALUES) | `int(record.get('overtime_minutes', 0) or 0),` | `float(record.get('overtime_hours', 0) or 0),` |
| L2102 (SELECT 读取) | `'overtime_minutes': row['overtime_minutes'] if 'overtime_minutes' in row.keys() else 0,` | `'overtime_hours': float(row['overtime_hours']) if 'overtime_hours' in row.keys() else 0,` |

### 验收标准

| 验收项 | 方法 | 预期 |
|-------|------|------|
| INSERT 使用 overtime_hours | 写入一条子步骤记录 | SQLite 中字段名为 overtime_hours |
| VALUES 传浮点数 | 写入 2.5 小时 | 数据库中存 2.5 |
| 旧数据读取不报错 | 读取旧记录（如有） | 默认返回 0，不抛异常 |

### 输出契约

- 交付物：storage_layer.py 已修改，语法验证通过
- 后置任务：TASK-06

---

## TASK-05: sub_step_handler.py 工时单位改造

### 输入契约

| 前置依赖 | 说明 |
|---------|------|
| 环境 | sync/handlers/sub_step_handler.py 可正常运行 |
| 风险项 | 同时影响 wechat_container.db 和 chengsheng.db 两个 SQLite 库 |

### 实现内容

**文件**: [sync/handlers/sub_step_handler.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/sync/handlers/sub_step_handler.py)

| 位置 | 改前 | 改后 |
|------|------|------|
| L77 (wechat_container INSERT 字段) | `overtime_minutes, created_at)` | `overtime_hours, created_at)` |
| L90 (VALUES) | `int(data.get('overtime_minutes', 0) or 0),` | `float(data.get('overtime_hours', 0) or 0),` |
| L113 (chengsheng INSERT 字段) | `overtime_minutes, created_at)` | `overtime_hours, created_at)` |
| L127 (VALUES) | `int(data.get('overtime_minutes', 0) or 0),` | `float(data.get('overtime_hours', 0) or 0),` |

### 验收标准

| 验收项 | 方法 | 预期 |
|-------|------|------|
| 两个数据库 INSERT 均使用 overtime_hours | 事件触发写入 | 两个 SQLite 库字段名均变更 |
| VALUES 传浮点数 | 传入 1.5 | 存为 1.5 |
| EventBus 数据兼容 | 事件 data 无 overtime_hours 时 | 默认 0，不报错 |

### 输出契约

- 交付物：sub_step_handler.py 已修改，语法验证通过
- 后置任务：TASK-06

---

## TASK-06: schema_auto.py + cs_report.html 工时单位改造

### 输入契约

| 前置依赖 | 说明 |
|---------|------|
| TASK-03 | 确认 container_center_api.py 字段名变更为 `overtime_hours` |
| TASK-04 | 确认 storage_layer.py 字段名一致 |
| TASK-05 | 确认 sub_step_handler.py 字段名一致 |

### 实现内容

#### 修改1: [schema_auto.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/schema_auto.py)

| 位置 | 改前 | 改后 |
|------|------|------|
| L21 (`process_sub_steps` 表) | `'overtime_minutes': 'INTEGER DEFAULT 0'` | `'overtime_hours': 'REAL DEFAULT 0'` |
| L43 (`sub_steps` 表) | `'overtime_minutes': 'INTEGER DEFAULT 0'` | `'overtime_hours': 'REAL DEFAULT 0'` |

#### 修改2: [templates/cs_report.html](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/templates/cs_report.html)

| 位置 | 改前 | 改后 |
|------|------|------|
| L302 (HTML input) | id=`overtime_minutes` | id=`overtime_hours` |
| L946 (JS 取值) | `document.getElementById('overtime_minutes')` | `document.getElementById('overtime_hours')` |
| L957 (JS 转换) | `overtime_minutes=parseInt(...)` | `overtime_hours=parseFloat(...) or 0` |
| L976 (请求体) | `overtime_minutes` | `overtime_hours` |

### 验收标准

| 验收项 | 方法 | 预期 |
|-------|------|------|
| schema_auto.py 建表字段正确 | 启动后检查新表结构 | `overtime_hours REAL DEFAULT 0` |
| cs_report.html 前端 input 改名 | 打开页面检查元素 | input id 为 overtime_hours |
| cs_report.html 提交字段正确 | 提交报工检查请求体 | JSON 中包含 `overtime_hours` |
| 旧页面无 JS 错误 | 打开 cs_report.html 控制台 | 无 `getElementById` null 错误 |

### 输出契约

- 交付物：schema_auto.py + cs_report.html 已修改
- 后置任务：无（问题B全部完成）

---

## TASK-07: EventBus 注册 + 建表 + MySQL 同步（问题C核心）

### 输入契约

| 前置依赖 | 说明 |
|---------|------|
| TASK-01 | `list_operators()` 已返回 `wechat_userid`（数据链路就绪） |
| TASK-02 | `create_operator()` 已接收 `wechat_userid`（数据入口就绪） |
| 环境 | dispatch_center.py 有 `get_db_cursor()` 可用，MySQL 可连接 |
| 风险项 | H1(EventBus未订阅)、R4(事件时序竞争)、R5(重复注册) |

### 实现内容

**文件**: [dispatch_center.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py)

#### 子任务 7.1: `_ensure_operators_table()` — 自动建表

在文件合适位置（建议在 `sync_operators_from_wechat` 附近或工具函数区）添加：

```python
def _ensure_operators_table():
    """自动创建 MySQL operators 表（幂等）"""
    try:
        with get_db_cursor() as (cursor, conn):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operators (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    operator_id VARCHAR(100) NOT NULL UNIQUE COMMENT '外部标识（同operators.json的id）',
                    name VARCHAR(100) NOT NULL COMMENT '操作员名称',
                    wechat_userid VARCHAR(100) DEFAULT '' COMMENT '微信用户ID',
                    role VARCHAR(50) DEFAULT '操作员' COMMENT '角色',
                    department VARCHAR(200) DEFAULT '' COMMENT '部门',
                    enabled TINYINT(1) DEFAULT 1 COMMENT '启用状态（1=在职，0=离职停用）',
                    resigned_at DATETIME DEFAULT NULL COMMENT '离职时间（NULL=在职）',
                    notify_enabled TINYINT(1) DEFAULT 1 COMMENT '消息通知',
                    max_tasks INT DEFAULT 10 COMMENT '最大任务数',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作员表'
            """)
            conn.commit()
            logger.info('MySQL operators 表已确认存在')
    except Exception as e:
        logger.warning('创建 MySQL operators 表失败(非致命): %s', e)
```

在 dispatch_center.py 启动/初始化时调用一次（如在 `register_blueprint` 或模块加载时）。

#### 子任务 7.2: `_sync_operator_to_mysql()` — 通用同步函数

```python
def _sync_operator_to_mysql(op_data, action='upsert'):
    """同步单个操作员数据到 MySQL operators 表"""
    try:
        _ensure_operators_table()
        with get_db_cursor() as (cursor, conn):
            if action == 'delete':
                cursor.execute(
                    "UPDATE operators SET enabled=0, resigned_at=NOW() WHERE operator_id = %s",
                    (op_data['id'],)
                )
            elif action == 'reactivate':
                cursor.execute("""
                    UPDATE operators SET name=%s, wechat_userid=%s, role=%s, department=%s,
                        enabled=1, resigned_at=NULL WHERE operator_id=%s
                """, (op_data.get('name', ''), op_data.get('wechat_userid', ''),
                      op_data.get('role', '操作员'), op_data.get('department', ''),
                      op_data['id']))
            else:
                cursor.execute("""
                    INSERT INTO operators (operator_id, name, wechat_userid, role, department,
                        enabled, notify_enabled, max_tasks)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name=VALUES(name), wechat_userid=VALUES(wechat_userid),
                        role=VALUES(role), department=VALUES(department),
                        enabled=VALUES(enabled), notify_enabled=VALUES(notify_enabled),
                        max_tasks=VALUES(max_tasks)
                """, (
                    op_data['id'], op_data.get('name', ''),
                    op_data.get('wechat_userid', ''), op_data.get('role', '操作员'),
                    op_data.get('department', ''), int(op_data.get('enabled', True)),
                    int(op_data.get('notify_enabled', True)), op_data.get('max_tasks', 10)
                ))
            conn.commit()
    except Exception as e:
        logger.warning('同步操作员到MySQL失败(非致命, operator_id=%s): %s', op_data.get('id', '?'), e)
```

#### 子任务 7.3: EventBus 订阅器注册

在 dispatch_center.py 启动初始化位置（如文件末尾的初始化块或 `if __name__` 块）添加订阅器：

```python
# 注册 EventBus 订阅器（确保只注册一次）
_subscribers_registered = False

def _register_operator_event_handlers():
    """注册操作员事件的MySQL同步处理器"""
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
    logger.info('操作员事件MySQL同步处理器已注册')
```

#### 子任务 7.4: `sync_operators_from_wechat()` 增加 MySQL 同步

在 `sync_operators_from_wechat()` 函数中（L3116 附近），创建或更新每个操作员后追加 MySQL 写入：

```python
# 在 container_config.add_operator(op) 成功后追加
_sync_operator_to_mysql({
    'id': op.id,
    'name': op.name,
    'wechat_userid': op.wechat_userid,
    'role': op.role,
    'department': op.department,
    'enabled': op.enabled,
    'notify_enabled': op.notify_enabled,
    'max_tasks': op.max_tasks,
}, 'upsert')

# 在离职标记后追加
_sync_operator_to_mysql({'id': op.id}, 'delete')
```

#### 子任务 7.5: 历史数据迁移

在 `_ensure_operators_table()` 或启动初始化时，将 `operators.json` 中已有操作员批量写入 MySQL：

```python
def _migrate_operators_to_mysql():
    """将 operators.json 已有操作员迁移到 MySQL（幂等）"""
    try:
        from container_config import container_config
        operators = container_config.get_all_operators()
        count = 0
        for op in operators:
            _sync_operator_to_mysql({
                'id': op.id,
                'name': op.name,
                'wechat_userid': op.wechat_userid,
                'role': op.role,
                'department': op.department,
                'enabled': op.enabled,
                'notify_enabled': op.notify_enabled,
                'max_tasks': op.max_tasks,
            }, 'upsert')
            count += 1
        if count > 0:
            logger.info('历史操作员已迁移 %d 人到 MySQL', count)
    except Exception as e:
        logger.warning('迁移操作员到MySQL失败(非致命): %s', e)
```

### 验收标准

| 验收项 | 方法 | 预期 |
|-------|------|------|
| MySQL operators 表自动创建 | 启动 dispatch_center.py | 表已存在，结构正确 |
| 新建操作员同步到 MySQL | 调度中心新建操作员 → 查 MySQL | MySQL 有该记录 |
| 编辑操作员同步到 MySQL | 修改姓名/部门 → 查 MySQL | 字段已更新 |
| 删除操作员标记离职 | 删除操作员 → 查 MySQL | enabled=0, resigned_at 非空 |
| 同步企业微信写入 MySQL | 触发 sync_operators_from_wechat → 查 MySQL | 新增/更新/离职标记均生效 |
| 历史数据迁移 | 首次启动 → 查 MySQL | operators.json 中所有操作员已迁移 |
| 重复注册防护 | 多次调用 `_register_operator_event_handlers()` | 只注册一次，回调不重复执行 |

### 输出契约

- 交付物：dispatch_center.py 新增约 120 行代码
- 后置任务：TASK-09（需要 MySQL 数据就绪）

---

## TASK-08: 容器中心 OPERATORS 改为动态加载

### 输入契约

| 前置依赖 | 说明 |
|---------|------|
| TASK-03 | container_center_api.py 已修改，同一文件避免冲突 |
| 环境 | 容器中心可访问 `container_config` 或 `operators.json` |

### 实现内容

**文件**: [container_center_api.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_api.py)

#### 修改1: 替换 OPERATORS 硬编码列表 (L660-L667)

将模块级硬编码 `OPERATORS` 列表替换为动态加载函数：

```python
# 移除硬编码 OPERATORS 列表
# 替换为动态加载函数
def _get_dynamic_operators():
    """从 container_config 动态加载操作员列表"""
    try:
        from container_config import container_config
        operators = container_config.get_all_operators()
        return [{
            'operator_id': op.id,
            'name': op.name,
            'role': op.role,
            'team_name': op.department or '',
            'wechat': op.wechat_userid or '',
            'enabled': op.enabled,
        } for op in operators]
    except Exception as e:
        logger.warning('动态加载操作员列表失败，返回空列表: %s', e)
        return []
```

#### 修改2: 替换所有引用点

将所有使用 `OPERATORS` 列表的地方改为调用 `_get_dynamic_operators()`：

- `api_v4_operators()` (L967-969)
- `get_operators()` (L960-964)
- 所有 `next((op for op in OPERATORS if ...)` 查找模式

将这些位置的 `OPERATORS` 替换为 `_get_dynamic_operators()` 或添加缓存。

#### 修改3: 兼容版 OPERATORS 列表 (L924-L931)

同样替换，或直接移除（若确认 3.0 版本兼容段不再使用）。

### 验收标准

| 验收项 | 方法 | 预期 |
|-------|------|------|
| 操作员列表动态加载 | 容器中心 GET /api/operators | 返回与 operators.json 一致 |
| 新增操作员立即可见 | 调度中心新建操作员 → 容器中心查列表 | 操作员已出现 |
| 离职标记反映在列表 | 离职操作员 → 容器中心列表 | enabled=false |
| 性能无显著下降 | 批量请求 | 响应时间 < 200ms（可考虑加内存缓存） |
| 降级不崩溃 | container_config 不可用时 | 返回空列表，不抛500 |

### 输出契约

- 交付物：container_center_api.py 已修改
- 后置任务：TASK-09（需要容器中心动态加载就绪）

---

## TASK-09: 离职访问控制 — 三入口注入 _check_operator_enabled()

### 输入契约

| 前置依赖 | 说明 |
|---------|------|
| TASK-07 | MySQL operators 表已就绪，enabled 状态可查询 |
| TASK-08 | 容器中心 OPERATORS 已动态加载，含 enabled 标记 |
| 风险项 | R2(容器中心不可用时的回退绕过) |

### 实现内容

#### 文件1: [dispatch_center.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py)

**注入点**: `create_process_sub_step()` 参数校验后、写入前

```python
def _check_operator_enabled(operator_name='', wechat_userid=''):
    """检查操作员是否在职，离职人员返回 False 和错误信息"""
    # 第一层：从 container_config 读取 enabled 状态
    try:
        from container_config import container_config
        for op in container_config.get_all_operators():
            if (op.name == operator_name or (wechat_userid and op.wechat_userid == wechat_userid)):
                if not op.enabled:
                    return False, f'操作员"{operator_name}"已离职，无法报工'
                return True, None
    except Exception as e:
        logger.warning('检查操作员状态失败(尝试MySQL兜底): %s', e)

    # 第二层：从 MySQL operators 表兜底查询
    try:
        with get_db_cursor() as (cursor, conn):
            cursor.execute(
                "SELECT enabled FROM operators WHERE name = %s OR wechat_userid = %s LIMIT 1",
                (operator_name, wechat_userid)
            )
            row = cursor.fetchone()
            if row and not row[0]:
                return False, f'操作员"{operator_name}"已离职，无法报工'
    except Exception as e:
        logger.warning('MySQL兜底检查失败: %s', e)

    return True, None  # 均不可用时放行（不阻断生产）
```

在 `create_process_sub_step()` 中增加调用：
```python
ok, msg = _check_operator_enabled(operator, wechat_userid)
if not ok:
    return jsonify({'code': 403, 'message': msg}), 403
```

#### 文件2: [api/legacy_routes.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/legacy_routes.py)

**注入点**: `api_create_sub_step()` 参数校验后、写入前
- 导入 `_check_operator_enabled`（从 dispatch_center.py 或单独抽出）
- 相同检查逻辑

#### 文件3: [container_center_api.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_api.py)

**注入点**: `api_create_sub_step()` 参数校验后、写入前 (L2477 附近)
- 使用 `_get_dynamic_operators()` 返回的 enabled 状态检查
- 或直接检查 operator 的 enabled 属性

### 验收标准

| 验收项 | 方法 | 预期 |
|-------|------|------|
| 调度中心报工阻断离职人员 | 离职操作员在调度中心报工 | 返回 403 "已离职" |
| 容器中心报工阻断离职人员 | 离职操作员扫码报工 | 返回 403 "已离职" |
| 旧版API报工阻断离职人员 | 直接调用 legacy API 离职报工 | 返回 403 "已离职" |
| 在职人员正常报工 | 在职操作员报工 | 正常通过 |
| 兜底不阻断生产 | container_config 不可用时 | 放行并记录警告日志 |

### 输出契约

- 交付物：dispatch_center.py + legacy_routes.py + container_center_api.py 已修改
- 后置任务：TASK-10

---

## TASK-10: 前端过滤 + include_disabled 支持

### 输入契约

| 前置依赖 | 说明 |
|---------|------|
| TASK-09 | 后端 enabled 状态数据已就绪 |
| 风险项 | 前端过滤后离职人员仍可通过直接 API 调用报工（已在 TASK-09 后端阻断） |

### 实现内容

#### 修改1: [dispatch_center.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py)

`list_operators()` 增加 `include_disabled` 参数支持：

```python
@dispatch_center_bp.route('/operators', methods=['GET'])
def list_operators():
    include_disabled = request.args.get('include_disabled', '0') == '1'
    operators = DispatchContext.get_instance().get_cached_operators() or []
    operators_list = [{
        'id': op.get('id') or op.get('operator_id', ''),
        'name': op.get('name', ''),
        'role': op.get('role', ''),
        'department': op.get('department', '') or op.get('team_name', ''),
        'enabled': op.get('enabled', True),
        'notify_enabled': op.get('notify_enabled', True),
        'max_tasks': op.get('max_tasks', 0),
        'wechat_userid': op.get('wechat_userid', ''),
    } for op in operators if include_disabled or op.get('enabled', True)]
    return jsonify({'code': 0, 'data': operators_list})
```

#### 修改2: [dispatch_center.js](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/static/js/dispatch_center.js)

前端过滤离职操作员：

| 位置 | 功能 | 修改 |
|------|------|------|
| `loadOperators()` 任务筛选下拉框 | 填充下拉选项 | 当前已默认过滤（后端默认不返），无需改；或加 `enabled` 判断 |
| `reassignTask()` 转派操作员对话框 | 列表展示 | 同上，后端已过滤 |
| 操作员管理列表 | 管理员查看全部操作员 | `GET /operators?include_disabled=1` 获取全部，离职标记"已离职" |

### 验收标准

| 验收项 | 方法 | 预期 |
|-------|------|------|
| 下拉框不显示离职操作员 | 打开任务筛选下拉框 | 离职操作员不可见 |
| 管理员可查看离职人员 | 操作员管理页面 | 离职人员可见，标记"已离职" |
| include_disabled 参数生效 | GET /operators?include_disabled=1 | 返回全部操作员(含离职) |
| 默认不返离职人员 | GET /operators (无参) | 只返回 enabled=true |

### 输出契约

- 交付物：dispatch_center.py + dispatch_center.js 已修改
- 后置任务：无（全部完成）

---

## 附录：验证命令

### 语法验证
```bash
cd d:\yuan\不锈钢网带跟单3.0
python -c "import ast; ast.parse(open('mobile_api_ai/dispatch_center.py', encoding='utf-8').read())"
python -c "import ast; ast.parse(open('mobile_api_ai/container_center_api.py', encoding='utf-8').read())"
python -c "import ast; ast.parse(open('mobile_api_ai/api/legacy_routes.py', encoding='utf-8').read())"
python -c "import ast; ast.parse(open('mobile_api_ai/storage_layer.py', encoding='utf-8').read())"
python -c "import ast; ast.parse(open('mobile_api_ai/sync/handlers/sub_step_handler.py', encoding='utf-8').read())"
python -c "import ast; ast.parse(open('mobile_api_ai/schema_auto.py', encoding='utf-8').read())"
```

### 回归搜索（确保无遗漏）
```bash
# 检查 overtime_minutes 残留
findstr /sni "overtime_minutes" mobile_api_ai\*.py mobile_api_ai\templates\*.html mobile_api_ai\static\js\*.js

# 注意：以下位置允许保留 overtime_minutes（属于兼容层）
# - storage_layer.py 读取端的兼容处理

---

## 附录：任务拆分方案审计报告

> 审计日期：2026-05-26
> 审计依据：DESIGN_操作员ID与工时单位统一改造.md、TASK_操作员ID与工时单位统一改造.md、实际代码验证
> 审计方法：交叉校验 + 代码行号验证 + 风险映射追溯

---

### 一、任务完整性（TC — 对照 DESIGN 验证覆盖度）

| 编号 | 等级 | 发现 | 影响 | 建议 |
|------|------|------|------|------|
| **TC-01** | 🔴 | **B-06 完全缺失**：`scripts/tools/sync_container_to_cs.py`（6处 `overtime_minutes`）未纳入任何 TASK。DESIGN 执行计划阶段3明确列出的文件，TASK 文档完全未提及 | 实施后该迁移脚本仍使用 `overtime_minutes`，新数据写入 `overtime_hours` 字段后，迁移脚本读取不到 | 在 TASK-06 中追加：在 sync_container_to_cs.py 中添加 `overtime_hours` 读取兼容层（读取 `overtime_hours`，若为0则回退 `overtime_minutes`） |
| **TC-02** | 🔴 | **H4 垃圾列未清理**：`storage_mysql.py` 的 `PSS_COLUMNS`（已确认 L49）同时包含 `overtime_minutes` 和 `overtime_hours`，没有任何 TASK 计划移除 `overtime_minutes` | 数据写入了两个字段，造成存储浪费和查询歧义 | 在 TASK-06 中追加：实施完问题B所有字段迁移后，最后从 `PSS_COLUMNS` 中移除 `overtime_minutes` 列 |
| **TC-03** | 🟡 | **扫码报工路由未明确**：TASK-09 中对"扫码报工相关路由"的描述过于模糊（"或直接检查 operator 的 enabled 属性"），未给出精确的路由函数名或行号 | 实施时容易遗漏扫码报工入口的离职检查 | 在 TASK-09 中明确扫码报工路由的函数名（如 `container_center_api.py` 中的 `scan_to_report` 或类似路由） |
| **TC-04** | 🟡 | **legacy_routes.py 导入方式模糊**：TASK-09 说 `_check_operator_enabled` 从 dispatch_center.py 导入"或单独抽出"，没有明确方案 | 实施时产生模块导入方式的不确定性 | 明确指定：将 `_check_operator_enabled` 放在 dispatch_center.py 中，其他文件通过 `from dispatch_center import _check_operator_enabled` 导入 |
| **TC-05** | 🟡 | **TASK-07 调用时机未说明**：`_register_operator_event_handlers()` 的调用位置未在伪代码或实现内容中明确 | 如果忘记在 app 初始化时调用，EventBus 订阅不会生效，MySQL 同步完全失效 | 在 TASK-07 实现内容中明确：需要在 `dispatch_center.py` 应用工厂或 `create_app()` 中调用此函数 |
| **TC-06** | 🟢 | **wecom_auth.py 离职检查未确认**：DESIGN 7.10节第1项确认已有 enabled 检查，但 TASK 文档未通过阅读代码确认此检查确实存在且正确 | 离职阻断链路在 APP 登录端可能存在盲区 | 在 TASK-09 验收标准中增加：阅读 `wecom_auth.py` 的 `wecom_login()` 确认 enabled 检查逻辑 |

---

### 二、依赖关系与批次策略（DP）

| 编号 | 等级 | 发现 | 影响 | 建议 |
|------|------|------|------|------|
| **DP-01** | 🔴 | **同一文件跨3个批次修改**：`container_center_api.py` 在批次1(TASK-03)、批次3(TASK-08)、批次4(TASK-09)被修改3次。三个修改点分散在文件不同位置（~L2491、~L660、~L924、~L2477），每次修改都涉及同一文件的打开、修改、验证 | 批次1改完后，批次3/4在旧代码上继续改，可能出现行号偏移、合并遗漏、甚至代码回退。每批次间的修改互不知晓 | **方案A（推荐）**：将 TASK-08 从批次3移至批次4，与 TASK-09 合并为同一批次执行，确保对 `container_center_api.py` 的修改一次性完成。<br>**方案B**：保持原批次，但在 TASK-03 备注中记录 L660/L924/L2477 在批次3/4需要修改，提醒后续操作 |
| **DP-02** | 🟡 | **TASK-06 先行验证不明确**：TASK-06 依赖 TASK-03/04/05 确认字段名。文档说"等批次2执行时确认字段名已改好"，但没有明确的验证步骤 | 如果 TASK-03/04/05 的实施与文档有偏差（如列名改为 `hours` 而非 `overtime_hours`），TASK-06 会直接沿用错误 | 在 TASK-06 的"执行前检查"中增加：`grep -n "overtime_hours\|overtime_minutes"` 验证各文件的字段名是否统一 |

---

### 三、输入输出契约质量（IQ）

| 编号 | 等级 | 发现 | 影响 | 建议 |
|------|------|------|------|------|
| **IQ-01** | 🟡 | **TASK-02 前端位置搜索词模糊**：只说"搜索`新建操作员`或`createOperatorModal`"，未提供精确行号或具体 HTML 元素 | 实施时可能需要额外搜索定位，增加时间成本 | 补充前端的精确搜索关键词或行号范围 |
| **IQ-02** | 🟡 | **TASK-08 兼容版 OPERATORS 处理模糊**：对 L924-L931 的兼容版 OPERATORS 说"同样替换，或直接移除"——两个选择差异很大 | 直接移除可能影响旧版扫码报工，改为动态加载又需要测试 | 明确指定：**同样替换为 `_get_dynamic_operators()`**，不直接移除，保持向后兼容 |
| **IQ-03** | 🟡 | **TASK-10 前端修改缺少精确代码**：说"前端部分只需在后端过滤基础上确认前端下拉框逻辑，无需额外操作；或加 enabled 判断"——缺少精确的修改方案 | 实施时可能遗漏前端过滤或做了不必要的改动 | 明确：后端已过滤，前端只需确认 `loadOperators()` 回调中不主动传 `include_disabled=1` 即可；操作员管理页面的"显示离职"按钮需额外处理 |
| **IQ-04** | 🟡 | **TASK-07 验收标准缺少时序测试**：未包含 EventBus 时序竞争（R4）的验证，即"创建操作员后立即报工，MySQL 能否查到" | 时序竞争可能导致线上报工失败 | 在验收标准中增加时序压力测试：创建操作员后 100ms 内发起报工，验证阻断逻辑是否正常工作 |
| **IQ-05** | 🟡 | **TASK-04 验收标准未包含 H5 兼容层验证**：storage_layer.py 读数据时没有兼容层来识别旧数据的 `overtime_minutes` | 旧的报工记录读取不到工时数据 | 在验收标准中增加：用旧数据（`overtime_minutes` 有值）验证读取，确认兼容层将其映射到 `overtime_hours` |

---

### 四、风险覆盖率（RC — 20个风险点映射检查）

**DESIGN 文档审计共发现 20 个风险点（CRITICAL×4 + HIGH×6 + MEDIUM×3 + LOW×2 + 补充×5），TASK 映射情况：**

| 风险ID | 等级 | 描述 | 覆盖任务 | 覆盖状态 |
|--------|------|------|---------|---------|
| C1 | 🔴 | list_operators 缺少 wechat_userid | TASK-01 | ✅ 完全覆盖 |
| C2 | 🔴 | 容器中心同步只传4字段 | TASK-03(修改3) | ✅ 完全覆盖 |
| C3 | 🔴 | create_operator 不传 wechat_userid | TASK-02 | ✅ 完全覆盖 |
| C4 | 🔴 | 三源数据模型不一致 | TASK-08 | ✅ 完全覆盖 |
| H1 | 🔴 | EventBus 未订阅 operator.created | TASK-07(子任务3) | ✅ 完全覆盖 |
| H2 | 🔴 | 容器中心同步无事务保证 | TASK-03(修改4) | ✅ 完全覆盖 |
| H3 | 🔴 | sync_bridge 查表无结果 | TASK-07(建表+迁移) | ⚠️ 间接覆盖，需验收标准确认 |
| **H4** | 🔴 | **storage_mysql.py 垃圾列** | **❌ 未覆盖** | 见 TC-02 |
| **H5** | 🔴 | **缺少统一字段映射层** | **❌ 未覆盖** | 见 IQ-05 |
| H6 | 🔴 | 容器中心硬编码列表 | TASK-08 | ✅ 完全覆盖 |
| **M1** | 🟡 | **sync_bridge 线程安全** | **❌ 未覆盖** | 见 RC-03 |
| M2 | 🟡 | 调用端静默吞异常 | TASK-03(修改4) | ✅ 完全覆盖 |
| M3 | 🟡 | cs_report.html 字段不一致 | TASK-06 | ✅ 完全覆盖 |
| **L1** | 🟢 | sync_container_to_cs.py 迁移脚本 | **❌ 未覆盖** | 见 TC-01 |
| **L2** | 🟢 | EventBus 事件幂等 | **❌ 未覆盖** | 见 RC-05 |
| R1 | 🟠 | 实施顺序依赖 | TASK-03(合并) | ✅ 完全覆盖 |
| R2 | 🟠 | 离职检查回退绕过 | TASK-09(双层检查) | ✅ 完全覆盖 |
| R3 | 🟠 | 前端不传 wechat_userid | TASK-02 | ✅ 完全覆盖 |
| **R4** | 🟠 | **EventBus 时序竞争** | **❌ 未覆盖** | 见 IQ-04 |
| R5 | 🟢 | subscribe 重复注册 | TASK-07(全局变量) | ✅ 完全覆盖 |

**未覆盖风险汇总（5个）：**

| 编号 | 等级 | 风险 | 状态 | 处理建议 |
|------|------|------|------|---------|
| **RC-01** | 🔴 | H4 storage_mysql.py 垃圾列 | 未覆盖 | 追加到 TASK-06 |
| **RC-02** | 🔴 | H5 统一字段映射层 | 未覆盖 | 追加到 TASK-04 实现内容 |
| **RC-03** | 🟡 | M1 sync_bridge 线程安全 | 未覆盖 | 追加到 TASK-03：`STORED_ROUTES` 加 `threading.Lock()` |
| **RC-04** | 🟡 | R4 EventBus 时序竞争 | 未覆盖 | 追加到 TASK-07：同步模式下 MySQL 写入先于报工请求处理 |
| **RC-05** | 🟢 | L2 事件幂等 | 未覆盖 | 追加到 TASK-07 验收标准：重复触发 operator.created 事件不产生重复记录 |

---

### 五、文档结构与代码细节（DS）

| 编号 | 等级 | 发现 | 说明 |
|------|------|------|------|
| **DS-01** | 🟢 | **TASK-03 `overtime_hours` 类型确认**：TASK-03 说改为 `float(data.get('overtime_hours', 0))`（已确认 container_center_api.py L2491 原为 `int()`），但后续同步到 storage_layer.py 时字段类型为 `INTEGER` → `REAL`（TASK-06 确认） | 类型链一致，无问题 |
| **DS-02** | 🟢 | **sync_container_to_cs.py 字段迁移确认**：该文件 L260 现用 `ALTER TABLE ... ADD COLUMN overtime_minutes INTEGER DEFAULT 0`，需追加 `overtime_hours REAL DEFAULT 0` | 追加到 TASK-06 实现内容 |

---

### 六、审计结论

#### 6.1 整体评价

| 维度 | 评分 | 说明 |
|------|------|------|
| 任务完整性 | ⚠️ **7/10** | 10个任务覆盖了 DESIGN 约 85% 的需求，但遗漏 B-06、H4、H5 等关键项 |
| 依赖正确性 | ⚠️ **8/10** | Mermaid 图和批次分组基本正确，但 container_center_api.py 三批次修改是严重问题 |
| 输入输出质量 | ✅ **8/10** | 大多数验收标准可测试，伪代码精确，但部分前端位置模糊 |
| 风险覆盖 | ⚠️ **7/10** | 20个风险点中 15 个已覆盖，5 个未覆盖（2 CRITICAL + 1 MEDIUM + 2 LOW） |
| 文档结构 | ✅ **9/10** | 格式一致、Mermaid 清晰、章节有序 |

#### 6.2 实施前必须解决项（按优先级）

| 优先级 | 编号 | 描述 | 操作 |
|--------|------|------|------|
| 🔴 P0 | DP-01 | container_center_api.py 三批次修改冲突 | 将 TASK-08 移至批次4，与 TASK-09 合并执行 |
| 🔴 P0 | TC-01 + RC-01 | B-06 + H4 未覆盖（2个 CRITICAL 风险） | 追加到 TASK-06 实现内容 |
| 🔴 P0 | RC-02 | H5 字段映射层缺失 | 追加到 TASK-04 实现内容（读取端兼容 `overtime_minutes` 回退到 `overtime_hours`） |
| 🟡 P1 | TC-03/04/05 | 模糊描述修正 | TASK-07/08/09 中补充精确函数名、导入方式、调用位置 |
| 🟡 P1 | RC-04 | R4 EventBus 时序竞争 | TASK-07 验收标准增加时序测试 |
| 🟢 P2 | IQ-03/05 | 验收标准完善 | 补充前端验证和兼容层验证 |

#### 6.3 修复后的推荐批次策略

```
批次1: TASK-01, TASK-02, TASK-03, TASK-04(含H5), TASK-05      ← 无变化，TASK-04追加兼容层
批次2: TASK-06(追加B-06+H4)                                      ← 追加 sync_container_to_cs.py 和 storage_mysql.py 清理
批次3: TASK-07                                                   ← 仅 TASK-07（独立，无文件冲突）
批次4: TASK-08 + TASK-09(合并)                                    ← 合并批次，一次性改完 container_center_api.py
批次5: TASK-10                                                   ← 无变化
```

---

> 审计结论：TASK 文档整体质量良好（约 78/100），但建议在实施前按 P0 优先级修复 5 个关键问题，特别是 **container_center_api.py 跨批次修改冲突** 和 **B-06/H4/H5 风险未覆盖** 问题，否则实施过程中可能产生严重的回归错误。

---

## 深度审计报告（第二轮）

> 审计日期：2026-05-26
> 审计方法：逐行代码验证 + 数据流端到端追踪 + 类型链检查 + 第一轮修复建议自我审计
> 审计范围：dispatch_center.py、container_center_api.py、storage_layer.py、sync_bridge.py、legacy_routes.py、storage_mysql.py、schema_auto.py、cs_report.html

---

### 1. 现有代码运行时 Bug（DA-01）

| 编号 | 严重度 | 文件:行号 | 发现 | 根因 |
|------|--------|----------|------|------|
| **DA-01** | 🔴 **CRITICAL** | [dispatch_center.py:L3103](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L3103) | **`create_operator()` 存在 `NameError` 运行时崩溃** | L3103 使用了 `role` 变量，但该变量在函数作用域中**从未定义**。L3100 `body.get('role', '操作员')` 的结果未赋值给任何变量，直接内联传给了 `OperatorConfig(role=...)`。调用 `EventBus.get().publish('operator.created', {'role': role, ...})` 时 Python 会抛出 `NameError: name 'role' is not defined`，operator.created 事件永远不会被发布，MySQL 同步完全失效 |

**影响链**：`create_operator()` → L3103 NameError → `operator.created` 事件丢失 → TASK-07 `_register_operator_event_handlers()` 收不到通知 → MySQL operators 表无数据 → TASK-09 离职检查 MySQL 兜底查不到人

**修复**：L3103 `'role': role` → `'role': body.get('role', '操作员')`

---

### 2. TASK 层实现漏洞（DA-02 ~ DA-04）

| 编号 | 严重度 | 关联任务 | 发现 |
|------|--------|---------|------|
| **DA-02** | 🔴 **CRITICAL** | TASK-02 | **TASK-02 修复不完整**：文档仅提及给 `OperatorConfig(...)` 添加 `wechat_userid=body.get('wechat_userid', '')`，但忽略了 L3100-L3106 的 event publish 中同样缺少 `wechat_userid`。即使 TASK-02 改完了 OperatorConfig，L3103 的 `role` NameError 也会阻止事件发布 |

**影响**：C3 修复一半，`operator.created` 事件载荷仍然缺少 `wechat_userid`，MySQL operators 表的 `wechat_userid` 列始终为空

**修复**：TASK-02 实现内容追加：同时修复 L3101-L3106 event payload，添加 `'wechat_userid': body.get('wechat_userid', '')`

| 编号 | 严重度 | 关联任务 | 发现 |
|------|--------|---------|------|
| **DA-03** | 🔴 **CRITICAL** | TASK-04 + TASK-06 | **`storage_layer.py` SQLite 表无 `overtime_hours` 列**：`schema_auto.py` 创建的两个表（L21 `process_sub_steps`、L43 `sub_steps`）的字段定义中只有 `overtime_minutes: INTEGER DEFAULT 0`，**没有 `overtime_hours` 列**。TASK-04 将 INSERT 和 SELECT 的字段名改为 `overtime_hours` 后，SQLite 执行 `INSERT INTO sub_steps (..., overtime_hours) VALUES (...)` 会抛出 `OperationalError: table sub_steps has no column named overtime_hours` |

**影响链**：TASK-03 改 `container_center_api.py` 的变量名 → TASK-04 改 `storage_layer.py` 的 INSERT/SELECT → SQLite 拒绝不认识列 → 所有报工写入失败

**修复方案**：TASK-06（schema_auto.py）必须在 TASK-04 之前执行（或合并执行），在 `schema_auto.py` 的 CREATE TABLE 语句中新增 `overtime_hours: REAL DEFAULT 0`。或：TASK-04 和 TASK-06 合并为一个批次，先加列再改写入

| 编号 | 严重度 | 关联任务 | 发现 |
|------|--------|---------|------|
| **DA-04** | 🔴 **CRITICAL** | TASK-03 | **TASK-03 与 TASK-04 的执行顺序依赖倒置**：文档将 TASK-03（改 container_center_api.py）和 TASK-04（改 storage_layer.py）放在批次1并行执行，标注为"无依赖"。但实际存在**隐性依赖链**：TASK-03 修改 `container_center_api.py:api_create_sub_step()` 将变量名改为 `overtime_hours`，该数据会通过 storage_layer 写入 SQLite；如果 TASK-04 未先完成（或未在同一批次中协调），storage_layer.py 的 INSERT 仍在用 `overtime_minutes` 列名，而 `overtime_hours` 列在 SQLite 中根本不存在 |

**影响**：并行执行时若 TASK-04 先执行完、TASK-03 后执行完，中途产生的时间窗口内数据写入失败

**修复方案**：TASK-03 的"无依赖"改为"依赖 TASK-04 和 TASK-06 的列名变更先完成"。或将 TASK-03/04/05/06 合并为一个批次，按 TASK-06(加列)→TASK-04(改读写)→TASK-05(改子handler)→TASK-03(改容器中心 API)的顺序串行执行

---

### 3. 数据模型不兼容（DA-05 ~ DA-07）

| 编号 | 严重度 | 关联任务 | 发现 |
|------|--------|---------|------|
| **DA-05** | 🔴 **HIGH** | TASK-08 | **`wechat` 与 `wechat_userid` 字段语义完全不同**：`container_center_api.py` 的硬编码 OPERATORS（L660）使用 `wechat` 字段存储**微信账号名**（如 `@张三`），不是企业微信 `userid`（如 `zhangsan@company`）。TASK-08 替换为 `_get_dynamic_operators()` 后，返回的数据来自 `container_config.OperatorConfig`，其字段名为 `wechat_userid`（企业微信唯一标识）。前端或外部 API 调用者如果读取 `op.wechat` 会得到 `undefined`，而读取 `op.wechat_userid` 才会获得正确的企业微信 ID |

**验证**：`container_center_api.py` L660: `{'operator_id': 'OP001', 'name': '张三', 'role': '工人', 'team_name': '一班', 'wechat': '@张三'}` — 全搜 `.get('wechat')` 无结果，说明外部调用者不使用 `wechat` 字段。但兼容性上字段名变化仍然对对外暴露的 API 有影响

**影响**：`/api/v4/operators` 和 `/api/operators` 的返回数据结构变化，`wechat` 变为 `wechat_userid`。如果外部系统调用了这些 API 并依赖 `wechat` 字段名，会返回空值

**修复方案**：TASK-08 中增加字段兼容映射：`_get_dynamic_operators()` 返回时在 `wechat_userid` 基础上也写入 `wechat` 字段（取 `wechat_userid` 值），保持向后兼容

| 编号 | 严重度 | 关联任务 | 发现 |
|------|--------|---------|------|
| **DA-06** | 🔴 **HIGH** | TASK-08 | **`operator_id` 值域改变导致 API 中断**：`container_center_api.py` 的硬编码 OPERATORS 使用自定义 ID 值（OP001、OP002、OP003），而 `_get_dynamic_operators()` 返回的是 `dispatch_center.py` 中 operators.json 的 `operator_id`（使用 MySQL auto-increment 整数或自定义字符串）。**任何引用 `OP001`/`OP002`/`OP003` 的外部代码都会失效** |

**验证**：`container_center_api.py` 有 3 处通过 `op['operator_id'] == operator_id` 匹配操作员（L1093、L1207、L1512），这些匹配依赖 `operator_id` 值连续可用。TASK-08 替换后，值从 'OP001' 变为 '1'（如果 dispatch_center 使用数字 ID），所有匹配逻辑全部中断

**影响**：容器中心的扫码报工、工单查询等功能可能无法匹配操作员

**修复方案**：TASK-08 需同时在 `_get_dynamic_operators()` 中保留 `operator_id` 字段名不变（仅值改变），并确保 dispatch_center 的 operator_id 格式兼容。或者在 `api_process_sub_steps` 等 3 个函数中补充操作员匹配兼容层

| 编号 | 严重度 | 关联任务 | 发现 |
|------|--------|---------|------|
| **DA-07** | 🔴 **MEDIUM** | TASK-03 + TASK-04 | **`int()` → `float()` 类型变更不兼容**：`container_center_api.py` L2491 原为 `int(data.get('overtime_minutes', 0) or 0)`（整型 5 分钟 = 5），改为 `float(data.get('overtime_hours', 0) or 0)`（浮点 5 分钟 = 0.0833小时）。但 `storage_layer.py` 写入 SQLite 时仍用 `INTEGER` 类型列，`float` 值被截断为整数（0.0833 → 0），导致数据精度丢失 |

**验证**：`schema_auto.py` L21: `'overtime_minutes': 'INTEGER DEFAULT 0'` — SQLite INTEGER 列存储 float 值会被截断。`storage_layer.py` L2068: `int(record.get(...))` 原代码也强转 int

**影响**：数据精度丢失（0.0833 → 0），前端看到的工时始终为 0

**修复方案**：TASK-06 修改 `schema_auto.py` 时，必须将 `overtime_hours` 列的类型定义为 `REAL DEFAULT 0`（SQLite 的 REAL = 8字节浮点数）。同时 `storage_layer.py` L2068 改为 `float(...)` 而非 `int(...)`

---

### 4. 审计修复建议的自我审计（DA-08 ~ DA-09）

| 编号 | 严重度 | 来源 | 发现 |
|------|--------|------|------|
| **DA-08** | 🟡 **MEDIUM** | 第一轮审计 DP-01 | **合并批次建议的潜在风险**：第一轮审计建议将 TASK-08 从批次3移至批次4，与 TASK-09 合并。但 TASK-08 是"容器中心动态加载操作员"，TASK-09 是"离职访问控制"。TASK-08 先做动态加载后，TASK-09 的 `_check_operator_enabled()` 才能通过动态列表查到离职状态。顺序正确。但 TASK-08 还涉及 3 处 `operator_id` 匹配逻辑的适配（DA-06），这些适配工作可能影响 TASK-09 的入口判断。**建议 TASK-08 放在 TASK-09 之前执行，但 TASK-08 的验收标准中需验证动态列表包含 enabled 字段** |

| **DA-09** | 🟡 **MEDIUM** | 第一轮审计 RC-03 | **`threading.Lock` 修复建议不完全正确**：第一轮审计建议 `STORED_ROUTES` 加锁解决线程安全。但 `sync_bridge.py` 的 `/sub-step-report` 端点（L313）本身就是 `threading.Thread(target=..., daemon=True).start()` 的异步模式。加了 `threading.Lock()` 仅能保证 STORED_ROUTES 字典的写入互斥，但不能保证 TCP 连接的线程安全性。**更安全的方案是使用 `threading.local()` 为每个线程维护独立的 requests Session** |

---

### 5. 深度审计结论

#### 严重度统计

| 等级 | 数量 | 编号 |
|------|------|------|
| 🔴 **CRITICAL** | 4 | DA-01（现有Bug）, DA-02（TASK-02遗漏）, DA-03（列不存在）, DA-04（依赖顺序错误） |
| 🔴 **HIGH** | 2 | DA-05（字段语义不兼容）, DA-06（operator_id值域改变） |
| 🔴 **MEDIUM** | 2 | DA-07（类型精度丢失）, DA-08（批次合并复查） |
| 🟡 **MEDIUM** | 1 | DA-09（Lock方案需改进） |

#### 与第一轮审计的差异

| 维度 | 第一轮审计 | 第二轮深度审计 |
|------|-----------|---------------|
| 方法 | 文档交叉校验 | 逐行代码路径追踪 + 类型链验证 |
| 发现 | 18项（覆盖面问题） | 9项（实现深度问题） |
| 等级分布 | 4🔴+6🟡+8🟢 | 4🔴+2🔴HIGH+2🔴MED+1🟡 |
| 关键增量 | — | **发现生产级 Bug（DA-01）**、列不存在（DA-03）、类型精度（DA-07） |

#### 实施前追加的强制检查点

| 顺序 | 检查点 | 验证方法 |
|------|--------|---------|
| 1 | **types链验证**：`int(overtime_minutes) → float(overtime_hours)` 在所有读取/写入点的一致性 | `grep -n "int.*overtime\|float.*overtime\|overtime_hours.*INTEGER\|overtime_hours.*REAL"` |
| 2 | **列存在验证**：SQLite 中 `overtime_hours` 列是否已通过 ALTER TABLE 或 CREATE TABLE 创建 | `python -c "import sqlite3; c=sqlite3.connect('xxx.db'); c.execute('PRAGMA table_info(sub_steps)').fetchall()"` |
| 3 | **字段名兼容验证**：`wechat` 字段名在 `container_center_api.py` 的 API 返回中是否存在 | 搜索 `.get('wechat')` 确认外部调用者是否依赖此字段 |
| 4 | **operator_id 值域验证**：dispatch_center 返回的 operator_id 格式是否兼容 OP001 风格的匹配逻辑 | 打印 `container_config.get_all_operators()` 的前 3 条记录 |

#### 修复后推荐批次策略（修订版）

```
批次1: TASK-01, TASK-02(含DA-02修补), TASK-05                              ← 无文件冲突任务先行
批次2: TASK-06(先修DA-03+DA-07 → schema加列+改类型) + TASK-04(再改读写字段,依赖批次2的列)  ← 批次2内部串行
批次3: TASK-03(改变量名,依赖批次2的字段名就绪)                                    ← 依赖批次2
批次4: TASK-07(含EventBus订阅+DA-01修复确认)                                    ← 独立执行
批次5: TASK-08(含DA-05/06兼容适配) → TASK-09(离职阻断) → TASK-10(前端过滤)         ← 按顺序串行
```

> 深度审计结论：发现**1处生产级运行时 Bug**（DA-01 `role` 未定义），以及 **3处 CRITICAL 实现漏洞**（DA-02~DA-04）。建议在实施任何 TASK 前，先修复 DA-01 现有 Bug。批次策略需要**调整为6个批次**（因 TASK-03/04/06 产生了实际的执行顺序依赖），而非原计划的5批次。按 P0→CRITICAL 修复顺序：DA-01 → DA-03 → DA-02+DA-04 → DA-07 → DA-05+DA-06。
