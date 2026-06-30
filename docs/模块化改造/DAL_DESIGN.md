# DAL_DESIGN.md（DAL 详细设计）

> 文档版本：v1.0（2026-06-13）
> 关联文档：ARCHITECT_全面模块化改造.md, TASK_全面模块化改造.md

---

## 一、DAL 架构总览

DAL（Data Access Layer）是模块化改造的核心数据访问层，封装所有数据库操作。

### 1.1 分层结构

```
┌──────────────────────────────────────────────────────┐
│ 业务模块（Business Modules）                          │
│   - OrderModule / ProcessModule / QualityModule ...  │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│ 模块基类（BaseModule）                                │
│   - 统一异常处理 / 错误码 / 日志                      │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│ 数据访问层（DAL）                                    │
│   - BaseStorage（基类）                              │
│   - ContainerStorage（container_center 库）          │
│   - SteelbeltStorage（steel_belt 库）                │
│   - InventoryStorage（inventory_db 库）              │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│ 数据库连接池                                          │
│   - pymysql + DBUtils.PooledDB                       │
│   - 三个独立库：container_center / steel_belt / ...  │
└──────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则

| 原则 | 说明 |
|------|------|
| **零跨库直查** | DAL 内不直接 JOIN 跨库表 |
| **本地表优先** | 读操作优先使用本地表（container_center） |
| **8008 同步** | 写操作通过 8008 桥接写入 steel_belt |
| **降级队列** | 同步失败时入 outbox 队列 |
| **可灰度** | 通过 Feature Flag 切换 |

---

## 二、BaseStorage 基类

### 2.1 接口定义

```python
# mobile_api_ai/dal/base_storage.py
from typing import List, Dict, Any, Optional

class BaseStorage:
    """所有存储层的基类"""

    def __init__(self, pool_name: str):
        self._pool = None  # 延迟初始化

    def _get_connection(self):
        """获取数据库连接（子类实现）"""
        raise NotImplementedError

    def _execute(self, sql: str, params: tuple) -> int:
        """执行 SQL（INSERT/UPDATE/DELETE）"""
        with self._get_connection() as conn:
            with conn.cursor() as c:
                return c.execute(sql, params)

    def insert(self, table: str, data: dict) -> int:
        """插入数据"""
        cols = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        return self._execute(sql, tuple(data.values()))

    def update(self, table: str, data: dict, where: str, params: tuple) -> int:
        """更新数据"""
        set_clause = ', '.join([f"{k}=%s" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        return self._execute(sql, tuple(data.values()) + params)

    def delete(self, table: str, where: str, params: tuple) -> int:
        """删除数据"""
        sql = f"DELETE FROM {table} WHERE {where}"
        return self._execute(sql, params)

    def fetch_one(self, sql: str, params: tuple) -> Optional[Dict]:
        """查询单条"""
        with self._get_connection() as conn:
            with conn.cursor() as c:
                c.execute(sql, params)
                return c.fetchone()

    def fetch_all(self, sql: str, params: tuple) -> List[Dict]:
        """查询多条"""
        with self._get_connection() as conn:
            with conn.cursor() as c:
                c.execute(sql, params)
                return c.fetchall()
```

### 2.2 慢查询日志（基类内置）

```python
import time
import logging

logger = logging.getLogger(__name__)

class BaseStorage:
    SLOW_QUERY_THRESHOLD_MS = 200
    VERY_SLOW_QUERY_THRESHOLD_MS = 1000

    def _log_slow_query(self, sql, params, elapsed_sec, row_count=None):
        elapsed_ms = elapsed_sec * 1000
        if elapsed_ms < self.SLOW_QUERY_THRESHOLD_MS:
            return
        if elapsed_ms >= self.VERY_SLOW_QUERY_THRESHOLD_MS:
            logger.error(f'[VERY SLOW SQL] {elapsed_ms:.2f}ms rows={row_count} | {sql[:200]}')
        else:
            logger.warning(f'[SLOW SQL] {elapsed_ms:.2f}ms rows={row_count} | {sql[:200]}')
```

---

## 二点五、字段白名单 - 实际 SQL 例子

### 2.5.1 报工数据写入（白名单应用）

```python
# mobile_api_ai/dal/modules/process_module.py

# [字段白名单 v2.0] 22 字段白名单（与 sync_bridge.py:469-494 一致）
SUB_STEP_FIELD_WHITELIST = {
    'uuid', 'process_id', 'process_record_id', 'order_no', 'step_name',
    'batch_no', 'quantity', 'qualified_qty', 'operator', 'operator_id',
    'wechat_userid', 'equipment_name', 'remark', 'record_date', 'source',
    'overtime_hours', 'synced', 'synced_at', 'created_at', 'updated_at',
    'created_by', 'updated_by',
}

def validate_sub_step_data(data: dict) -> Tuple[bool, List[str]]:
    """校验报工数据，返回 (is_valid, invalid_fields)"""
    invalid = [k for k in data.keys() if k not in SUB_STEP_FIELD_WHITELIST]
    return len(invalid) == 0, invalid


class ProcessModule(BaseModule):
    def report_sub_step(self, data: dict):
        """报工提交（v2.0: 走 8008 桥接 + 字段白名单）"""
        # 1. 字段白名单校验
        is_valid, invalid = validate_sub_step_data(data)
        if not is_valid:
            return {
                'code': 1603,
                'message': f'同步参数错误: 含禁止字段 {invalid}',
            }
        
        # 2. 必填字段校验
        required = ['order_no', 'step_name', 'quantity']
        for field in required:
            if not data.get(field):
                return {'code': 1001, 'message': f'必填字段缺失: {field}'}
        
        try:
            # 3. 写入本地表（container_center）
            local_id = self.storage.insert('process_sub_steps_local', data)
            
            # 4. 走 8008 同步到 steel_belt
            import requests
            resp = requests.post(
                'http://127.0.0.1:8008/api/sync/sub-step-report',
                json=data,
                timeout=5,
            )
            if resp.status_code == 200 and resp.json().get('code') == 0:
                return {'code': 0, 'message': 'success', 'data': {'id': local_id}}
            
            # 5. 8008 失败则入 outbox 降级队列
            return self._enqueue_outbox('sub-step-report', data)
        
        except Exception as e:
            return self._handle_exception(e, code=1501)
    
    def _enqueue_outbox(self, action: str, data: dict):
        """降级队列"""
        import json
        import uuid
        with open('/tmp/sync_outbox/queue.jsonl', 'a') as f:
            f.write(json.dumps({
                'id': str(uuid.uuid4()),
                'action': action,
                'payload': data,
            }) + '\n')
        return {'code': 1604, 'message': '同步已入队列'}
```

### 2.5.2 状态变更同步

```python
class ProcessModule(BaseModule):
    def update_status(self, order_no: str, new_status: str, operator: str):
        """更新订单状态（v2.0: 走 8008 桥接）"""
        # 白名单字段
        data = {
            'order_no': order_no,
            'new_status': new_status,
            'operator': operator,
            'updated_at': datetime.now().isoformat(),
        }
        
        try:
            # 1. 更新本地表
            self.storage.update(
                'process_records_local',
                {'status': new_status, 'updated_at': data['updated_at']},
                where='order_no=%s',
                params=(order_no,),
            )
            
            # 2. 走 8008 同步
            import requests
            resp = requests.post(
                'http://127.0.0.1:8008/api/sync/status-change',
                json=data,
                timeout=5,
            )
            if resp.status_code == 200 and resp.json().get('code') == 0:
                return {'code': 0, 'message': 'success'}
            
            return self._enqueue_outbox('status-change', data)
        
        except Exception as e:
            return self._handle_exception(e, code=1503)
```

### 2.5.3 客户群查询（替代跨库直查）

```python
class OrderModule(BaseModule):
    def get_customer_group(self, order_no: str):
        """查询客户群（v2.0: 走本地表，替代跨库直查）"""
        # ❌ 之前：跨库直查
        # conn, c = get_steelbelt_cursor()
        # c.execute("SELECT customer_group FROM orders WHERE order_no=%s", (order_no,))
        # result = c.fetchone()
        
        # ✅ 之后：读本地表
        result = self.storage.fetch_one(
            "SELECT customer_group FROM orders_local WHERE order_no=%s",
            (order_no,),
        )
        return result.get('customer_group', '') if result else ''
```

### 2.5.4 违规日志查询（替代跨库直查）

```python
class ViolationModule(BaseModule):
    def list_violations(self, page: int = 1, page_size: int = 20, scenario: str = '', severity: str = ''):
        """查询违规日志（v2.0: 走本地表）"""
        # ❌ 之前：跨库直查 _core.py:1790-1796
        # conn = _get_violation_conn()
        # cur = conn.cursor()
        # cur.execute("SELECT * FROM violation_log WHERE 1=1 ...")
        
        # ✅ 之后：读本地表
        where = 'WHERE 1=1'
        params = []
        if scenario:
            where += ' AND scenario=%s'
            params.append(scenario)
        if severity:
            where += ' AND severity=%s'
            params.append(severity)
        
        offset = (page - 1) * page_size
        sql = f"SELECT * FROM violations_local {where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, offset])
        
        rows = self.storage.fetch_all(sql, tuple(params))
        total = self.storage.fetch_one(
            f"SELECT COUNT(*) AS cnt FROM violations_local {where}",
            tuple(params[:-2] if page_size else params),
        )
        
        return {
            'code': 0,
            'data': rows,
            'total': total.get('cnt', 0) if total else 0,
        }
```

### 2.5.5 字段白名单 SQL 校验

```sql
-- 验证：写入的字段是否在白名单
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'steel_belt'
  AND table_name = 'process_sub_steps';

-- 结果应该是 22 字段（v2.0 白名单）
-- 如果有 28 字段（含 content/metadata 等），说明白名单违规
```

```python
def check_whitelist_violation():
    """运行 SQL 检查字段白名单违规"""
    sql = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'steel_belt'
      AND table_name = 'process_sub_steps'
    """
    rows = self.storage.fetch_all(sql, ())
    actual_fields = {r['column_name'] for r in rows}
    whitelist = SUB_STEP_FIELD_WHITELIST
    
    # 实际有但白名单没有的（禁止字段被启用）
    forbidden = actual_fields - whitelist
    # 白名单有但实际没有的（漏字段）
    missing = whitelist - actual_fields
    
    if forbidden:
        logger.error(f'[WHITELIST] 禁止字段已存在: {forbidden}')
    if missing:
        logger.warning(f'[WHITELIST] 白名单字段缺失: {missing}')
    
    return {'forbidden': forbidden, 'missing': missing}
```

---

## 三、ConcreteStorage 实现

### 3.1 ContainerStorage

- **库名**：`container_center`
- **核心表**：`process_records`, `process_sub_steps`, `data_packages`, `orders_local`
- **特殊能力**：
  - 业务主表，所有读操作走这里
  - 字段白名单严格：只接收业务核心字段

### 3.2 SteelbeltStorage

- **库名**：`steel_belt`
- **核心表**：`process_records`, `process_sub_steps`
- **写入限制**：
  - 仅通过 8008 桥接写入
  - 不允许直接 INSERT/UPDATE
  - 字段白名单：22 字段（详见 SUPPLEMENT §1.3）

### 3.3 InventoryStorage

- **库名**：`inventory_db`
- **核心表**：`inventory_items`, `inventory_movements`
- **独立性**：完全独立，不与其他库交互

---

## 四、模块基类 BaseModule

```python
# mobile_api_ai/dal/base_module.py

class BaseModule:
    """业务模块基类"""

    def __init__(self, storage: BaseStorage):
        self.storage = storage

    def _handle_exception(self, e: Exception, code: int = 5000):
        """统一异常处理：返回错误码 + 记录日志"""
        logger.exception(f'[{self.__class__.__name__}] 异常: {e}')
        return {'code': code, 'message': str(e)}

    def _validate(self, data: dict, required_fields: list) -> bool:
        """参数验证"""
        return all(data.get(f) for f in required_fields)
```

### 4.1 订单模块示例

```python
# mobile_api_ai/dal/modules/order_module.py

class OrderModule(BaseModule):
    def get_order(self, order_no: str):
        try:
            return self.storage.fetch_one(
                "SELECT * FROM orders_local WHERE order_no=%s", (order_no,))
        except Exception as e:
            return self._handle_exception(e, code=1301)

    def create_order(self, data: dict):
        if not self._validate(data, ['order_no', 'product_name']):
            return {'code': 1001, 'message': '订单号和产品名必填'}
        try:
            return self.storage.insert('orders_local', data)
        except Exception as e:
            return self._handle_exception(e, code=1501)
```

---

## 五、字段白名单管理

### 5.1 字段白名单（修订后）

**steel_belt.process_sub_steps 实际写入 22 字段**：

| 类别 | 字段数 | 字段 |
|------|--------|------|
| 核心字段 | 5 | order_no, status, plan_start, plan_end, updated_at |
| 业务字段 | 17 | uuid, process_id, process_record_id, step_name, batch_no, quantity, qualified_qty, operator, operator_id, wechat_userid, equipment_name, remark, record_date, source, overtime_hours, synced, synced_at, created_at, created_by, updated_by |

**注意**：与 SUPPLEMENT §1.3 一致，扩白名单为 22 字段。

### 5.2 白名单校验

```python
FIELD_WHITELIST = {
    'process_sub_steps': [
        'order_no', 'status', 'plan_start', 'plan_end', 'updated_at',
        # ... 17 业务字段
    ]
}

def validate_fields(table: str, data: dict) -> bool:
    allowed = FIELD_WHITELIST.get(table, [])
    return all(k in allowed for k in data.keys())
```

---

## 六、灰度切换策略

### 6.1 Feature Flag

```python
# mobile_api_ai/config/feature_flags.py

FEATURE_FLAGS = {
    'DAL_ENABLED': {
        'enabled': False,           # 总开关
        'percentage': 0,            # 灰度比例 0-100
        'whitelist': [],            # 白名单 order_no
        'blacklist': [],            # 黑名单 order_no
    },
    'ORDER_MODULE_DAL': False,
    'PROCESS_MODULE_DAL': False,
    'QUALITY_MODULE_DAL': False,
    'MATERIAL_MODULE_DAL': False,
    'SYNC_BRIDGE_VIA_8008': False,
    'READ_FROM_LOCAL_TABLES': True,
}
```

### 6.2 灰度阶段

| 阶段 | 比例 | 持续时间 | 验证内容 |
|------|------|----------|----------|
| 1. 白名单 | 5 订单 | 3 天 | 功能正确性 |
| 2. 10% | 10% | 1 周 | 性能指标 |
| 3. 50% | 50% | 1 周 | 监控告警 |
| 4. 100% | 100% | 持续 | 全量验证 |

---

## 七、错误码

详见 `ERROR_CODES.md`（已规划：避免 5000-5099 段位）

---

## 八、监控点

| 指标 | 阈值 | 告警 |
|------|------|------|
| API 响应时间 | > 100ms | WARNING |
| API 响应时间 | > 1s | ERROR |
| SQL 执行时间 | > 200ms | WARNING |
| SQL 执行时间 | > 1s | ERROR |
| 同步失败率 | > 1% | WARNING |
| 同步失败率 | > 5% | ERROR |
| 跨库直查 | > 0 次 | WARNING |

详见 `/api/perf/stats` 端点。

---

## 九、参考

- [ARCHITECT_全面模块化改造.md](./ARCHITECT_全面模块化改造.md)
- [TASK_全面模块化改造.md](./TASK_全面模块化改造.md)
- [SUPPLEMENT_全面模块化改造.md](./SUPPLEMENT_全面模块化改造.md)
- [BRIDGE_PROTOCOL.md](./BRIDGE_PROTOCOL.md)
- [ERROR_CODES.md](./ERROR_CODES.md)
