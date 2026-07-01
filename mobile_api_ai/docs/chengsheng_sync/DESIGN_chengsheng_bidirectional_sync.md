# chengsheng.db 双向同步设计方案（事件驱动版）

## 1. 当前架构分析

### 1.1 现有数据库体系

```
┌─────────────────────────────────────────────────────────────────┐
│                      app.py (端口 5008)                          │
│                                                                  │
│  ┌───────────────────────┐    ┌───────────────────────────────┐  │
│  │   legacy_routes.py    │    │   dispatch_center_bp          │  │
│  │   (晨圣报工旧API层)     │    │   (调度中心API)                │  │
│  │                       │    │                               │  │
│  │  读/写: chengsheng.db │    │  只读写: wechat_container.db  │  │
│  │  读/写: wechat_container.db│                            │  │
│  └──────────┬────────────┘    └──────────┬────────────────────┘  │
│             │                             │                       │
└─────────────┼─────────────────────────────┼───────────────────────┘
              │                             │
              ▼                             ▼
   ┌──────────────────┐       ┌──────────────────────────┐
   │  chengsheng.db    │       │  wechat_container.db     │
   │  (晨圣报工主库)     │       │  (调度中心主库)            │
   │                   │       │                          │
   │  orders           │       │  process_records         │
   │  workers          │  ────►│  process_sub_steps       │
   │  sub_steps ◄──────│ 单向   │  order_cost              │
   │  attendance       │       │  dispatch_commands       │
   │  production_orders│       │  data_packages           │
   │  process_records  │       │  data_flow_logs          │
   │  order_processes  │       │  schedule_records        │
   └──────────────────┘       │  ...更多调度中心特有表     │
                              └──────────────────────────┘
```

### 1.2 当前数据流向

| 方向 | 数据 | 路径 | 状态 |
|------|------|------|------|
| → chengsheng.db | 报工子步骤(sub_steps) | `POST /api/process_sub_step` → legacy_routes → `_insert_sub_step()` | ✅ 已有 |
| → chengsheng.db | 报工子步骤(sub_steps) | `container_center_api.add_sub_step()` → `_sync_sub_step_to_chengsheng()` | ✅ 已有 |
| chengsheng.db → | orders | `GET /api/dashboard` → legacy_routes → `_query_all('SELECT * FROM orders')` | ✅ 已有 |
| chengsheng.db → | workers | `GET /api/workers` → legacy_routes → `_query_all('SELECT * FROM workers')` | ✅ 已有 |
| chengsheng.db → | sub_steps(历史) | `GET /api/sub_step_records` → legacy_routes | ✅ 已有 |
| chengsheng.db → | orders(fallback) | `GET /api/scan-info` fallback → `_scan_info_fallback()` | ✅ 已有 |
| **未同步** | process_records(调度中心→晨圣) | 调度中心新增排产→chengsheng.db无对应记录 | ❌ 缺失 |
| **未同步** | workers(双向) | 工人数据在两个库独立管理 | ❌ 缺失 |
| **未同步** | attendance(不持久化) | 考勤数据存在内存中 | ❌ 缺失 |
| **未同步** | 调度中心数据→chengsheng.db | 排产、进度、完成等数据均不同步 | ❌ 缺失 |

### 1.3 核心问题

1. **数据孤岛**: 调度中心(wechat_container.db)的排产数据无法在晨圣报工(chengsheng.db)中查看
2. **统一数据源缺失**: 晨圣报工前端虽然标榜"主库"，但调度中心操作完全绕过chengsheng.db
3. **考勤无持久化**: attendance存在内存变量，服务重启即丢失
4. **订单状态不同步**: wechat_container.db中的process_records状态变更不反映到chengsheng.db的orders

## 2. 目标架构设计

### 2.1 核心原则

1. **chengsheng.db = 晨圣报工主库**: 晨圣报工前端(cs_report.html)的所有业务数据以chengsheng.db为准
2. **事件驱动同步**: 所有同步由业务代码中的数据变更事件触发，无需轮询
3. **数据归属明确**: 每个数据域有明确的主库归属
4. **最终一致性**: 同步允许秒级延迟，但不允许永久不一致

### 2.2 目标架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                         app.py (端口 5008)                            │
│                                                                      │
│  ┌───────────────────────────┐   ┌──────────────────────────────┐   │
│  │  legacy_routes.py (改造)   │   │  dispatch_center_bp          │   │
│  │  ─ 写入操作后发布事件 ──►  │   │  ─ 写入操作后发布事件 ──►    │   │
│  └────────┬──────────────────┘   └─────────┬────────────────────┘   │
│           │                                │                        │
│           ▼                                ▼                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    EventBus (事件总线)                         │   │
│  │                                                              │   │
│  │  事件类型:                                                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │ORDER_CREATED │  │SUB_STEP_     │  │WORKER_CHANGED    │   │   │
│  │  │ORDER_UPDATED │  │CREATED       │  │ATTENDANCE_UPDATED│   │   │
│  │  │ORDER_STATUS_ │  │SUB_STEP_     │  │QUALITY_UPDATED   │   │   │
│  │  │CHANGED       │  │UPDATED       │  │                  │   │   │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘   │   │
│  └─────────┼─────────────────┼───────────────────┼──────────────┘   │
│            │                 │                   │                  │
│            ▼                 ▼                   ▼                  │
│  ┌────────────┐  ┌────────────────┐  ┌────────────────────────┐   │
│  │ SyncHandler│  │ SyncHandler    │  │ SyncHandler            │   │
│  │ 订单同步    │  │ 子步骤同步     │  │ 工人/考勤/质检同步      │   │
│  │ DC↔CS      │  │ DC↔CS         │  │ CS→DC / DC→CS         │   │
│  └─────┬──────┘  └───────┬────────┘  └───────────┬────────────┘   │
└────────┼──────────────────┼───────────────────────┼────────────────┘
         │                  │                       │
         ▼                  ▼                       ▼
   ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐
   │ chengsheng.db    │  │ wechat_container │  │ container_config │
   │ (晨圣主库)        │  │ .db (调度中心库)  │  │ .json (操作员)   │
   └─────────────────┘  └─────────────────┘  └──────────────────┘
```

## 3. 数据域主库归属

| 数据域 | 主库 | 同步方向 | 说明 |
|--------|------|---------|------|
| 订单/排产 (orders ↔ process_records) | **chengsheng.db** | 双向 | 晨圣报工以orders为准，调度中心排产写入时同步到orders |
| 报工子步骤 (sub_steps) | **wechat_container.db** | 双向 | 调度中心统一管理，同步到chengsheng.db供报工前端查询 |
| 工人/操作员 (workers) | **chengsheng.db** | 双向 | 人员管理以chengsheng.db的workers表为准 |
| 考勤 (attendance) | **chengsheng.db** | 单向(CS→DC) | 考勤统一持久化到chengsheng.db |
| 质检 (quality) | **wechat_container.db** | 单向(DC→CS) | 质检数据统一在调度中心管理，同步到chengsheng.db供查询 |

## 4. 事件驱动同步架构

### 4.1 核心组件

```
┌──────────────────────────────────────────────────────────────┐
│                    EventBus (单例)                            │
│                                                              │
│  publish(event_type, data) ────► 所有订阅者收到通知           │
│  subscribe(event_type, handler) ────► 注册监听器              │
│  unsubscribe(event_type, handler)                            │
│                                                              │
│  内部:                                                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  {                                                      │ │
│  │    'order.created':  [handler1, handler2, ...],         │ │
│  │    'order.updated':  [handler1, ...],                   │ │
│  │    'sub_step.created': [handler1, ...],                 │ │
│  │    'worker.created':  [handler1, ...],                  │ │
│  │    'attendance.updated': [handler1, ...],               │ │
│  │    'quality.updated':  [handler1, ...]                  │ │
│  │  }                                                      │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
         ▲                                    │
         │ publish(event)                     │ subscribe(handler)
         │                                    ▼
  ┌──────────────┐              ┌──────────────────────────────┐
  │  业务代码      │              │  SyncHandlers                 │
  │  (写入操作后)  │              │                              │
  │              │              │  - sync_order_to_cs()         │
  │  legacy_     │  事件发布      │  - sync_order_to_dc()        │
  │  routes.py   │────────────► │  - sync_sub_step()            │
  │              │              │  - sync_worker()              │
  │  container_  │              │  - sync_attendance()          │
  │  center_api  │              │  - sync_quality()             │
  │              │              │                              │
  │  dispatch_   │              │  每个handler:                 │
  │  center.py   │              │  1. 收到事件                   │
  │              │              │  2. 执行数据库同步              │
  └──────────────┘              │  3. 写入 sync_log             │
                                │  4. 异常重试 (最多3次)         │
                                └──────────────────────────────┘
```

### 4.2 事件类型定义

| 事件名称 | 触发时机 | 载荷(data) | 触发的同步动作 |
|---------|---------|-----------|---------------|
| `order.created` | 晨圣报工新建订单 | `{order_id, name, ...}` | DC: 同步到process_records |
| `order.updated` | 晨圣报工更新订单 | `{order_id, changes}` | DC: 更新process_records |
| `order.status_changed` | 订单状态变更 | `{order_id, from_status, to_status}` | DC: 同步状态到process_records |
| `process.created` | 调度中心新建排产 | `{process_id, order_no, ...}` | CS: 同步到orders |
| `process.updated` | 调度中心更新排产 | `{process_id, changes}` | CS: 更新orders |
| `process.status_changed` | 排产进度变更 | `{process_id, current_step, status}` | CS: 同步进度到orders |
| `sub_step.created` | 任意端口报工 | `{sub_step_data}` | 对方库同步写入 |
| `sub_step.updated` | 修改报工记录 | `{sub_step_id, changes}` | 对方库同步更新 |
| `worker.created` | 晨圣新增工人 | `{worker_data}` | DC: 同步到操作员 |
| `worker.updated` | 晨圣修改工人 | `{worker_id, changes}` | DC: 同步更新操作员 |
| `worker.deleted` | 晨圣删除工人 | `{worker_id}` | DC: 同步删除操作员 |
| `operator.created` | 调度中心新增操作员 | `{operator_data}` | CS: 同步到workers |
| `operator.updated` | 调度中心修改操作员 | `{operator_id, changes}` | CS: 同步更新workers |
| `operator.deleted` | 调度中心删除操作员 | `{operator_id}` | CS: 同步删除workers |
| `attendance.updated` | 晨圣报工打卡 | `{attendance_data}` | DC: 同步考勤记录 |
| `quality.updated` | 调度中心质检完成 | `{quality_data}` | CS: 同步质检记录 |

### 4.3 事件驱动流程（以排产创建为例）

```
调度中心创建排产
│
├─ 1. dispatch_center.py 执行 INSERT INTO process_records
├─ 2. EventBus.publish('process.created', process_data)
│
└─ 3. sync_handler_order.py 收到事件
   ├─ 3.1 调用 _map_process_to_order() 字段映射
   ├─ 3.2 写入 chengsheng.db.orders (INSERT OR IGNORE)
   ├─ 3.3 写入 sync_log (type='order', direction='dc_to_cs')
   └─ 3.4 完成（若失败，重试3次，仍失败记录错误）

总计耗时: ~50ms (网络无开销，同进程内事件)
```

### 4.4 冲突解决策略

| 冲突类型 | 解决策略 | 说明 |
|---------|---------|------|
| 订单状态冲突 | 以chengsheng.db为准 | orders是主数据源 |
| 报工数据冲突 | 以wechat_container.db为准 | 调度中心是子步骤的统一入口 |
| 工人数据冲突 | 以chengsheng.db为准 | 人员管理主库 |
| 时间戳冲突 | 保留较新的更新 | 通过updated_at字段判断 |

### 4.5 数据一致性保障

1. **同步日志表**: 在chengsheng.db中新增 `sync_log` 表，记录每次同步操作
2. **幂等性设计**: 所有同步操作支持重复执行不产生副作用（使用INSERT OR IGNORE / UPDATE WHERE version）
3. **失败重试**: 同步失败自动重试3次，仍失败写入sync_log.error_msg
4. **保底校对**: EventBus启动时可选执行一次全量校对（非轮询，仅在服务启动时）

### 4.6 衔接机制：事件同步后触发推进+推送（方案1）

事件处理器将数据写入 wechat_container.db 后，需要触发容器中心原有的自动推进和推送逻辑。采用 **方案1：HTTP 内部 API** 实现松耦合衔接。

#### 设计决策

```
事件处理器完成数据同步 (chengsheng.db → wechat_container.db)
    │
    ▼
HTTP POST → /api/internal/check-advance  (同进程本地调用，即localhost:5008)
    │
    ├── 1. 读 process_records + process_sub_steps
    ├── 2. 解析 steps JSON → 判断是否需要推进
    ├── 3. 如需推进 → UPDATE process_records (current_step/status)
    ├── 4. push_to_report_system()          → 异步推送报工程序 webhook
    └── 5. _sync_status_to_all_systems()    → 同步到调度中心+微信通知
```

#### 为什么不用直接 import 调用（方案2）

| 方案 | 耦合度 | 云端迁移影响 | 选型 |
|------|--------|-------------|------|
| 方案1: HTTP 内部 API | 松（通过 URL） | 无（URL 可配置） | ✅ 采用 |
| 方案2: 直接 import | 紧（依赖模块路径） | 大（云端可能无法 import 本地模块） | ❌ |
| 方案3: 链式事件 | 中（事件链条） | 中 | ❌ |

#### 新增内部 API 定义

```python
# container_center_api.py 中新增
@app.route('/api/internal/check-advance', methods=['POST'])
@require_api_key
def api_internal_check_advance():
    """
    内部 API：事件同步完成后触发推进判断+推送
    由 sync/handlers/sub_step_handler.py 调用，不对外暴露
    
    请求体: {"process_id": "...", "step_name": "..."}
    返回: {"code": 0, "data": {"advanced": true/false}}
    """
    data = request.get_json(force=True)
    process_id = data.get('process_id')
    step_name = data.get('step_name')
    # ... 复用 api_create_sub_step() 中 L2103-L2165 的推进判断逻辑 ...
    # 包括: 读 process_records → 解析 steps JSON → 比对 cur_step → 自动推进
    # 推进后调用 push_to_report_system() 和 _sync_status_to_all_systems()
```

#### 事件处理器调用内部 API

```python
# sync/handlers/sub_step_handler.py
import requests
import os

def sync_sub_step_handler(data: dict):
    """
    接收 sub_step.created 事件
    1. 写入 wechat_container.db（同步数据到调度中心）
    2. 调用内部 API 触发推进+推送
    """
    # 步骤1: 写入 wechat_container.db
    dc_conn = get_dc_conn()
    try:
        dc_conn.execute('''
            INSERT OR IGNORE INTO process_sub_steps
            (id, process_id, order_no, step_name, batch_no, quantity, operator, remark, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data.get('id'), data.get('process_id'), data.get('order_no'),
              data.get('step_name'), data.get('batch_no'), data.get('quantity'),
              data.get('operator'), data.get('remark'), data.get('created_at')))
        dc_conn.commit()
        
        # 写入同步日志
        write_sync_log('sub_step', 'cs_to_dc', data.get('id'))
    except Exception as e:
        write_sync_log('sub_step', 'cs_to_dc', data.get('id'), 'failed', str(e))
        raise
    finally:
        dc_conn.close()

    # 步骤2: 调用内部 API 触发推进判断+推送
    internal_url = os.environ.get('INTERNAL_API_URL', 'http://localhost:5008')
    try:
        resp = requests.post(
            f'{internal_url}/api/internal/check-advance',
            json={
                'process_id': data.get('process_id'),
                'step_name': data.get('step_name')
            },
            timeout=5
        )
        if resp.status_code == 200:
            logger.info(f'推进检查完成: process_id={data.get("process_id")}')
    except Exception as e:
        logger.warning(f'推进检查请求失败(非致命): {e}')
```

#### 完整数据流（改造后）

```
晨圣报工扫码提交报工
    │
    ▼ ❶ 写入主库
chengsheng.db.sub_steps ← INSERT
    │
    ▼ ❷ 发布事件
EventBus.publish('sub_step.created', record)
    │
    ▼ ❸ 事件处理器同步到调度中心
sync_sub_step_handler()
    │
    ├── INSERT INTO wechat_container.db.process_sub_steps  ← 数据同步
    │
    └── ❹ HTTP POST /api/internal/check-advance
            │
            ▼ ❺ 推进判断（同进程，同步执行）
            ├── 读 process_records → 解析 steps JSON
            ├── 判断 current_step 是否需推进
            ├── UPDATE process_records (current_step/status)
            ├── push_to_report_system()  → webhook
            └── _sync_status_to_all_systems() → 微信推送
```

## 5. 详细实现方案

### 5.1 核心文件清单

```
mobile_api_ai/
├── sync/
│   ├── __init__.py              # 导出EventBus和所有handler
│   ├── event_bus.py             # EventBus 单例（发布/订阅）
│   ├── sync_log.py              # sync_log 表的读写封装
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── order_handler.py     # 订单/排产同步处理器
│   │   ├── sub_step_handler.py  # 报工子步骤同步处理器
│   │   ├── worker_handler.py    # 工人/操作员同步处理器
│   │   ├── attendance_handler.py # 考勤同步处理器
│   │   └── quality_handler.py   # 质检同步处理器
│   ├── mappers/
│   │   ├── __init__.py
│   │   └── field_mapper.py      # 字段映射工具（状态值转换等）
│   └── utils.py                 # 数据库连接等工具
```

### 5.2 chengsheng.db 新增表和字段

```sql
-- 同步日志表
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL,        -- 'order', 'sub_step', 'worker', 'attendance', 'quality'
    direction TEXT NOT NULL,        -- 'cs_to_dc', 'dc_to_cs'
    source_id TEXT NOT NULL,        -- 源记录ID
    target_id TEXT DEFAULT '',
    status TEXT DEFAULT 'success',  -- 'success', 'failed'
    error_msg TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    synced_at TEXT
);

-- orders表增加同步字段
ALTER TABLE orders ADD COLUMN dc_process_id TEXT DEFAULT '';
ALTER TABLE orders ADD COLUMN updated_at TEXT DEFAULT '';
ALTER TABLE orders ADD COLUMN version INTEGER DEFAULT 1;

-- workers表增加同步字段
ALTER TABLE workers ADD COLUMN dc_operator_id TEXT DEFAULT '';
ALTER TABLE workers ADD COLUMN updated_at TEXT DEFAULT '';
ALTER TABLE workers ADD COLUMN version INTEGER DEFAULT 1;

-- attendance表增加同步标记
ALTER TABLE attendance ADD COLUMN synced INTEGER DEFAULT 0;
ALTER TABLE attendance ADD COLUMN dc_sync_key TEXT DEFAULT '';

-- 新增质检记录表
CREATE TABLE IF NOT EXISTS quality_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id TEXT NOT NULL,
    order_no TEXT NOT NULL,
    result TEXT DEFAULT 'pass',
    inspection_type TEXT DEFAULT '巡检',
    defect_description TEXT DEFAULT '',
    inspector TEXT DEFAULT '',
    inspection_items TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    synced_at TEXT
);
```

### 5.3 wechat_container.db 新增字段

```sql
ALTER TABLE process_records ADD COLUMN cs_order_id INTEGER DEFAULT 0;
ALTER TABLE process_records ADD COLUMN synced INTEGER DEFAULT 0;
ALTER TABLE process_sub_steps ADD COLUMN synced INTEGER DEFAULT 0;
```

### 5.4 EventBus 核心实现

```python
# sync/event_bus.py
"""
EventBus 单例 - 事件驱动同步的核心
所有数据变更通过这里发布，对应的Handler自动响应
"""

import logging
from collections import defaultdict
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)


class EventBus:
    """事件总线，单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = defaultdict(list)
        return cls._instance

    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        self._subscribers[event_type].append(handler)
        logger.debug(f'[EventBus] 订阅事件: {event_type} -> {handler.__name__}')

    def publish(self, event_type: str, data: dict):
        """发布事件，同步调用所有订阅者"""
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            logger.debug(f'[EventBus] 无订阅者: {event_type}')
            return
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f'[EventBus] handler失败: {handler.__name__}, event={event_type}, err={e}')

    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""
        self._subscribers[event_type] = [
            h for h in self._subscribers[event_type] if h != handler
        ]
```

### 5.5 同步处理器示例

```python
# sync/handlers/order_handler.py
"""
订单/排产同步处理器
处理 order.created / process.created 等事件
"""

def sync_process_to_cs_handler(data: dict):
    """
    调度中心排产 → 同步到 chengsheng.db.orders
    订阅: process.created, process.updated
    """
    conn = get_cs_conn()
    try:
        mapped = map_process_to_order(data)
        conn.execute(
            'INSERT OR IGNORE INTO orders '
            '(order_id, name, material, spec, status, priority, ...) '
            'VALUES (?, ?, ?, ?, ?, ?, ...)',
            (mapped['order_id'], mapped['name'], ...)
        )
        conn.commit()
        write_sync_log('order', 'dc_to_cs', data.get('id'))
        logger.info(f'排产同步到orders成功: {data.get("id")}')
    except Exception as e:
        write_sync_log('order', 'dc_to_cs', data.get('id'), 'failed', str(e))
        logger.error(f'排产同步失败: {e}')
        raise  # EventBus catch, 触发重试
    finally:
        conn.close()


def sync_order_to_dc_handler(data: dict):
    """
    晨圣订单变更 → 同步到 process_records
    订阅: order.created, order.updated, order.status_changed
    """
    dc_conn = get_dc_conn()
    try:
        # 更新 process_records 的对应记录
        mapped = map_order_to_process(data)
        dc_conn.execute(
            'UPDATE process_records SET status=?, current_step=?, updated_at=? '
            'WHERE order_no=?',
            (mapped['status'], mapped['current_step'], mapped['updated_at'],
             mapped.get('order_no'))
        )
        dc_conn.commit()
        write_sync_log('order', 'cs_to_dc', data.get('order_id'))
    except Exception as e:
        write_sync_log('order', 'cs_to_dc', data.get('order_id'), 'failed', str(e))
        raise
    finally:
        dc_conn.close()
```

### 5.6 业务代码中的事件发布（最小侵入）

在现有业务的写入操作后，**只加一行**：

```python
# legacy_routes.py - 现有函数末尾加一行
def api_create_sub_step():
    # ... 原有写入逻辑不变 ...
    record = {...}
    cur.execute('INSERT INTO process_sub_steps ...')
    conn.commit()

    # 只加这一行:
    EventBus().publish('sub_step.created', record)
```

```python
# container_center_api.py - 现有函数末尾加一行
def add_sub_step(data):
    # ... 原有写入逻辑不变 ...
    cur.execute('INSERT INTO process_sub_steps ...')
    conn.commit()

    # 替换原有 _sync_sub_step_to_chengsheng() 调用:
    EventBus().publish('sub_step.created', data)  # ← 统一走事件
```

```python
# dispatch_center.py - 新建排产函数末尾
def create_process(data):
    # ... 原有创建排产逻辑 ...
    cur.execute('INSERT INTO process_records ...')
    conn.commit()

    # 加一行:
    EventBus().publish('process.created', data)   # ← 触发同步到orders
```

### 5.7 初始化注册

```python
# sync/__init__.py 或 app.py 启动时
def init_sync_engine():
    """初始化同步引擎，注册所有事件订阅"""
    bus = EventBus()

    # 注册订单/排产同步
    from sync.handlers.order_handler import (
        sync_process_to_cs_handler,
        sync_order_to_dc_handler
    )
    bus.subscribe('process.created', sync_process_to_cs_handler)
    bus.subscribe('process.updated', sync_process_to_cs_handler)
    bus.subscribe('order.created', sync_order_to_dc_handler)
    bus.subscribe('order.status_changed', sync_order_to_dc_handler)

    # 注册子步骤同步
    from sync.handlers.sub_step_handler import sync_sub_step_handler
    bus.subscribe('sub_step.created', sync_sub_step_handler)

    # 注册工人同步
    from sync.handlers.worker_handler import sync_worker_handler
    bus.subscribe('worker.created', sync_worker_handler)
    bus.subscribe('worker.updated', sync_worker_handler)

    # 注册考勤同步
    from sync.handlers.attendance_handler import sync_attendance_handler
    bus.subscribe('attendance.updated', sync_attendance_handler)

    # 注册质检同步
    from sync.handlers.quality_handler import sync_quality_handler
    bus.subscribe('quality.updated', sync_quality_handler)

    logger.info('同步引擎初始化完成，已注册 12 个事件订阅')
```

## 6. 改造点清单

### 改造A: legacy_routes.py

| 改造点 | 操作 | 事件 | 优先级 |
|--------|------|------|--------|
| `_insert_sub_step()` | 末尾加 `EventBus().publish('sub_step.created', ...)` | sub_step.created | P0 |
| `api_create_sub_step()` | 末尾加事件发布 | sub_step.created | P0 |
| `api_post_attendance()` | 改为持久化到chengsheng.db + 发布事件 | attendance.updated | P0 |
| `api_get_attendance()` | 改为读chengsheng.db | 无事件 | P0 |
| `api_submit_quality()` | 末尾加事件发布 | quality.updated | P1 |

### 改造B: container_center_api.py

| 改造点 | 操作 | 事件/API | 优先级 |
|--------|------|---------|--------|
| 新增 `POST /api/internal/check-advance` | 内部API，复用推进判断逻辑(L2103-L2165)，调用push_to_report_system + _sync_status_to_all_systems | 供sync_handler调用 | P0 |
| `add_sub_step()` | 替换`_sync_sub_step_to_chengsheng()`为事件发布 | sub_step.created | P0 |
| `add_sub_step()` 内创建排产逻辑 | 末尾加事件发布 | process.created | P1 |

### 改造C: dispatch_center.py

| 改造点 | 操作 | 事件 | 优先级 |
|--------|------|------|--------|
| 创建排产 (createProcess/assignProcess) | 末尾加事件发布 | process.created | P1 |
| 更新排产状态 (advanceProcess/rejectProcess) | 末尾加事件发布 | process.status_changed | P1 |
| 操作员管理 (saveOperator) | 末尾加事件发布 | operator.created/updated | P1 |

### 改造D: 新建 sync/ 模块

| 文件 | 内容 | 优先级 |
|------|------|--------|
| `sync/event_bus.py` | EventBus 单例 | P0 |
| `sync/sync_log.py` | sync_log 表封装 | P0 |
| `sync/handlers/order_handler.py` | 订单/排产同步 | P1 |
| `sync/handlers/sub_step_handler.py` | 子步骤同步 | P0 |
| `sync/handlers/worker_handler.py` | 工人同步 | P1 |
| `sync/handlers/attendance_handler.py` | 考勤同步 | P0 |
| `sync/handlers/quality_handler.py` | 质检同步 | P1 |
| `sync/mappers/field_mapper.py` | 字段映射工具 | P1 |
| `sync/__init__.py` | 初始化注册所有订阅 | P0 |

## 7. 实施路线图

### 阶段1: 事件基础设施 (P0)

**预计工作量: 0.5天**

1. 创建 `sync/` 模块目录结构
2. 实现 `EventBus` 单例
3. 实现 `sync_log` 表操作
4. 在 `app.py` 启动时初始化同步引擎
5. 验证: EventBus 发布/订阅功能正常

### 阶段2: 报工子步骤事件同步 + 内部 API 衔接 (P0)

**预计工作量: 1天**

1. 实现 `sub_step_handler.py`（写 wechat_container.db + 调用内部 API）
2. 在 `container_center_api.py` 新增 `POST /api/internal/check-advance` 内部 API
   - 从 wechat_container.db 读取 process_sub_steps/process_records
   - 执行推进判断逻辑（当前 `api_create_sub_step()` L2103-L2165 的复用）
   - 触发 `push_to_report_system()` + `_sync_status_to_all_systems()`
3. 在 `legacy_routes.py` 的 `_insert_sub_step()` 末尾加事件发布
4. 在 `container_center_api.py` 的 `api_create_sub_step()` 末尾替换原同步函数为事件发布
5. 验证: 报工后子步骤同步 + 自动推进 + 微信推送全链路正常

### 阶段3: 考勤持久化 (P0)

**预计工作量: 0.5天**

1. 实现 `attendance_handler.py`
2. `legacy_routes.py` 考勤API改为读写chengsheng.db
3. 验证: 服务重启后考勤不丢失

### 阶段4: 订单/排产事件同步 (P1)

**预计工作量: 1天**

1. 实现 `field_mapper.py`（字段映射 + 状态值转换）
2. 实现 `order_handler.py`
3. 在 `dispatch_center.py` 排产创建/状态变更处加事件发布
4. 验证: 调度中心排产后chengsheng.db有对应订单

### 阶段5: 工人/质检事件同步 (P1)

**预计工作量: 0.5天**

1. 实现 `worker_handler.py`
2. 实现 `quality_handler.py`
3. 在 `dispatch_center.py` 操作员管理加事件发布
4. 在 `legacy_routes.py` 质检提交加事件发布
5. 验证: 两个系统人员/质检数据一致

## 8. 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 事件发布遗漏 | 同步缺失 | 中 | sync_log记录 + 保底校对 |
| 事件处理异常 | 单次同步失败 | 中 | 自动重试3次 + 日志记录 |
| 循环事件 | 无限递归同步 | 低 | handler中加防循环标记 |
| 性能影响 | 写操作变慢 | 低 | EventBus同步调用，单次~10ms |

## 9. 验收标准

- [ ] EventBus 发布/订阅功能正常，12个事件订阅全部注册
- [ ] 报工子步骤: 两个数据库完全一致，无遗漏
- [ ] 考勤数据: 服务重启后不丢失
- [ ] 订单数据: 调度中心排产后晨圣报工可查看，状态同步
- [ ] 工人数据: 两个系统人员一致
- [ ] 质检数据: 调度中心质检完成同步到chengsheng.db
- [ ] 向前兼容: 现有API接口不变，前端无需修改
