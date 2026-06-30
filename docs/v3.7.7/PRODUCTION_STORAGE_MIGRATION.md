# 生产环境存储迁移指南

> **创建日期**: 2026-06-25
> **完成日期**: 2026-06-25（v3.7.8 D1 ✅ 已实施）
> **状态**: ✅ D1 已完成（双轨模式），D2/D3 待 v3.7.9+
> **优先级**: 🔴 高

---

## ✅ v3.7.8 实施结果

| 项 | 计划 | 实施 |
|---|------|------|
| 存储方案 | A. MySQL (推荐) | ✅ 采用 A + 内存 fallback |
| 数据表 | dispatch_center_tasks | ✅ DDL 已建（docs/v3.7.8/ddl/） |
| 写入入口 | core.db_compat.get_conn() | ✅ 已对接 |
| 查询方法 | SELECT from dispatch_center_tasks | ✅ 3 个查询函数全部 DB 化 |
| 撤回方法 | DELETE from dispatch_center_tasks | ✅ TaskRecallPublisher.recall 已 DB 化 |
| 单元测试 | test_storage_production.py | ✅ test_publisher_v378_db.py（20 用例） |
| 业务不中断 | 故障 fallback | ✅ DB 异常 fallback 内存 + ERROR 日志 |

**关键决策**: 采用"双轨模式"（环境变量 `DISPATCH_CENTER_USE_DB=1` 切换），而非纯 DB 模式。理由：
- 单元测试无需 DB，保留内存模式
- 生产环境启用 DB，DB 异常时自动 fallback 内存（业务不中断）
- 灰度切换更安全，无需一次性迁移

详见 `docs/STORAGE_INVENTORY.md` 第 7 节决策记录 D1/D2。

## 背景

`mobile_api_ai/dispatch_center/publisher.py` 中的 `_store_task()` 使用 **内存字典** 存储任务：

```python
_task_store: Dict[str, Dict[str, Any]] = {}  # 内存版！
```

**这在生产环境有问题**：
- ❌ 多进程不共享（每个 worker 独立字典）
- ❌ 服务重启数据丢失
- ❌ 无法跨实例查询任务

## 检测

环境变量 `DISPATCH_CENTER_ENV=production` 会触发警告日志：

```python
if _IS_PRODUCTION:
    logger.warning(f'⚠️ 使用 IN-MEMORY 存储 task_id={task_id} 生产环境请实现 _store_task_production() 替换')
```

## 迁移方案

### 方案 A: MySQL（推荐）

集成到现有 `container_center` 数据库：

```sql
CREATE TABLE IF NOT EXISTS dispatch_center_tasks (
    id VARCHAR(64) PRIMARY KEY,
    type VARCHAR(32) NOT NULL,
    payload JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

```python
# _store_task_production 实现
import json
from mobile_api_ai.container_center.storage import get_mysql_connection

def _store_task_production(task_id: str, task_type: str, payload: Dict[str, Any]) -> None:
    with get_mysql_connection() as conn:
        conn.execute(
            'INSERT INTO dispatch_center_tasks (id, type, payload) '
            'VALUES (%s, %s, %s) '
            'ON DUPLICATE KEY UPDATE payload=VALUES(payload)',
            (task_id, task_type, json.dumps(payload))
        )
```

### 方案 B: Redis（高性能）

```python
import json
import redis

_redis = redis.Redis(host='localhost', port=6379, db=0)

def _store_task_production(task_id: str, task_type: str, payload: Dict[str, Any]) -> None:
    _redis.hset(
        f'dispatch_task:{task_id}',
        mapping={'type': task_type, 'payload': json.dumps(payload)}
    )
    _redis.expire(f'dispatch_task:{task_id}', 86400)  # 24h TTL
```

### 方案 C: 复用 container_center DB（v3.7.8+）

直接调用 `container_center_v5.py` 的任务表：

```python
from mobile_api_ai.container_center.core import save_task_to_db

def _store_task_production(task_id: str, task_type: str, payload: Dict[str, Any]) -> None:
    save_task_to_db(task_id=task_id, task_type=task_type, payload=payload)
```

## 任务查询改造

对应的 3 个查询方法也要改造：

| 方法 | 内存版 | 生产版 |
|------|--------|--------|
| `get_all_tasks()` | `list(_task_store.values())` | `SELECT * FROM dispatch_center_tasks` |
| `get_task_by_id()` | `_task_store.get(task_id)` | `SELECT * WHERE id=?` |
| `get_task_count()` | 内存遍历 | `SELECT COUNT(*) GROUP BY type` |

## 实施步骤

### Step 1: 选方案
- [ ] A: MySQL（已有 DB，扩展表）
- [ ] B: Redis（已有缓存，复用）
- [ ] C: container_center DB（业务耦合）

### Step 2: 实现 _store_task_production
参考方案 A/B/C 示例代码

### Step 3: 改造查询方法
- `get_all_tasks` → 真实 DB 查询
- `get_task_by_id` → 真实 DB 查询
- `get_task_count` → 真实 DB 查询

### Step 4: 添加测试
```python
# test_storage_production.py
def test_store_production():
    # 测试生产存储
    ...
```

### Step 5: 灰度发布
- [ ] 测试环境验证
- [ ] 预发布验证
- [ ] 生产灰度 1 周
- [ ] 全量发布

## 时间估计

| 工作量 | 工作 |
|:------:|------|
| 1 天 | 选方案 + 实现 _store_task_production |
| 1 天 | 改造查询方法 |
| 0.5 天 | 测试 |
| 1 周 | 灰度观察 |
| **总计** | **~2 周** |

## 不实施的后果

如果不在 v3.7.8 前实施：
1. 生产环境多 worker 部署会导致任务数据不一致
2. 服务重启会丢失已发布任务
3. 任务统计不准确（get_task_count 不可信）

## 验收标准

- [x] `_store_task_production` 已实现 ✅
- [x] 3 个查询方法已用真实 DB ✅
- [x] 单元测试覆盖生产路径 ✅ (20 用例)
- [ ] 灰度 1 周无问题 ⏳ 待生产部署后验证
- [x] 文档同步更新 ✅ (STORAGE_INVENTORY.md / ACCEPTANCE_v3.7.8.md)

---

**历史**: 本指南创建时担心 desktop_container_integration.py 删除前未完成 DB 化。**v3.7.8 已解决此问题** — publisher.py 已支持 DB 模式，desktop_container_integration.py 可在灰度期后安全删除（P2）。