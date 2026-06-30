# 现有程序改动清单（逐文件详细方案）

## 本文档目标

基于 DESIGN_第四代存储+解耦合.md 和 10 个 TASK 文件，逐一列出每个现有文件需要改什么、怎么改、为什么改。**用于在开始编码前确认方案完整性**。

---

## 零、完整数据流分析（所有涉及的文件）

### 部署拓扑

```
电脑A (主软件) ──┐
电脑B (主软件) ──┤──LAN──→ 服务器(唯一实例):
电脑C (主软件) ──┘          │
                            ├── 调度中心(唯一):5003
                            │   ├── wechat_server.py (Flask入口, ~30处直引)
                            │   └── dispatch_center.py (流程引擎, ~80处直引)
                            │
                            ├── 容器中心(唯一):5002
                            │   ├── container_center_api.py (Flask入口, 注册蓝图)
                            │   ├── container_center_v5.py (核心库, 内部改造)
                            │   └── storage_layer.py (弃用标记)
                            │
                            └── (其他蓝图服务)
                                │
                              互联网 → wechat_cloud:5006 (不需改动)
```

### Flow 1：主软件 → 调度中心 → 存储 → 微信发送

```
主软件 ──LAN──→ wechat_server:5003 /api/sync/task & /api/sync/report
  │
  ├── _container_center.collect_material/quality/report()    ❌ ~10处直引
  ├── _container_center.get_tasks_by_order()                 ❌
  ├── _container_center.get_task_by_order()                  ❌
  ├── _container_center.get_task()                           ❌
  ├── _container_center.complete_task()                      ❌
  ├── _container_center.update_task_progress()               ❌
  ├── _callback_sender.send() → 主软件回调URL               ✅ 保留
  │
  └──→ 经过流程判断后:
        dispatch_center.py
        ├── cc.storage.xxx()              ❌ ~16处
        ├── cc.distributor.xxx()          ❌ ~4处
        ├── cc.config.xxx()               ❌ ~2处
        └── _send_wechat_via_cloud()      ❌ ~18处 → CloudPoller → wechat_cloud:5006
```

### Flow 2：微信回复 → 调度中心 → 主软件回写

```
微信回复 → wechat_cloud:5006 → message_store
  → CloudPoller 轮询 → handle_cloud_message
  → wechat_server_handlers.py → WechatMessageHandler
  → _container_center.storage.xxx()                     ❌ 直引
  → _callback_sender.send() → 主软件回调URL            ✅ 保留
```

### 总结：所有需要改的直引路径

| 文件 | 改动词量 | 直引目标 |
|------|:--------:|---------|
| `dispatch_center.py` | **~80处** | cc.storage / cc.distributor / cc.config / _send_wechat / _get_container_center |
| `wechat_server.py` | **~30处** | _container_center.xxx() |
| `container_center_v5.py` | **中** | 内部新增 DocumentStore 双写 |
| `container_center_api.py` | **中** | 注册新蓝图 |
| `wechat_cloud.py` | **0** | 独立HTTP服务，不动 |

---

## 一、总览：文件改动状态

| 文件路径 | 状态 | 改动量 | 涉及阶段 |
|---------|:----:|:------:|:--------:|
| `dispatch_center.py` | **✅ P0完成** | ~16处cc.storage替换为SDK（0语法错误） | P0已完成，P1/P3待续 |
| `wechat_server.py` | **✅ P0完成** | ~12处_container_center存储调用替换为SDK（0语法错误） | P0已完成 |
| `container_center_v5.py` | **改造** | 中（方法内部改存储层调用） | 第一阶段 |
| `container_center_api.py` | **改造** | 中（注册新蓝图+路由调整） | 第一阶段 |
| `storage_layer.py` | **改造** | 小（保留+标记弃用） | 第一阶段 |
| `app.py` | **改造** | 小（启动配置调整） | 第三阶段 |
| `config.py` | **改造** | 小（新增环境变量读取） | 第一阶段 |
| `integration/timeout_reminder.py` | **删除** | — | 第三阶段 |
| `templates/dispatch_center.html` | **改造** | 中（新增告警配置区域） | 第三阶段 |
| `container_center/` (12个新文件) | **新增** | — | 各阶段 |

> 新增文件见 DESIGN 文档第 2.3 节和 TASK 1.1～3.3，本文档**只分析现有文件如何改造**。

---

## 二、逐文件改动详细方案

---

### 文件 1：`dispatch_center.py`（最大改动量，2056 行）

#### 总体策略

分三阶段渐进改造，每阶段只替换一类引用，不破坏现有业务逻辑。

```
当前状态：dispatch_center.py
  ├── _get_container_center()      → 创建 cc 实例（29处调用者）
  ├── cc.storage.xxx()             → P0: 替换为 client.xxx()（~16处）
  ├── cc.distributor.xxx()         → P1: 替换为 client.xxx()（4处）
  ├── cc.config.xxx()              → P1: 替换为 client.xxx()（2处）
  ├── _send_wechat_via_cloud()   → P0: 替换为 client.send_message()（~18处）
  ├── _check_overdue_tasks()       → P1: 迁移到容器中心 AlertEngine
  └── _check_outsource_reminders() → P1: 迁移到容器中心 AlertEngine
```

---

#### 阶段一改动（P0，对应 TASK 1.4）

##### 改动 1.1：替换 `cc.storage.xxx()` 为 `client.xxx()`

| 方法 | 次数 | 当前代码 | 替换为 | 逻辑说明 |
|------|:----:|---------|--------|---------|
| `get_packages(limit=N)` | **6处** | `cc.storage.get_packages(limit=100)` | `client.get_packages(doc_type='work_order', limit=100)` | 兼容方法内部调 `query_documents()`，返回 List[Dict] 格式不变 |
| `get_package(id)` | **3处** | `cc.storage.get_package(pkg_id)` | `client.get_package(pkg_id)` | 内部调 `get_document()`，返回 Dict 格式不变 |
| `save_package(pkg)` | **2处** | `cc.storage.save_package(pkg)` | `client.save_package(pkg)` | 内部调 `create_document()`，返回新建 ID |
| `update_package(id, fields)` | **3处** | `cc.storage.update_package(id, fields)` | `client.update_document(id, fields)` | 内部调 `PUT /api/container/data/<id>` 局部更新 |
| `update_package_status(id, status)` | **2处** | `cc.storage.update_package_status(id, status)` | `client.update_document_status(id, status)` | 内部调 `PUT /api/container/data/<id>/status` |

**改动方式**：
1. 在 `dispatch_center.py` 顶部（约 L15）新增 `client` 导入和初始化：
   ```python
   from container_center.client import ContainerCenterClient
   _cc_client = None
   def _get_client():
       global _cc_client
       if _cc_client is None:
           _cc_client = ContainerCenterClient()
       return _cc_client
   ```

   > 注意：暂不删除 `_get_container_center()`，P0 阶段需要它提供 `cc.distributor` 和 `cc.config` 访问。

2. 逐行替换 ~16 处 `cc.storage.xxx()` 为 `client.xxx()`，保留原有的 try/except/日志。

3. 替换后运行验证：调度中心启动后数据读写正常。

**✅ dispatch_center.py P0 完成状态（2026-05-13）：**
- ~16处 `cc.storage.xxx()` 全部替换为 `_get_client().xxx()` SDK 调用
- 0个语法错误（GetDiagnostics 验证通过）
- 0个残留 `cc.storage` 或 `hasattr.*storage` 引用（grep 验证通过）
- `_send_wechat_via_cloud` 替换标记为 P1（TASK 2.3）

##### 改动 1.2：替换 `_send_wechat_via_cloud()` 为 `client.send_message()`

| 调用位置 | 次数 | 当前代码 | 替换为 | 逻辑说明 |
|---------|:----:|---------|--------|---------|
| 直接调用（assign_task/reassign_task/cancel_task/advance_process/reject_process_step 等） | **3处直接** | `_send_wechat_via_cloud(to, content)` | `_get_client().send_message(content=content, to=to)` | API 调用，移除本地函数依赖 |
| 间接调用（通过 _send_wechat_via_cloud 转发） | **~15处间接** | 同上 | 同上 | 同上 |

**改动方式**：
1. 搜索全部 `_send_wechat_via_cloud(` 出现位置
2. 替换为 `_get_client().send_message(content=..., to=...)`，注意参数顺序调整（原函数 `to` 在前，SDK 方法 `content` 在前）
3. 保留原 try/except 异常处理
4. **暂不删除 `_send_wechat_via_cloud()` 函数定义**（P1 完成后统一删除）

---

#### 阶段二改动（P1，对应 TASK 2.3）

##### 改动 2.1：替换 `cc.distributor.distribute()` 为 `client.distribute()`

| 调用位置 | 行号参考 | 当前代码 | 替换为 |
|---------|:--------:|---------|--------|
| `assign_task` | ~L667-669 | `cc.distributor.distribute(task_id, operator_id)` | `_get_client().distribute(task_id, operator_id)` |
| `batch_assign` | ~L822-823 | `cc.distributor.distribute(...)` | `_get_client().distribute(...)` |
| `create_outsource_record` | ~L1690 | `cc.distributor.distribute(...)` | `_get_client().distribute(...)` |
| `assign_outsource_record` | ~L1722 | `cc.distributor.distribute(...)` | `_get_client().distribute(...)` |

##### 改动 2.2：替换 `cc.config.get_*_operators*()` 为 `client.get_operators()`

| 调用位置 | 行号参考 | 当前代码 | 替换为 |
|---------|:--------:|---------|--------|
| — | ~L349-350 | `cc.config.get_all_operators()` | `_get_client().get_operators()` |
| — | ~L411 | `cc.config.get_operators_by_department(dept)` | `_get_client().get_operators(department=dept)` |

##### 改动 2.3：替换 `cc.collect_outsource()` 为 `client.create_document()`

| 调用位置 | 当前代码 | 替换为 |
|---------|---------|--------|
| 1处 | `cc.collect_outsource(data)` | `client.create_document(doc_type='outsource', data=data)` |

##### 改动 2.4：告警列表查询和告警忽略

| 调用位置 | 当前代码 | 替换为 |
|---------|---------|--------|
| 告警列表查询（约 L1863 路由 `GET /alerts`） | 从本地 data 查询 | `client.get_alert_list(level, alert_type)` |
| 告警忽略（约 L1902 路由 `POST /alerts/<id>/dismiss`） | 本地更新 | `client.dismiss_alert(alert_id)` |

##### 改动 2.5：移除告警定时器调用

| 位置 | 行号参考 | 操作 |
|------|:--------:|------|
| `start_background_cheduler` 函数体 | ~L2038-2056 | 移除 `_check_overdue_tasks()` 和 `_check_outsource_reminders()` 两行调用 |
| 保留空定时器或移除整个函数 | — | 暂保留框架，等 T3.1 清理 |

---

#### 阶段三改动（清理，对应 TASK 3.1）

##### 改动 3.1：删除 `_get_container_center()` 函数

**前提**：P0 + P1 全部替换完成，确认 `cc.xxx()` 已无任何调用。

删除函数定义（约 L317-335），同时：
- 清理引用的 import（`from wechat_server import container_center` 等）
- 清理延迟导入

##### 改动 3.2：删除 `_send_wechat_via_cloud()` 函数

**前提**：全部替换为 `client.send_message()`。

删除函数定义（约 L33-57），清理 import。

##### 改动 3.3：清理无用的 import

| 待清理的 import | 原因 |
|----------------|------|
| `from container_center_v5 import ...` 或同类直引用 | 全部通过 SDK 调用 |
| `from integration.timeout_reminder import ...` | timeout_reminder.py 将被删除 |
| 与 `_get_container_center()` 相关的延迟导入 | 函数已删除 |

---

### 文件 2：`wechat_server.py`（2541 行，新增 P0 改动）

#### 总体策略

**之前 MODIFICATION_PLAN 遗漏了这个文件的大头改动。** `wechat_server.py` 是主软件数据进入系统的第一站，有约 30 处 `_container_center` 直引。

同步接口（`/api/sync/*`）保留在此文件（选项A），内部替换直引为 SDK 调用。

#### 具体改动

##### 改动 2.1：初始化 SDK 客户端

在文件顶部，与 `_container_center` 初始化的同区域（~L129-190），新增：

```python
# Phase 1: SDK客户端（替代直引 container_center）
from container_center.client import ContainerCenterClient
_cc_client = None

def _ensure_cc_client():
    global _cc_client
    if _cc_client is None:
        _cc_client = ContainerCenterClient()
    return _cc_client
```

保留 `_container_center` 的初始化逻辑，**P0 阶段两个并行存在**，方便分步替换。

##### 改动 2.2：替换 ~30 处 `_container_center.xxx()` 

将所有 `_container_center.xxx()` 替换为 `_ensure_cc_client().xxx()`：

| 路由/位置 | 调用的方法 | 处数 | 替换为 |
|----------|-----------|:----:|--------|
| `/api/sync/task` (L440-481) | `collect_material`/`collect_quality`/`collect_report`/`get_tasks_by_order` | ~6 | `_ensure_cc_client().collect_material(...)` 等 |
| `/api/sync/report` (L570-625) | `get_task_by_order`/`get_task`/`complete_task`/`update_task_progress` | ~6 | `_ensure_cc_client().complete_task(...)` 等 |
| `/api/sync/tasks` (L952-964) | `get_tasks_by_operator`/`get_all_tasks` | ~3 | `_ensure_cc_client().get_tasks_by_operator(...)` |
| `/api/sync/tasks/<id>` (L982-985) | `get_task` | ~2 | `_ensure_cc_client().get_task(...)` |
| `/api/sync/task/<order>/status` (L1007-1011) | `get_tasks_by_order` | ~2 | `_ensure_cc_client().get_tasks_by_order(...)` |
| `/health`、`/status` (L676-687) | 可用性检查 | ~2 | `_ensure_cc_client().health_check()` |
| `_notifier.initialize` (L190) | 传递引用 | ~1 | 保留（notifier 是流程引擎所需） |
| `container_center = _container_center` (L185) | 导出模块变量 | ~1 | T3.1 删除 |
| 各处 `if _container_center:` 检查 | 存在性判断 | ~6 | 替换为 `if _ensure_cc_client():` 或 `if _cc_client:` |

##### 改动 2.3：不改动的部分

| 部分 | 原因 |
|------|------|
| `_callback_sender`、`_callback_url` | 回调逻辑在调度中心本地，通过 HTTP 回写主软件，不需要走容器中心 |
| `_app_bot` | 企业微信应用机器人，调度中心本地管理 |
| `WechatMessageHandler` | 微信消息处理器，涉及微信指令解析，不依赖存储 |
| `_notifier` / `_message_hub` / `_command_manager` | 流程引擎的组件，与存储无关 |
| `_drift_detector` | 时间漂移检测，独立功能 |

##### 改动 2.4：P0 完成状态（2026-05-13）

| 替换项 | 状态 | 说明 |
|-------|:----:|------|
| `collect_material/quality/report` → `save_package(doc_type=...)` | ✅ | sync 创建任务 3处 |
| `get_tasks_by_order` → `get_packages()` + 客户端过滤 | ✅ | sync + get_task_status 2处 |
| `get_task_by_order` → `get_packages()` + 客户端过滤 | ✅ | check_task 1处 |
| `get_task` → `get_package()` | ✅ | sync_report 1处 |
| `complete_task` → `update_document('work_order', ...)` | ✅ | sync_report 1处 |
| `update_task_progress` → `update_document('work_order', ...)` | ✅ | complete_task 1处 |
| `get_tasks_by_operator` → `get_packages()` + 客户端过滤 | ✅ | get_sync_tasks 1处 |
| `get_all_tasks` → `get_packages()` | ✅ | get_sync_tasks 1处 |
| `collect_outsource` → `create_document('outsource', ...)` | ✅ | publish_outsource 1处 |
| `_container_center.distributor.distribute` | ⏳ P1 | publish_outsource 保留 |
| 语法错误 | 0 | GetDiagnostics 验证通过 |
| 残留 `_container_center` 存储调用 | 0 | grep 验证通过 |

---

### 文件 3：`container_center_v5.py`（1067 行）

#### 总体策略

这个文件不会被删除——它是当前所有容器中心功能的核心实现。改造策略是：

1. **第一阶段**：新增的存储层（DocumentStore）作为内部新路径，ContainerCenter 类的方法**内部切换**到新存储层
2. **第二阶段**：ContainerCenter 作为**兼容性适配器**，原有方法签名不变，内部调新 API
3. **第三阶段**：不再被 dispatch_center.py 和 wechat_server.py 直引用后，可作为独立模块存在

#### 具体改动

##### 改动 3.1：`ContainerCenter.__init__` 初始化新存储层

```python
# 当前：初始化 SQLiteStorage
self.storage = SqliteStorage(db_path)

# 改为：同时初始化新存储层（兼容模式）
from container_center.storage.router import DatabaseRouter
from container_center.storage.document_store import DocumentStore
self._router = DatabaseRouter()
self._doc_store = DocumentStore(self._router)
# 原有 self.storage 保留（旧代码兼容）
```

##### 改动 3.2：方法内部双写/优先新存储

适用于所有被外部调用的方法。以 `get_packages()` 为例：

```python
def get_packages(self, limit=100, status=None):
    try:
        return self._doc_store.query_documents(
            doc_type='work_order', status=status, size=limit
        )
    except Exception:
        logger.warning("新存储层不可用，回退到旧存储")
        return self.storage.get_packages(limit=limit, status=status)
```

完整的方法覆盖清单：

| 方法 | 外部调用文件 | 替换策略 |
|------|------------|---------|
| `get_packages` | dispatch_center | 新存储优先，旧存储 fallback |
| `get_package` | dispatch_center | 同上 |
| `save_package` | dispatch_center | 同时写新旧存储（双写确保不丢数据） |
| `update_package` | dispatch_center | 优先新存储，旧存储同步更新 |
| `update_package_status` | dispatch_center | 同上 |
| `get_all_tasks` | wechat_server | 新存储优先 |
| `get_task` | wechat_server | 同上 |
| `get_task_by_order` | wechat_server | 同上 |
| `get_tasks_by_order` | wechat_server | 同上 |
| `get_tasks_by_operator` | wechat_server | 同上 |
| `complete_task` | wechat_server | 新存储优先 |
| `update_task_progress` | wechat_server | 同上 |
| `collect_material` | wechat_server | 新存储创建文档，旧存储同写 |
| `collect_quality` | wechat_server | 同上 |
| `collect_report` | wechat_server | 同上 |
| `get_all_operators` | dispatch_center | 移入 ConfigStore |
| `distribute` | dispatch_center | 移入 API 层 |

##### 改动 3.3：`shutdown()` 中关闭新存储层连接

```python
def shutdown(self):
    if hasattr(self, '_router'):
        self._router.close_all()
    self.storage.close()
```

---

### 文件 4：`container_center_api.py`（1022 行，~36 条路由）

#### 总体策略

这个文件是 Flask 应用入口，目前包含约 36 条路由（任务管理、外协管理、配置管理等）。改造策略：

1. **注册新蓝图**：将新的 `container_center/api/` 蓝图注册到此应用
2. **路由不动**：现有路由不动，保持向后兼容
3. **内部改造**：逐步将现有路由内部实现切换到新存储层

#### 具体改动

##### 改动 4.1：注册新 API 蓝图

```python
# 在 create_app() 或类似初始化函数中
from container_center.api.data_api import data_bp
from container_center.api.message_api import message_bp
from container_center.api.distribute_api import distribute_bp
from container_center.api.config_api import config_bp
from container_center.api.alert_api import alert_bp

app.register_blueprint(data_bp, url_prefix='/api/container')
app.register_blueprint(message_bp, url_prefix='/api/container')
app.register_blueprint(distribute_bp, url_prefix='/api/container')
app.register_blueprint(config_bp, url_prefix='/api/container')
app.register_blueprint(alert_bp, url_prefix='/api/container')
```

##### 改动 4.2：初始化 DatabaseRouter

在 `container_center_api.py` 启动时初始化 DatabaseRouter 并传递给各 blueprint：

```python
router = DatabaseRouter()
data_api.router = router
message_api.router = router
...
```

##### （不改动）现有路由完整保留

以下路由**不动**（P0/P1 改造不涉及它们）：

| 路由前缀 | 用途 | 状态 |
|---------|------|:----:|
| `/health` | 健康检查 | 不动 |
| `/api/pool/status` | 池状态 | 不动 |
| `/api/tasks/*` | 任务管理 | 不动 |
| `/api/process-records/*` | 工序记录 | 不动 |
| `/api/outsource/*` | 外协管理 | 不动 |
| `/api/internal/config/*` | 内部配置 | 不动 |

---

### 文件 5：`storage_layer.py`（~2200 行）

#### 总体策略

`SQLiteStorage` 类（~1400 行）将被新存储层**逐步替代**，而不是立即删除。

#### 具体改动

##### 改动 5.1：标记弃用

在文件顶部和 `SqliteStorage` 类定义处添加弃用标记：

```python
# 已弃用: 请使用 container_center.storage.document_store.DocumentStore
# 此模块将在第四阶段移除
```

---

### 文件 6：`config.py`

#### 具体改动

新增环境变量读取（不硬编码默认值）：

```python
# 容器中心配置
CC_DATA_DIR = os.getenv('CC_DATA_DIR')
CC_PORT = os.getenv('CC_PORT')

# 调度中心容器中心连接
CONTAINER_CENTER_URL = os.getenv('CONTAINER_CENTER_URL')

# 共享鉴权密钥（不设默认值，缺失则启动报错退出）
SHARED_SECRET = os.getenv('SHARED_SECRET')
```

---

### 文件 7：`app.py`

#### 具体改动

条件性初始化，支持容器中心和调度中心在同一进程的开发模式：

```python
import os
RUN_MODE = os.getenv('RUN_MODE', 'production')

if RUN_MODE == 'production':
    app = create_app()
else:
    from container_center.api import register_all_blueprints
    app = create_app()
    register_all_blueprints(app)
```

---

### 文件 8：`integration/timeout_reminder.py`（198 行）

#### 操作

**删除**（对应 TASK 3.1）

#### 前提

- T2.1 告警引擎已迁移完成
- 确认 `dispatch_center.py` 和其他文件不再 import 此模块

---

### 文件 9：`templates/dispatch_center.html`

#### 总体策略

调度中心前端模板，新增告警规则配置区域，不动现有页面结构。

#### 具体改动

##### 改动 9.1：新增告警配置入口（导航栏）

```html
<li><a href="#alert-config" onclick="showAlertConfig()">告警配置</a></li>
```

##### 改动 9.2：新增告警配置页面容器

```html
<div id="alert-config-panel" style="display:none;">
  <!-- 超时告警配置 -->
  <!-- 外协催单配置 -->
  <!-- 告警记录列表 -->
</div>
```

##### 改动 9.3：新增 JS 控制逻辑

```javascript
function showAlertConfig() {
    // 调用 GET /api/container/config/alert_rules 加载配置
    // 调用 GET /api/container/alert/list 加载告警记录
}
function saveAlertRules(rules) {
    // 调用 PUT /api/container/config/alert_rules
}
function dismissAlert(alertId) {
    // 调用 POST /api/container/alert/<id>/dismiss
}
```

##### 不改动

现有的告警列表加载/忽略功能（约 L2060-2102）**保留**。

---

## 三、不用改的文件清单（重要）

以下文件经过完整流程分析，确认**不需要修改**：

| 文件 | 原因 |
|------|------|
| `wechat_cloud.py` | 独立HTTP服务，只通过HTTP对外交互，无直引 |
| `cloud_poller.py` | 轮询功能不变，仅编码实现 |
| `cloud_backup.py` | 归档备份，独立域 |
| `wechat_message_store.py` | 消息ACK追踪，独立域 |
| `integration/desktop_callback.py` | 回调发送器，由 _callback_sender 管理，保留 |
| `wechat_server_handlers.py` | 微信指令解析、确认处理，不依赖存储层 |
| `container_center_client.py` | **删除**（被新的 container_center/client 替换） |
| 前端非告警配置的所有模板 | 通过 SDK 获取数据，返回格式一致 |
| `static/` CSS/JS | 仅通过全局 CSS 变量引用 |
| 企业微信机器人模块（`bots/`） | 不依赖存储，纯消息通道 |

---

## 四、按阶段汇总改动文件

### 第一阶段（P0：存储改造 + 核心API + SDK）

| 文件 | 改动 | 前置依赖 |
|------|------|---------|
| **新增** `container_center/storage/` (5文件) | router / document_store / index_store / config_store / alert_store | 无 |
| **新增** `container_center/api/` (5文件) | data / message / distribute / config / alert | T1.1 |
| **新增** `container_center/client/` (1文件) | ContainerCenterClient（含collect/compatible方法） | T1.2 |
| **新增** `container_center/services/` (2文件) | AlertEngine / MessageService | T1.1 |
| **改造** `container_center_v5.py` | 初始化新存储层 + 方法双写 | T1.1 |
| **改造** `container_center_api.py` | 注册新蓝图 | T1.1 |
| **改造** `wechat_server.py` | **替换 ~30 处 _container_center 直引** | T1.3 |
| **改造** `dispatch_center.py` | 替换 ~16 处 cc.storage + ~18 处 _send_wechat_via_cloud | T1.3 |
| **改造** `config.py` | 新增环境变量 | 无 |

### 第二阶段（P1：告警引擎 + 配置API）

| 文件 | 改动 | 前置依赖 |
|------|------|---------|
| **改造** `dispatch_center.py` | 替换 4 处 cc.distributor + 2 处 cc.config + 告警引用 | T2.1 + T2.2 |
| **改造** `dispatch_center.py` | 移除告警定时器调用 | T2.1 |

### 第三阶段（清理 + 部署 + 前端）

| 文件 | 改动 | 前置依赖 |
|------|------|---------|
| **改造** `dispatch_center.py` | 删除 _get_container_center() + _send_wechat_via_cloud() + 清理import | P0+P1完成 |
| **删除** `integration/timeout_reminder.py` | 功能合并到告警引擎 | T2.1 |
| **改造** `app.py` | 统一部署模式 | T3.1 |
| **改造** `templates/dispatch_center.html` | 新增告警配置页面 | T2.2 |
| **创建** `.env.example` | 环境变量模板 | 无 |

---

## 五、关键改造逻辑对照表

### 5.1 调用替换对照

```
当前调用方式                      → 新调用方式
───────────────────────────────────────────────────────────────
cc.storage.get_packages(...)     → client.get_packages(...)
cc.storage.get_package(id)      → client.get_package(id)
cc.storage.save_package(pkg)    → client.save_package(pkg)
cc.storage.update_package(id,f) → client.update_document(id, f)
cc.storage.update_package_status→ client.update_document_status

cc.distributor.distribute(t,o)  → client.distribute(t, o)
cc.config.get_all_operators()   → client.get_operators()
cc.config.get_operators_by_department → client.get_operators(department=)
cc.collect_outsource(data)      → client.create_document(...)

_container_center.collect_material → client.collect_material(...)
_container_center.collect_quality  → client.collect_quality(...)
_container_center.collect_report   → client.collect_report(...)
_container_center.complete_task    → client.complete_task(...)
_container_center.update_task_progress → client.update_task_progress(...)
_container_center.get_task_by_order   → client.get_task_by_order(...)
_container_center.get_tasks_by_order  → client.get_tasks_by_order(...)
_container_center.get_tasks_by_operator→ client.get_tasks_by_operator(...)
_container_center.get_all_tasks       → client.get_all_tasks(...)
_container_center.get_task            → client.get_task(...)

_send_wechat_via_cloud(to, c)   → client.send_message(content=c, to=to)
_get_container_center()          → _get_client()

_check_overdue_tasks()           → AlertEngine 容器中心定时执行
_check_outsource_reminders()     → AlertEngine 容器中心定时执行

本地告警列表查询/忽略            → client.get_alert_list() / client.dismiss_alert()
```

### 5.2 函数迁移对照

| 原函数（dispatch_center.py） | 新位置（container_center/） |
|-----------------------------|---------------------------|
| `_get_container_center()` | **删除**（替代为 `_get_client()`） |
| `_send_wechat_via_cloud()` | **删除**（替代为 `client.send_message()`） |
| `_check_overdue_tasks()` | `services/alert_engine.py → check_overdue_tasks()` |
| `_check_outsource_reminders()` | `services/alert_engine.py → check_outsource_reminders()` |
| `start_background_cheduler` | `services/alert_engine.py → start()` |
| `SqliteStorage`（storage_layer.py） | `storage/document_store.py → DocumentStore` |

---

## 六、实施顺序确认

```
T1.1 存储层 ──→ T1.2 HTTP API ──→ T1.3 SDK ──→ T1.4 调度中心&微信(直引替换)
                                                      │  ↑
T1.2 ──→ T2.1 告警引擎 ──→ T2.3 调度中心P1替换 ←─ T2.2 告警配置API
                                                      │
                                                      ├──→ T3.1 清理直引+删除
                                                      ├──→ T3.2 统一部署
                                                      └──→ T3.3 前端告警页面
```

> **关键依赖点**：
> - T1.4 替换 `wechat_server.py` 和 `dispatch_center.py` 的 P0 直引（~48处）
> - T2.1 + T2.2 完成后 → T2.3 替换 P1 直引
> - T1.4 + T2.3 都完成 → T3.1 清理
> - T3.1 → T3.2 ； T2.2 → T3.3（可并行）
