# 操作员ID与工时单位统一改造方案

## 一、改造背景

本次改造涉及两个独立但有交集的问题：

### 问题A: 操作员ID双标识方案
- **问题**：报工时 `operator_id` 传递的是企业微信 `userid`（字符串），与 MySQL `operators.id`（自增整数）类型不匹配，无法做 JOIN 关联
- **目标**：`operator_id` 存 MySQL `operators.id`（整数），`wechat_userid` 单独存微信ID（用于发消息）

### 问题B: 工时单位统一为小时
- **问题**：部分代码使用 `overtime_minutes`（分钟），部分已改为 `overtime_hours`（小时），存在混用不一致
- **目标**：全局统一使用 `overtime_hours`（小时），废弃 `overtime_minutes`

---

## 二、改造范围总体图

### 数据流全链路

```
前端页面（报工表单）
    │
    ├─── cs_report.html  ──→ container_center_api.py ──→ storage_layer.py (SQLite)
    │                                                   └──→ sub_step_handler.py (同步到MySQL)
    │
    └─── dispatch_center.js ──→ dispatch_center.py ──→ sync_bridge.py ──→ MySQL process_sub_steps
                                        │
                                        └──→ legacy_routes.py ──→ sync_bridge.py ──→ MySQL
```

| 层级 | 组件 | 数据库类型 |
|------|------|-----------|
| 晨圣(CS) | `cs_report.html` + `container_center_api.py` | SQLite (`chengsheng.db`, `wechat_container.db`) |
| 调度中心 | `dispatch_center.js` + `dispatch_center.py` | JSON文件（本地存储） |
| 同步桥 | `sync_bridge.py` | MySQL (`process_sub_steps`) |
| 本地同步 | `sub_step_handler.py` | SQLite (`wechat_container.db`, `chengsheng.db`) |

---

## 三、问题A: 操作员ID双标识方案（已完成）

### 3.1 当前推送内容

| 字段 | 当前值 | 问题 |
|------|--------|------|
| `operator_id` | 企业微信 userid（如 `"ZhuangQinglian"`） | 字符串，与 MySQL `operators.id` 整数不匹配 |
| `wechat_userid` | 无此字段 | 缺失 |

### 3.2 目标方案

| 字段 | 类型 | 来源 | 用途 |
|------|------|------|------|
| `operator` | VARCHAR | 前端选择 | 操作员名称，用于展示 |
| `operator_id` | INTEGER | SyncBridge 按名称查询 MySQL `operators.id` | 数据库关联 |
| `wechat_userid` | VARCHAR | 前端从 `/dispatch-center/operators` 获取 | 发送微信消息 |

### 3.3 已完成的修改

| 文件 | 修改内容 | 状态 |
|------|---------|------|
| [sync_bridge.py](../../mobile_api_ai/sync_bridge.py) | 新增 `wechat_userid` 参数；`sync_sub_step_report()` 始终按名称查 MySQL 获取整数 `id` 和 `wechat_userid`；INSERT 列新增 `wechat_userid`；自动建字段 | ✅ 完成 |
| [dispatch_center.js](../../mobile_api_ai/static/js/dispatch_center.js) | 移除 `operatorId` 查询，不再发送 `operator_id`，保留 `wechatUserid` | ✅ 完成 |
| [dispatch_center.py](../../mobile_api_ai/dispatch_center.py) | 仍接收空 `operator_id`（兼容旧版），新增 `wechat_userid` 透传 | ✅ 完成 |
| [legacy_routes.py](../../mobile_api_ai/api/legacy_routes.py) | `api_create_sub_step` 和 `_post_process_sub_step` 新增 `wechat_userid` 接收和传递 | ✅ 完成 |
| [storage_mysql.py](../../mobile_api_ai/storage_mysql.py) | `PSS_COLUMNS` 新增 `wechat_userid` | ✅ 完成 |

---

## 四、问题B: 工时单位统一为小时（部分完成）

### 4.1 已完成部分

| 文件 | 说明 | 状态 |
|------|------|------|
| [dispatch_center.js](../../mobile_api_ai/static/js/dispatch_center.js) | 报工表单使用 `overtime_hours` | ✅ 完成 |
| [dispatch_center.py](../../mobile_api_ai/dispatch_center.py) | 接收和传递 `overtime_hours` | ✅ 完成 |
| [sync_bridge.py](../../mobile_api_ai/sync_bridge.py) | 写入 MySQL 使用 `overtime_hours` | ✅ 完成 |
| [legacy_routes.py](../../mobile_api_ai/api/legacy_routes.py) | 接收和传递 `overtime_hours` | ✅ 完成 |
| [storage_mysql.py](../../mobile_api_ai/storage_mysql.py) | PSS_COLUMNS 添加 `overtime_hours` | ✅ 完成 |

### 4.2 遗留待修改（按优先级排列）

#### 🔴 高优先级 — 容器中心API（影响晨圣报工功能）

**文件: [container_center_api.py](../../mobile_api_ai/container_center_api.py)**

| 行号 | 当前代码（overtime_minutes） | 需改为（overtime_hours） |
|------|----------------------------|------------------------|
| 2491 | `overtime_minutes = int(data.get('overtime_minutes', 0))` | `overtime_hours = float(data.get('overtime_hours', 0) or 0)` |
| 2509 | `'overtime_minutes': overtime_minutes,` | `'overtime_hours': overtime_hours,` |
| 2526-2531 | 同步到 sync_bridge 只传4个字段，缺少 `qualified_qty`, `overtime_hours`, `remark`, `equipment_name` | 补充完整字段传递 |

**影响**: 晨圣扫描报工 → container_center_api → 存SQLite仍是`overtime_minutes` → 同步到MySQL也缺失

#### 🔴 高优先级 — 本地SQLite存储层

**文件: [storage_layer.py](../../mobile_api_ai/storage_layer.py)**

| 行号 | 当前代码 | 需修改 |
|------|---------|--------|
| 2055 | INSERT 列 `overtime_minutes` | 改为 `overtime_hours` |
| 2068 | `int(record.get('overtime_minutes', 0))` | `float(record.get('overtime_hours', 0) or 0)` |
| 2102 | 读取返回 `overtime_minutes` | 改为 `overtime_hours` |

**影响**: SQLite `process_sub_steps` 表仍存分钟字段

#### 🔴 高优先级 — 事件同步处理器

**文件: [sync/handlers/sub_step_handler.py](../../mobile_api_ai/sync/handlers/sub_step_handler.py)**

| 行号 | 当前代码 | 需修改 |
|------|---------|--------|
| 77 | INSERT 列 `overtime_minutes` | 改为 `overtime_hours` |
| 90 | `int(data.get('overtime_minutes', 0))` | `float(data.get('overtime_hours', 0) or 0)` |
| 113 | INSERT 列 `overtime_minutes` | 改为 `overtime_hours` |
| 127 | `int(data.get('overtime_minutes', 0))` | `float(data.get('overtime_hours', 0) or 0)` |

**影响**: 事件驱动同步到SQLite仍用分钟

#### 🟡 中优先级 — 数据库Schema定义

**文件: [schema_auto.py](../../mobile_api_ai/schema_auto.py)**

| 行号 | 当前代码 | 需修改 |
|------|---------|--------|
| 21 | `'overtime_minutes': 'INTEGER DEFAULT 0'` | 改为 `'overtime_hours': 'REAL DEFAULT 0'` |
| 43 | 同上 | 同上 |

**影响**: 自动建表时字段仍为分钟

#### 🟡 中优先级 — 晨圣报工前端页面

**文件: [templates/cs_report.html](../../mobile_api_ai/templates/cs_report.html)**

| 行号 | 当前代码 | 需修改 |
|------|---------|--------|
| 302 | input id=`overtime_minutes` | 改为 `overtime_hours` |
| 946 | `document.getElementById('overtime_minutes')` | 改为 `overtime_hours` |
| 957 | `overtime_minutes=parseInt(...)` | 改为 `overtime_hours=parseFloat(...) 或 0` |
| 976 | 请求体 `overtime_minutes` | 改为 `overtime_hours` |

**影响**: 晨圣报工前端输入和提交仍用分钟

#### 🟢 低优先级 — 数据迁移脚本

**文件: [scripts/tools/sync_container_to_cs.py](../../mobile_api_ai/scripts/tools/sync_container_to_cs.py)**

| 行号 | 内容 | 需修改 |
|------|------|--------|
| 254 | 注释 `overtime_minutes` | 改为 `overtime_hours` |
| 260 | ALTER 加 `overtime_minutes` | 改为 `overtime_hours` |
| 276 | 读取 `overtime_minutes` | 改为 `overtime_hours` |
| 289 | INSERT 列 `overtime_minutes` | 改为 `overtime_hours` |
| 291 | VALUES 传 `overtime_minutes` | 改为 `overtime_hours` |
| 294 | 打印信息 `overtime_minutes分钟` | 改为 `overtime_hours小时` |

**影响**: 数据迁移工具，低频率使用

---

## 五、执行计划

### 阶段1: 问题B高优先级修复（3个文件）

| 任务 | 文件 | 预估修改量 |
|------|------|-----------|
| B-01 | `container_center_api.py` | 3处修改 |
| B-02 | `storage_layer.py` | 3处修改 |
| B-03 | `sub_step_handler.py` | 4处修改 |

### 阶段2: 问题B中优先级修复（2个文件）

| 任务 | 文件 | 预估修改量 |
|------|------|-----------|
| B-04 | `schema_auto.py` | 2处修改 |
| B-05 | `cs_report.html` | 4处修改 |

### 阶段3: 问题B低优先级修复（1个文件）

| 任务 | 文件 | 预估修改量 |
|------|------|-----------|
| B-06 | `sync_container_to_cs.py` | 6处修改 |

### 依赖关系

```
B-01 (container_center_api)
  │  影响: 晨圣报工功能、同步到MySQL链路
  │  并行: 无（与B-02/B-03独立）
  │
B-02 (storage_layer)
  │  影响: SQLite本地存储
  │
B-03 (sub_step_handler)
  │  影响: 事件同步到SQLite
  │
  ├──→ B-04 (schema_auto，依赖B-02/B-03确定字段名)
  │
  ├──→ B-05 (cs_report.html，依赖B-01确认接口字段)
  │
  └──→ B-06 (sync_container_to_cs.py，最后处理)
```

---

## 六、验证方案

### 6.1 语法验证
```bash
python -c "import ast; ast.parse(open('xxx.py', encoding='utf-8').read())"
```

### 6.2 功能验证

| 测试场景 | 涉及组件 | 验证点 |
|---------|---------|--------|
| 调度中心报工 | dispatch_center.js → dispatch_center.py → sync_bridge.py → MySQL | `operator_id` 为整数，`wechat_userid` 为字符串 |
| 晨圣扫描报工 | cs_report.html → container_center_api.py → storage_layer.py → sync_bridge.py → MySQL | 同上 |
| 旧版API报工 | legacy_routes.py → sync_bridge.py → MySQL | 同上 |
| 微信机器人报工 | wechat_work_bot_v2.py → dispatch_center.py → sync_bridge.py → MySQL | `operator_id` 为空时自动按名称查询 |

### 6.3 回归验证
- 搜索项目中剩余的 `overtime_minutes` 确保无遗漏
- 搜索项目中未改的 `operator_id` 使用点位

---

---

## 七、问题C: 操作员数据同步写入 MySQL operators 表（新增）

### 7.1 问题分析

当前操作员数据仅保存在本地 `operators.json` 文件（通过 `container_config.py`），**MySQL `operators` 表不包含这些操作员**。

当 `sync_bridge.py` 按名称查询 MySQL `operators` 表获取 `id` 和 `wechat_userid` 时：
- 若本地已添加操作员但 MySQL 中不存在 → 查不到匹配记录 → `operator_id` 为 0、`wechat_userid` 为空
- 导致报工记录中 `operator_id` 丢失，无法做 JOIN 关联

### 7.2 目标方案

在以下三个操作节点，**同时写入 MySQL `operators` 表**：

| 操作节点 | 当前行为 | 目标行为 |
|---------|---------|---------|
| **新建操作员**（dispatch_center） | 仅写入 `operators.json` | 同时写入 MySQL `operators` 表 |
| **编辑操作员**（dispatch_center） | 仅更新 `operators.json` | 同时更新 MySQL `operators` 表 |
| **删除操作员**（dispatch_center） | 仅删除 `operators.json` | 同时删除/标记 MySQL `operators` 表 |
| **同步企业微信**（sync_operators_from_wechat） | 仅写入 `operators.json` | 同时写入 MySQL `operators` 表 |

### 7.3 MySQL operators 表结构

| 列名 | 类型 | 说明 |
|------|------|------|
| `id` | INT AUTO_INCREMENT PRIMARY KEY | 自增整数 ID（用于 process_sub_steps 的 operator_id 关联） |
| `name` | VARCHAR(100) NOT NULL | 操作员名称（唯一匹配依据，供 sync_bridge 按名称查询） |
| `operator_id` | VARCHAR(100) NOT NULL UNIQUE | 外部标识（同 operators.json 的 id，如 `"ZhuangQinglian"`） |
| `wechat_userid` | VARCHAR(100) DEFAULT '' | 企业微信用户 ID |
| `role` | VARCHAR(50) DEFAULT '操作员' | 角色 |
| `department` | VARCHAR(200) DEFAULT '' | 部门 |
| `enabled` | TINYINT(1) DEFAULT 1 | 启用状态（1=在职，0=离职停用） |
| `resigned_at` | DATETIME DEFAULT NULL | 离职时间（NULL 表示在职） |
| `created_at` | DATETIME DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

### 7.4 已完成的修改

| 文件 | 修改内容 | 状态 |
|------|---------|------|
| `dispatch_center.py` | `_ensure_operators_table()` 自动建表 | ↻ **待实现** |
| `dispatch_center.py` | `create_operator()` 新增 MySQL 写入逻辑 | ↻ **待实现** |
| `dispatch_center.py` | `update_operator()` 新增 MySQL 更新逻辑 | ↻ **待实现** |
| `dispatch_center.py` | `delete_operator()` 新增 MySQL 离职标记逻辑（`enabled=0, resigned_at=NOW()`） | ↻ **待实现** |
| `dispatch_center.py` | `sync_operators_from_wechat()` 新增 MySQL 写入逻辑 | ↻ **待实现** |

### 7.5 关键实现逻辑

```python
# 自动建表（在 dispatch_center.py 启动时或首次调用时执行）
def _ensure_operators_table():
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

def _sync_operator_to_mysql(op, action='upsert'):
    """同步单个操作员数据到 MySQL operators 表"""
    with get_db_cursor() as (cursor, conn):
        if action == 'delete':
            # 离职标记：不物理删除，仅标记为禁用并记录离职时间
            cursor.execute("""
                UPDATE operators SET enabled=0, resigned_at=NOW()
                WHERE operator_id = %s
            """, (op.id,))
        elif action == 'reactivate':
            # 再入职：恢复启用、清空离职时间、更新所有数据
            cursor.execute("""
                UPDATE operators SET
                    name = %s, wechat_userid = %s, role = %s, department = %s,
                    enabled = 1, resigned_at = NULL
                WHERE operator_id = %s
            """, (op.name, op.wechat_userid, op.role, op.department, op.id))
        else:
            cursor.execute("""
                INSERT INTO operators (operator_id, name, wechat_userid, role, department, enabled, notify_enabled, max_tasks)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    wechat_userid = VALUES(wechat_userid),
                    role = VALUES(role),
                    department = VALUES(department),
                    enabled = VALUES(enabled),
                    notify_enabled = VALUES(notify_enabled),
                    max_tasks = VALUES(max_tasks)
            """, (op.id, op.name, op.wechat_userid, op.role, op.department,
                  int(op.enabled), int(op.notify_enabled), op.max_tasks))
        conn.commit()
```

### 7.6 同步企业微信时的差异化策略

同步逻辑分三阶段执行：

**阶段1：遍历微信通讯录 → 新增/更新/激活**
| 场景 | 在职操作员（enabled=1，微信存在） | 离职操作员再入职（enabled=0，微信重新出现） | 全新操作员（MySQL 不存在） |
|------|-----------------------------------|---------------------------------------------|---------------------------|
| 操作 | 仅更新 `name`、`department` | 恢复 `enabled=1`、清空 `resigned_at=NULL`、更新全部字段 | 全字段插入 |
| 不变字段 | `role`、`enabled`、`notify_enabled`、`max_tasks` | — | — |
| operator_id | 不变 | 不变 | 自动使用微信 `userid` |

**阶段2：扫描 MySQL 中不存在的微信人员 → 标记离职**
- 遍历 `operators.json` 中所有操作员，检查是否出现在本次微信通讯录中
- 若不在通讯录中 → `enabled=0` + `resigned_at=NOW()`
- **不物理删除**，保留 `operator_id` 和历史报工记录关联

**阶段3：`operators.json` 与 MySQL 同步**
- 以上所有操作同时写入 `operators.json` 和 MySQL `operators` 表

**注意**：
- 已有操作员的 `role` 不做覆盖（保持用户手动设置的角色）
- 再入职时自动恢复 `enabled=1`，清空离职时间，`operator_id` 保持不变
- 离职人员再次入职后，报工记录的 `operator_id` 关联不受影响

### 7.7 数据一致性保障

| 机制 | 说明 |
|------|------|
| **主从关系** | `operators.json` 为 **主数据源**（操作入口），MySQL 为 **读副本**（供 sync_bridge 查询） |
| **双向写入** | 所有操作员增删改操作，先写 `operators.json`，后写 MySQL |
| **幂等性** | MySQL 使用 `ON DUPLICATE KEY UPDATE`，重复写入不产生异常 |
| **回滚保护** | MySQL 写入失败仅记录日志，不影响 `operators.json` 的主数据操作 |
| **自动建表** | 在 `dispatch_center.py` 启动时自动检测并建表 |

### 7.8 与前序改造的关联

```
问题A（双ID方案）已修改 sync_bridge.py 查询 MySQL operators 表获取整数 id
        ↓
        sync_bridge.py 按 name 查 MySQL operators 表
        ↓
问题C（本需求）确保 dispatch_center 创建的操作员能被写入 MySQL operators 表
        ↓
        sync_bridge.py 能查到正确的 operator_id（整数）和 wechat_userid
```

### 7.9 验证要点

| 验证场景 | 方法 | 预期结果 |
|---------|------|---------|
| 新建操作员 | 调度中心新增操作员 → 查 MySQL `operators` 表 | 记录存在，字段正确 |
| 编辑操作员 | 修改姓名/部门 → 查 MySQL | 字段已更新 |
| 删除操作员 | 调度中心删除操作员 → 查 MySQL | 标记 `enabled=0`，`resigned_at` 有值，记录仍在 |
| 同步企业微信（新人） | 触发同步 → 查 MySQL | 全字段新增 |
| 同步企业微信（离职） | 微信删除某人后同步 → 查 MySQL | 记录仍在，`enabled=0`，`resigned_at` 非空 |
| 同步企业微信（再入职） | 离职人员重新出现 → 查 MySQL | `enabled=1`，`resigned_at=NULL`，数据已更新 |
| 报工匹配 | 报工 → 查 `process_sub_steps.operator_id` | 值为 MySQL `operators.id`（整数） |

---

### 7.10 离职人员的访问控制

标记为离职（`enabled=0`）的操作员，在所有报工路径上必须被拒绝操作。

#### 受控代码路径

| # | 文件 | 函数/路由 | 当前状态 |
|---|------|-----------|---------|
| 1 | `wecom_auth.py` | `wecom_login()` L76-77 | ✅ **已有** `enabled` 检查，返回"账号已被禁用" |
| 2 | `dispatch_center.py` | `create_process_sub_step()` L7391 | ❌ 无离职检查 |
| 3 | `container_center_api.py` | `api_create_sub_step()` L2477 | ❌ 无离职检查 |
| 4 | `container_center_api.py` | 扫码报工相关路由 | ❌ 需检查 |
| 5 | `api/legacy_routes.py` | `api_create_sub_step()` L488 | ❌ 无离职检查 |

#### 检查逻辑（统一模式）

```python
def _check_operator_enabled(operator_name='', wechat_userid=''):
    """检查操作员是否在职，离职人员返回 None 和错误信息"""
    cc = _get_container_center()
    if not cc:
        return True, None  # 无容器中心时不阻断
    for op in cc.get_all_operators():
        if (op.name == operator_name or op.wechat_userid == wechat_userid) and not op.enabled:
            return False, f'操作员"{operator_name}"已离职，无法报工'
    return True, None
```

#### 注入位置（各报工入口）

| 文件 | 注入点 | 操作 |
|------|--------|------|
| `dispatch_center.py` | `create_process_sub_step()` 参数校验后、写入前 | 调用 `_check_operator_enabled(operator, wechat_userid)` |
| `container_center_api.py` | `api_create_sub_step()` 参数校验后、写入前 | 同上 |
| `api/legacy_routes.py` | `api_create_sub_step()` 参数校验后、写入前 | 同上 |

#### 前端交互限制

离职操作员不得出现在 **调度中心前端** 的可选操作员列表中，具体涉及以下 UI 位置：

| # | 前端位置 | 当前行为 | 改造方式 |
|---|---------|---------|---------|
| 1 | `dispatch_center.js:loadOperators()` 任务筛选下拉框 | 显示所有操作员 | 过滤掉 `enabled=false` 的操作员 |
| 2 | `dispatch_center.js:reassignTask()` 转派操作员对话框 | 列表包含所有操作员 | 过滤掉 `enabled=false` 操作员 |
| 3 | `dispatch_center.js:assignTask()` 任务指派 | 直接通过 operatorId 指派 | **后端校验** — 操作员已离职时返回错误并提示"已离职，建议删除操作权限" |
| 4 | `dispatch_center.py:advanceProcess()` 流程推进 | 输入操作人名称后后端处理 | **后端校验** — 若操作人已离职，返回错误 |

**提示文案**：当尝试将任务/流程分配给离职人员时，返回错误提示：
```
操作员"XXX"已离职，无法分配任务。请在"操作员管理"中确认该人员状态。
```

#### 后端列表接口过滤

`GET /operators` API 默认只返回 `enabled=true` 的操作员；如需查看所有操作员（含离职），增加 `?include_disabled=1` 参数。

| 场景 | 接口路径 | 修改 |
|------|---------|------|
| 任务筛选、分配使用 | `GET /operators`（无参数） | 默认过滤掉 `enabled=false` |
| 操作员管理列表 | `GET /operators?include_disabled=1` | 返回全部操作员（含离职，标记状态） |

#### 验证要点

| 场景 | 方法 | 预期结果 |
|------|------|---------|
| 离职人员登录 | 离职人员扫码登录 | 返回 403 "账号已被禁用" |
| 离职人员调度中心报工 | 离职操作员在调度中心报工 | 返回错误"已离职，无法报工" |
| 离职人员容器中心报工 | 离职操作员扫码报工 | 返回错误"已离职，无法报工" |
| 离职人员旧版API报工 | 直接调用 legacy API | 返回错误"已离职，无法报工" |
| 在职人员正常报工 | 在职操作员报工 | 正常通过 |
| 任务下拉框不显示离职 | 打开任务筛选下拉框 | 离职操作员不可见 |
| 任务过滤 | include_disabled=1 查全部 | 离职操作员可见并标记"已离职" |
| 指派离职人员 | 尝试 assignTask 给离职人员 | 后端返回错误，提示"已离职" |

---

## 八、方案审计发现与风险点（完整审计报告）

### 8.1 审计范围

| 维度 | 覆盖 |
|------|------|
| 问题A（双ID方案） | 5个已完成文件代码实现审计 |
| 问题B（工时单位统一） | 11个相关文件全量审计 |
| 问题C（写入MySQL+离职管理） | 方案设计 + 4个报工代码路径 + 前端UI |
| 竞态条件/并发 | 同步链路、缓存、双写场景 |
| 数据一致性 | 三源数据模型（operators.json + MySQL + 容器中心硬编码列表） |
| 异常处理 | 网络、数据库、回滚机制 |
| 遗漏路径 | 全链路代码路径搜索 |

---

### 8.2 🔴 CRITICAL 风险点（4个 — 必须修复后方可实施）

#### C1. `list_operators()` API 缺少 `wechat_userid` 返回

- **位置**：[dispatch_center.py:L3068-L3076](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L3068-L3076)
- **描述**：`list_operators()` 返回的 operator dict 未包含 `wechat_userid` 字段，但 JS 前端代码 [dispatch_center.js:L2785](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/static/js/dispatch_center.js#L2785) 期望 `found.wechat_userid`。导致报工表单提交时 `wechatUserid` 始终为 `undefined`
- **根因**：`get_cached_operators()`(L656) 已从 `OperatorConfig` 读取 `wechat_userid`，但 `list_operators()` 手动构造响应 dict 时遗漏此字段
- **影响**：报工记录写入 MySQL 时 `wechat_userid` 列始终为空，双ID方案形同虚设
- **修复指引**：在 L3076 的 operators_list 中添加 `'wechat_userid': op.get('wechat_userid', '')`

#### C2. 容器中心 API 同步 sync_bridge 只传4个字段，关键数据丢失

- **位置**：[container_center_api.py:L2526-L2531](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_api.py#L2526-L2531)
- **描述**：`api_create_sub_step()` 向 sync_bridge 的 POST 请求仅传入 `order_no`、`step_name`、`operator`、`quantity` 共4个字段。缺失 `wechat_userid`、`overtime_hours`(当前为 `overtime_minutes`)、`qualified_qty`、`equipment_name`、`remark`
- **影响**：从容器中心入口报工的数据，同步到 MySQL 后除4个字段外全为空，导致报表统计和审核功能不可用
- **修复指引**：补充 `qualified_qty`、`overtime_hours`、`wechat_userid`、`remark`、`equipment_name` 到请求体

#### C3. `create_operator()` 不传 `wechat_userid` → 新建操作员无法登录

- **位置**：[dispatch_center.py:L3089-L3097](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L3089-L3097)
- **描述**：`create_operator()` 函数创建 `OperatorConfig` 时未传入 `wechat_userid` 参数。`wecom_auth.py:L69` 登录匹配使用 `if op.wechat_userid == userid:` 精确匹配，新建操作员的 `wechat_userid` 为空字符串，导致无法通过企业微信登录
- **影响**：调度中心新建的操作员无法登录 APP
- **修复指引**：在 `OperatorConfig(...)` 参数中添加 `wechat_userid=body.get('wechat_userid', '')`，同时前端在新建表单中支持自动填充 `wechat_userid`

#### C4. 三源数据模型架构风险（operators.json + MySQL + 容器中心硬编码列表）

- **描述**：系统中存在 **3个独立的操作员数据源**，且缺乏主从同步机制：

| 数据源 | 文件/位置 | 管理方式 | 特性 |
|--------|----------|---------|------|
| operators.json | `container_config.py` | `ContainerConfig` 增删改 | 本地主源，全量数据 |
| MySQL operators 表 | 方案6.3 定义 | `dispatch_center.py` EventBus 同步 | 新表，依赖事件驱动 |
| OPERATORS 硬编码列表 | `container_center_api.py:L660-667` | 手动修改代码 | **完全独立，不与其他源同步** |

- **影响**：
  - 容器中心入口(`cs_report.html`)使用的操作员数据来自硬编码列表，与 operators.json 不同步
  - 新建操作员在 operators.json 中生效，但在容器中心侧不可见
  - MySQL operators 表的离职状态无法同步到容器中心侧
  - **离职人员在容器中心入口仍可正常报工**（绕过离职检查）
- **修复指引**：`container_center_api.py` 的 OPERATORS 列表应改为从 `container_config` 或 operators.json 动态加载

---

### 8.3 🔴 HIGH 风险点（6个 — 建议在问题C实施时同步修复）

#### H1. `operator.created` 事件未订阅，MySQL 写入无实际入口

- **位置**：[dispatch_center.py:L3101](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py#L3101)
- **描述**：`operator.created`(L3101) 和 `operator.deleted`(L3796) 事件已发布，但文档中设计的 EventBus 订阅器（方案7.5 伪代码）**实际代码中未注册监听器**。操作员数据变更不会同步到 MySQL `operators` 表
- **影响**：即使 MySQL `operators` 表已自动创建，操作员数据变更也不会写入。sync_bridge 按名称查找 MySQL operators 时将无匹配记录，`operator_id` 始终为 0
- **修复指引**：在 `__init_subscribers()` 或 `register_event_handlers()` 中注册 `operator.created` 和 `operator.deleted` 事件的 MySQL 同步处理函数

#### H2. 容器中心同步到 MySQL 时无事务保证

- **位置**：[container_center_api.py:L2530](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_api.py#L2530)
- **描述**：向 sync_bridge 发送 POST 请求后，**没有等待确认或验证写入结果**。`timeout=SHORT_TIMEOUT`、无 `try-except` 包裹。如果 sync_bridge 不可用或 MySQL 写入失败，数据静默丢失
- **影响**：容器中心报工"成功"但 MySQL 无记录，造成数据不一致且不可追溯
- **修复指引**：包裹 try-except，sync_bridge 返回非200时记录告警日志；考虑使用本地队列暂存失败请求

#### H3. sync_bridge 按名称查询 MySQL operators 表可能无结果

- **位置**：[sync_bridge.py:L204-L207](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/sync_bridge.py#L204-L207)
- **描述**：`sync_sub_step_report()` 按 `operator` 名称查询 MySQL `operators` 表。若表不存在或查询无结果，`final_operator_id` 和 `mysql_wechat_userid` 均为 None，随后使用 `operator_id or 0`(L209) 作为回退
- **影响**：在问题C完全实施并历史数据迁移之前，sync_bridge 写入的 `operator_id` 列始终为 0，`wechat_userid` 为空
- **修复指引**：问题C完成前增加降级策略（如从 operators.json 直接读取），或增加日志告警

#### H4. storage_mysql.py 同时保留 overtime_minutes 和 overtime_hours，形成垃圾列

- **位置**：[storage_mysql.py:PSS_COLUMNS](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/storage_mysql.py)
- **描述**：PSS_COLUMNS 同时包含 `overtime_minutes` 和 `overtime_hours`。`_ensure_columns()` 函数会比对后自动添加缺失列，但 **`overtime_minutes` 不会被自动删除**。旧列永久保留
- **影响**：MySQL 表形成垃圾列，影响数据整洁度和查询效率
- **修复指引**：PSS_COLUMNS 中移除 `overtime_minutes`，配合 `_ensure_columns()` 的可选清理逻辑

#### H5. `overtime_minutes → overtime_hours` 改造缺少统一的字段映射层

- **描述**：方案将6个文件按优先级分为3层，但**缺少统一的字段映射策略**，各层独立修改可能引入不一致：
  - 读取端：部分文件返回 `overtime_minutes`(如 storage_layer.py)，部分返回 `overtime_hours`(如 sync_bridge.py)
  - 写入端：前端 cs_report.html 发送 `overtime_minutes`，dispatch_center.js 发送 `overtime_hours`
  - 数据类型转换不一致：部分使用 `int()`，部分使用 `float()`
- **影响**：改造后可能出现"某条链路用小时、另一条用分钟"的混乱局面
- **修复指引**：在 `storage_layer.py` 的读取端添加兼容层（同时识别 `overtime_hours` 和 `overtime_minutes` 字段），确保向前兼容

#### H6. 容器中心 OPERATORS 硬编码列表导致离职检查无法覆盖

- **位置**：[container_center_api.py:L660-L667](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_api.py#L660-L667)
- **描述**：容器中心入口(`cs_report.html` → `container_center_api.py`)使用独立的 OPERATORS 硬编码列表，此列表无 `enabled` 标记
- **影响**：即使 dispatch_center.py 和 legacy_routes.py 加了离职检查，**容器中心入口仍然是一个不受控的缺口**。离职人员从晨圣扫码报工可轻松绕过离职限制
- **修复指引**：将 OPERATORS 列表改为动态加载（从 operators.json 读取），并保留 `enabled` 状态

---

### 8.4 🟡 MEDIUM 风险点（3个 — 建议关注，非实施阻塞）

#### M1. sync_bridge MySQL 写入线程安全不足

- **位置**：[sync_bridge.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/sync_bridge.py)
- **描述**：`sync_sub_step_report()` 在高并发报工时可能被多线程/协程并发调用。MySQL INSERT 使用自动提交模式，无显式事务包裹。`STORED_ROUTES` 和 `_initialized` 在 `ensure_tables()` 和 `ensure_table_fields()` 中无锁保护
- **影响**：极端情况下可能出现主键冲突或数据错乱

#### M2. 调用端对 sync_bridge 失败的静默吞异常

- **描述**：`container_center_api.py:L2530` 向 sync_bridge 发送请求的代码缺少 `try-except` 包裹。当 sync_bridge 服务不可用或网络中断时，异常未被捕获记录
- **影响**：报工操作"假成功"，排查问题时无日志可用

#### M3. `cs_report.html` 前端 input 名称与后端期望字段不一致

- **位置**：[cs_report.html](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/templates/cs_report.html)
- **描述**：前端 HTML input name 使用 `overtime_minutes`，但 `api_create_sub_step()` 接收后需要转换为 `overtime_hours`。即使改名完成，`container_center_api.py` 向 sync_bridge 也只传4个字段，改了字段名也无意义
- **影响**：工时数据在容器中心链路中始终丢失

---

### 8.5 🟢 LOW 风险点（2个 — 建议记录，远期修复）

#### L1. 数据迁移脚本使用 overtime_minutes

- **位置**：[scripts/tools/sync_container_to_cs.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/scripts/tools/sync_container_to_cs.py)
- **描述**：6处使用 `overtime_minutes`，运行时迁移数据的工时单位不一致

#### L2. 事件驱动同步缺乏幂等处理

- **描述**：`EventBus` 发布的事件（`operator.created`、`operator.deleted`）被重复消费（如服务重启后重新重放），可能导致 MySQL 数据重复或冲突。使用 `ON DUPLICATE KEY UPDATE` 可缓解 INSERT 场景，但 DELETE/离职标记场景无幂等保证

---

### 8.6 设计文档遗漏项

| # | 遗漏项 | 严重度 | 说明 |
|---|--------|--------|------|
| D1 | `list_operators()` 缺少 `wechat_userid` | 🔴 已被 C1 覆盖 | — |
| D2 | 容器中心入口无法实现离职检查 | 🔴 已被 C4/H6 覆盖 | 容器中心独立 OPERATORS 硬编码列表无离职标记 |
| D3 | 历史数据迁移方案缺失 | 🟡 | 未定义如何将 `operators.json` 已有操作员写入 MySQL |
| D4 | 回滚方案缺失 | 🟡 | 未定义 MySQL 写入失败时的本地回退策略（如暂存队列） |

---

### 8.7 风险优先级矩阵

```
影响\概率    高                    中                    低
─────────  ───────────────────  ───────────────────  ───────────────────
高影响      C1(list_operators)   H1(EventBus未接)     L2(事件幂等)
            C2(容器中心丢字段)     H3(sync查无数据)
            C3(登录死锁)          H4(垃圾列)
            C4(三源数据)

中影响        H2(无事务保证)       M1(线程安全)
                                      M2(静默吞异常)

低影响                                          M3(字段不匹配)
                                                L1(脚本不一致)
```

### 8.8 结论

| 评估项 | 结果 |
|--------|------|
| 方案完整性 | ⚠️ 问题A/B 设计合理，问题C 存在关键遗漏（list_operators wechat_userid 缺失、容器中心离职检查未覆盖） |
| 技术可行性 | ✅ 架构可行，三源数据模型需整合（operators.json + MySQL + 容器中心硬编码列表） |
| 数据一致性 | ❌ 三源系统间缺乏同步机制，sync_bridge 写入字段不完整 |
| 异常处理 | ⚠️ sync_bridge 调用端部分路径静默吞异常，MySQL 写入无事务保证 |
| 并发安全 | ⚠️ 线程级安全不足，高并发下可能数据错乱 |
| 回滚能力 | ❌ 未定义回退策略，MySQL 写入失败报工数据可能丢失 |

**建议修复顺序**：C1 → C2 → C3 → C4 → H1 → H3 → H6 → H2 → H4 → H5 → M1 → M2 → M3 → L1 → L2

---

### 8.9 再次审计补充发现（新增风险点）

第一轮审计报告写入方案文档后，进行第二轮交叉审计，发现以下 **5个新增风险点**（第一轮未覆盖）：

#### R1 🟠 HIGH — 实施顺序依赖风险

- **描述**：问题B（容器中心 `api_create_sub_step` 改造）和问题C（EventBus 注册、MySQL operators 表同步）存在**交叉依赖**：
  - C2 修复（容器中心向 sync_bridge 传全字段）依赖问题B 先完成 `overtime_minutes→overtime_hours` 改造
  - H1 修复（EventBus 订阅）依赖问题C 的 MySQL operators 表先建好
  - H3 修复（sync_bridge 查表降级）依赖 H1 先完成
- **影响**：若按 "A→B→C" 顺序实施，中间状态容器中心的 `api_create_sub_step` 即使补了全字段，传的还是 `overtime_minutes`，导致 MySQL 中 `overtime_hours` 列仍为空
- **根因**：方案将问题A/B/C 视为平行改造，但修复 C2 时必须同时改问题B 的容器中心代码
- **缓解措施**：实施时将 C2 与问题B 的 `container_center_api.py` 改造合并为同一个子任务，禁止分拆

#### R2 🟠 MEDIUM — `_check_operator_enabled()` 回退绕过

- **位置**：[dispatch_center.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center.py)
- **描述**：`_check_operator_enabled()` 中若 `_get_container_center()` 返回 None（容器中心连接失败），函数返回 `(True, None)`，即**放行所有操作员**。此时离职人员也可通过调度中心报工
- **影响**：容器中心服务不可用期间，离职检查形同虚设
- **缓解措施**：增加第二层检查——直接读取 MySQL `operators` 表作为后备；或返回 `(False, "容器中心不可用，无法验证操作员状态")` 阻断操作

#### R3 🟠 MEDIUM — 前端不传 `wechat_userid` 导致 C3 修复无效

- **位置**：[dispatch_center.js:L2785-L2787](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/static/js/dispatch_center.js#L2785-L2787)
- **描述**：`create_operator()` 后端虽然新增了 `wechat_userid` 参数接收，但**新建操作员的弹窗表单未包含 `wechat_userid` 输入框**。用户手动创建的操作员 `wechat_userid` 始终为空字符串，C3 修复无效
- **影响**：调度中心新建操作员仍然无法登录 APP
- **缓解措施**：新建操作员弹窗增加 "企业微信账号" 输入框（自动带出匹配建议）；或严格限定手动创建仅用于不登录 APP 的辅助操作员

#### R4 🟠 MEDIUM — EventBus 事件时序竞争

- **描述**：`operator.created` 事件通过 EventBus 发布，MySQL 同步处理器异步执行。但 sync_bridge 的 `sync_sub_step_report()` 在报工时立即按名称查询 MySQL `operators` 表。若报工发生在操作员创建后极短时间内（<100ms），MySQL 写入可能尚未完成，导致报工时查不到该操作员，`operator_id` 降级为 0
- **影响**：快速连续操作（创建操作员 → 立即报工）导致 operator_id=0
- **缓解措施**：EventBus 同步处理器使用同步模式（同线程），或 MySQL 查询增加 2-3 次重试（间隔 50ms）

#### R5 🟢 LOW — `event_bus.subscribe()` 重复注册风险

- **描述**：如果 `register_event_handlers()`（或 `__init_subscribers()`）在服务生命周期内被多次调用（如热重载、Flask reloader），同一事件处理函数被重复订阅，导致操作员数据被多次写入 MySQL（`ON DUPLICATE KEY UPDATE` 虽可缓解 INSERT 场景，但 DELETE 场景无幂等保证）
- **影响**：`operator.deleted` 处理函数被重复调用时，MySQL 会多次执行 `UPDATE operators SET enabled=0`（幂等），影响不大；但若未来新增非幂等操作，热重载可能导致重复执行
- **缓解措施**：EventBus 订阅前先检查是否已订阅，或在服务初始化阶段只调用一次注册函数

---

## 九、风险与回退

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| `overtime_hours` 字段在 SQLite 表不存在 | INSERT 报错 | `schema_auto.py` 已定义，`ensure_table()` 自动建字段 |
| MySQL `process_sub_steps` 无 `wechat_userid` 字段 | INSERT 报错 | `sync_bridge.py` 已添加 `ALTER TABLE` 自动建字段逻辑 |
| 旧数据 `overtime_minutes` 与新代码不兼容 | 查询旧记录无值 | 读取时 `get('overtime_hours', 0)` 提供默认值 |
