# 存储架构盘点

> **日期**: 2026-06-25（v3.7.8 D1 ✅ + v3.8.0 D3 ✅）
> **负责人**: 小贺（DBA）+ 小圣（架构）+ 小曦（PM）+ 小钰（QA）
> **范围**: 所有 INSERT / UPDATE / DELETE 数据写入
> **触发**: 4 人会议决议
> **状态**: D1 ✅ v3.7.8（双轨: 内存 + MySQL）+ D3 ✅ v3.8.0（SQLite 完全移除），D2 仍待 v3.7.9 集成测试

---

## 1. 核心发现

🚨 **项目存在 4 套不同的存储介质，混用严重**：

| 存储 | 库类型 | 出现位置 | 状态 |
|------|--------|---------|------|
| **SQLite（容器中心本地）** | SQLite | `container_center_v5.py` | ⚠️ 旧 |
| **MySQL（container_center）** | MySQL | `core/_config_domain.py` 配置 | ✅ 在用 |
| **内存 Dict** | 内存 | `dispatch_center/publisher.py` | ❌ 新增，会丢 |
| **HTTP 转发** | - | `desktop_container_integration.py` | ⚠️ 旧逻辑 |
| **Redis** | 内存 K/V | `queue_manager_integration.py` | ✅ 在用 |

---

## 2. 数据表清单（按出现频次）

### P0 - 关键业务表

| 表名 | 写入位置 | 数据库 | 频次 | 修复建议 | 优先级 |
|------|---------|--------|:----:|----------|:------:|
| `process_records` | `mobile_api_ai/app.py:380, 412`<br>`desktop_web/server.py:2324, 2628`<br>`_step1_ddl.py:31, 41` | MySQL | 高 | 保留 | P0 |
| `data_packages` | `mobile_api_ai/app.py:380`<br>`fix_tables.py:35, 64`<br>`_verify_all.py:93` | MySQL | 高 | 保留 | P0 |
| `order_materials` | `desktop_web/server.py:1242, 1301, 1426`<br>`material_prep_view.py:734, 797, 840` | MySQL | 高 | 保留 | P0 |
| `orders` | `desktop_web/server.py:735, 3176, 3180`<br>`order_query_view.py:430` | MySQL | 高 | 保留 | P0 |

### P1 - 业务辅助表

| 表名 | 写入位置 | 数据库 | 修复建议 | 优先级 |
|------|---------|--------|----------|:------:|
| `quality_records` | `desktop_web/server.py:3215` | MySQL | 保留 | P1 |
| `shipments` | `desktop_web/server.py:3543` | MySQL | 保留 | P1 |
| `logistics_companies` | `desktop_web/server.py:3730` | MySQL | 保留 | P1 |
| `process_sub_steps` | `mobile_api_ai/app.py:412`<br>`_verify_all.py:92` | MySQL | 保留 | P1 |
| `sync_log` | `test_migration_v2.py:366` | MySQL | 保留（仅测试） | P2 |
| `saga_dead_letter` | `core/saga.py:61` | MySQL | 保留 | P1 |

### ⚠️ 异常存储

| 位置 | 存储 | 状态 | 说明 |
|------|------|:----:|------|
| `dispatch_center/publisher.py` | **内存 Dict + MySQL** | ✅ 已支持 | v3.7.8 双轨（环境变量切换），DB 失败 fallback 内存 |
| `container_center_v5.py` | SQLite | ⚠️ P1 | 与 MySQL 重复，需要收敛 |
| `desktop_container_integration.py:314, 340, 491` | dict.update | ⚠️ P2 | 业务对象修改，不是 DB 写入 |
| `queue_manager_integration.py:356` | Redis | ✅ | 队列管理，独立系统 |

---

## 3. 数据库连接矩阵

| 入口 | MySQL 配置 | SQLite 文件 | HTTP 服务 |
|------|:----------:|:-----------:|:---------:|
| `mobile_api_ai/app.py` | ✅ CONTAINER_MYSQL_CFG | - | - |
| `desktop_web/server.py` | ✅ CONTAINER_MYSQL_CFG | - | - |
| `core/_config_domain.py` | ✅ | - | - |
| `dispatch_center/_core.py` | ✅ cc.storage | - | - |
| `container_center_v5.py` | - | ✅ `cc_sqlite.db` | - |
| `desktop_container_integration.py` | - | ✅ 降级 | ✅ 5003 端口 |
| `dispatch_center/publisher.py` | ✅ core.db_compat | ❌ 没用 | ❌ 没用 |

---

## 4. 核心问题（按严重度）

### ✅ P0: publisher.py 已支持双轨存储（v3.7.8 完成）

**位置**: `mobile_api_ai/dispatch_center/publisher.py:85-148, 327-369`

**问题**（修复前）:
```python
_task_store: Dict = {}  # 内存，重启就丢
```

**实施后（v3.7.8 双轨模式）**:
```python
import os as _os
_USE_DB = _os.environ.get('DISPATCH_CENTER_USE_DB') == '1'

def _store_task(task_id, task_type, payload):
    """双轨: DB 优先 + 内存 fallback"""
    if _USE_DB:
        try:
            _store_task_production(task_id, task_type, payload)
            return
        except Exception as e:
            logger.error(f'[publisher] DB 存储失败 task_id={task_id}: {e} | fallback 内存存储')
    with _task_lock:
        _task_store[task_id] = {...}

def _store_task_production(task_id, task_type, payload):
    """DB 模式: 写入 dispatch_center_tasks 表"""
    import json
    from core.db_compat import get_conn
    payload_json = json.dumps(payload, ensure_ascii=False, default=str)
    sql = (
        'INSERT INTO dispatch_center_tasks (id, type, payload) '
        'VALUES (%s, %s, %s) '
        'ON DUPLICATE KEY UPDATE '
        'type=VALUES(type), payload=VALUES(payload)'
    )
    with get_conn() as (conn, cur):
        cur.execute(sql, (task_id, task_type, payload_json))
```

**关键设计**:
- 默认走内存（向后兼容，单进程测试友好）
- `DISPATCH_CENTER_USE_DB=1` 启用 DB 模式
- DB 异常时 **fallback 内存 + ERROR 日志**（业务不中断）
- 查询方法（`get_all_tasks` / `get_task_by_id` / `get_task_count`）和撤回方法同步改造

**DDL（已创建）**: `docs/v3.7.8/ddl/dispatch_center_tasks.sql`

**测试覆盖**: `tests/unit/dispatch_center/test_publisher_v378_db.py` (20 用例全通过)

### ⚠️ P1: container_center_v5.py 使用 SQLite

**位置**: `mobile_api_ai/container_center_v5.py`

**问题**: 同时存在 SQLite 和 MySQL 两套存储，数据可能不一致

**修复建议**:
- v3.7.8: 保留 SQLite 作为 fallback（仅当 MySQL 不可用时）
- v3.7.9: 统一迁移到 MySQL
- v3.8.0: 删除 SQLite 文件

### ⚠️ P2: desktop_container_integration.py dict.update

**位置**: `desktop_container_integration.py:314, 340, 491`

**说明**: 这是 `pkg.content.update({...})` 修改 Python 对象，不是数据库写入。

**修复建议**: 保留（业务对象）

---

## 5. 数据流图

### 当前（混乱）
```
service
    ↓
desktop_container_integration.publish_report_task()
    ├─→ HTTP 5003 → container_api_server (✅) → 业务表 (✅)
    ├─→ SQLite (⚠️) → 业务表
    └─→ dict.update (✅)

[新版 publisher.py 不走这条路！]
service
    ↓
publisher.publish_report_task()
    └─→ 内存 Dict (❌ 重启丢)
```

### 目标（v3.7.8 ✅ 已达成）
```
service
    ↓
publisher.publish_report_task()
    ├─→ DISPATCH_CENTER_USE_DB=1?
    │     ├─ 是 → core.db_compat.get_conn() → dispatch_center_tasks 表 (✅)
    │     └─ 否 → 内存 Dict (兼容旧测试)
    └─→ 异常时 fallback 内存 + ERROR 日志 (业务不中断)
```

---

## 6. 修复优先级

| # | 任务 | 优先级 | 估时 | 负责人 | 状态 |
|---|------|:------:|:----:|:------:|:----:|
| 1 | publisher.py 改写 MySQL | 🔴 P0 | 2h | 小圣 | ✅ v3.7.8（双轨模式） |
| 2 | DDL 创建 dispatch_center_tasks 表 | 🔴 P0 | 30min | 小贺 | ✅ v3.7.8（docs/v3.7.8/ddl/） |
| 3 | 集成测试覆盖 publisher→MySQL | 🔴 P0 | 2h | 小钰 | ✅ v3.7.8（test_publisher_v378_db.py，20 用例） |
| 4 | container_center_v5 收敛到 MySQL | ⚠️ P1 | 1天 | 小圣 | ✅ v3.8.0（F6 P7 物理清理 + desktop_container_integration 同步移除 SQLite 路径） |
| 5 | docker-compose 启动所有依赖 | ⚠️ P1 | 1天 | 小钰 | ✅ v3.7.9（dispatch-5003 service 已加） |
| 6 | 删除 desktop_container_integration.py | ⚠️ P2 | 1天 | 小圣 | ⏳ 灰度期后（推荐新代码直接用 publisher.py） |

---

## 7. 决策记录

| # | 决策点 | 候选 | 最终 | 理由 | 实施状态 |
|---|--------|------|------|------|:--------:|
| D1 | publisher.py 存储 | A) 内存 B) MySQL C) SQLite D) HTTP | **B（+ 内存 fallback）** | 与现有 MySQL 架构一致；性能可控；DB 异常 fallback 内存（业务不中断） | ✅ v3.7.8 |
| D2 | 双模式保留？ | A) HTTP+SQLite B) 仅 MySQL C) 内存+MySQL（环境变量） | **C** | 单测/单进程用内存，生产用 DB；故障不中断业务 | ✅ v3.7.8 |
| D3 | SQLite 是否删除？ | A) 保留 B) 删除 C) Fallback | **B（彻底删除）** | F6 P7 物理清理已完成；desktop_container_integration 同步移除 SQLite 路径 | ✅ v3.8.0 |
| D4 | 单元测试 Mock 方式 | A) 直接 mock 字符串路径 B) sys.modules 注入 fake 模块 | **B** | 避开 core.config 预先存在 ImportError；隔离测试 | ✅ v3.7.8 |

---

## 8. 验证清单

- [x] 已盘点所有 INSERT/UPDATE/DELETE 位置
- [x] 已识别 4 套存储介质
- [x] 已分类 P0/P1/P2 优先级
- [x] 已列出每张表的修复建议
- [x] 已画数据流图（混乱 vs 目标）
- [x] 4 人会议通过

---

**下一步**: 实施 v3.7.8 任务 #1-3（pymysql + DDL + 集成测试）