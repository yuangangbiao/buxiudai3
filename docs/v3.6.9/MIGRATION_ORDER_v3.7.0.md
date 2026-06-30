# 数据迁移顺序方案 - v3.7.0

> **创建日期**: 2026-06-28
> **关联版本**: v3.7.0 架构重构（18周计划）
> **性质**: P1 文档，Week 1 建立，Layer1 替换前必须确认
> **目的**: 定义51处 pymysql.connect 替换的顺序，避免改一半系统崩溃

---

## 零、范围边界（v3.7.1明确）

> ⚠️ **脱水说明**：v3.7.0说"51处"，实际全量grep找到125处。
> 以下是v3.7.1明确的范围划分。

```
✅ v3.7.1 Layer1范围（51处，全部处理）：
  app.py 26处
  report_record_admin.py 20处
  _core.py 1处（仅主业务路由内1处）
  feature_flags.py 2处
  standalone 1处（后门漏洞）
  ===================
  合计：51处

🟡 v3.7.1 顺带处理（在Phase3期间）：
  dispatch_center/schedule_routes.py 4处
  dispatch_center/_core.py 内部查询

🔴 v3.7.1 明确排除（Phase5范围）：
  container_center_api.py 10处（独立服务）
  container_api_server.py 32处（独立服务）
  container/dispatcher.py 24处（容器模块）
  scripts/ ~30处（运维脚本，无并发泄漏）
  migrations/ ~15处（一次性脚本）
  ===========================
  合计：74处排除
```

**排除原因**：
- 独立服务（container_api_server等）改造不影响主系统连接池稳定性
- scripts/和migrations/是运维脚本，不是长期运行的服务，无连接泄漏风险
- Phase3自然覆盖dispatch_center相关直连
- Phase5（v3.8.x）再处理容器/container相关

---

## 一、替换本质

```
改前:  conn = pymysql.connect(...)       # 每次新建连接
       cur = conn.cursor()               # 无连接归还
       ...                               # 异常路径下 conn 可能泄漏
       cur.close(); conn.close()          # 手动关闭，容易忘

改后:  conn = g.storage.get_connection() # 从连接池取
       with conn.cursor() as cur:        # 自动管理游标
       ...                               # 异常时 g.storage.release_connection 归还
       # 无需手动 close/return          # Flask 请求结束时统一归还
```

---

## 二、替换顺序原则

### 2.1 优先级矩阵

| 维度 | 高优先级（先改） | 低优先级（后改） |
|------|----------------|----------------|
| **数据安全性** | 只读操作（SELECT） | 写操作（INSERT/UPDATE/DELETE） |
| **事务范围** | 无事务（自动提交） | 有显式 BEGIN/COMMIT |
| **外部依赖** | 无外部调用 | 有微信/企微/API外部调用 |
| **异常风险** | 逻辑简单（<10行） | 逻辑复杂（>50行） |
| **与已知Bug关系** | 无关 | 涉及BUG-P0/BUG-P1 |

### 2.2 替换顺序

```
Phase 0 → 只读 + 无事务 + 无外部调用（最低风险）
Phase 1 → 只读 + 无事务 + 有外部调用
Phase 2 → 有事务 + 无外部调用
Phase 3 → 有事务 + 有外部调用
Phase 4 → 复杂逻辑（>100行）—— 留到最后
```

---

## 三、51处替换详细清单（按优先级排序）

> 数据来源：app.py行号 + report_record_admin.py行号 + _core.py行号

### Phase 0：只读 + 无事务（Week 3，先改）

| # | 文件 | 行号 | 路由/函数 | 类型 | 理由 |
|---|------|------|---------|------|------|
| 1 | app.py | ~322 | auth/login | 只读 | SELECT user，登录验证 |
| 2 | app.py | ~340 | auth/userinfo | 只读 | SELECT user info |
| 3 | app.py | ~360 | process/list | 只读 | SELECT 生产列表 |
| 4 | app.py | ~380 | process/{id} | 只读 | SELECT 单条记录 |
| 5 | app.py | ~400 | quality/list | 只读 | SELECT 质检列表 |
| 6 | app.py | ~420 | quality/{id} | 只读 | SELECT 质检详情 |
| 7 | app.py | ~440 | quality_inspection/list | 只读 | SELECT 质检记录 |
| 8 | app.py | ~450 | message/list | 只读 | SELECT 消息列表 |
| 9 | app.py | ~460 | approval/list | 只读 | SELECT 审批列表 |
| 10 | app.py | ~470 | stats/overview | 只读 | SELECT 统计概览 |
| 11 | app.py | ~480 | stats/daily | 只读 | SELECT 每日统计 |
| 12 | app.py | ~490 | health | 只读 | SELECT 1，只读不写 |
| 13 | app.py | ~510 | scan/records | 只读 | SELECT 扫码记录 |
| 14 | app.py | ~2010 | process/idempotent | 只读 | SELECT 防重检查 |

**说明**：以上14处为"查数据"，即使替换出错，也最多返回空数据，不破坏现有数据。

### Phase 1：只读 + 涉及已知Bug（Week 3-4，配合Bug修复）

| # | 文件 | 行号 | 路由/函数 | 类型 | 关联Bug |
|---|------|------|---------|------|---------|
| 15 | app.py | ~? | process/my-tasks | 只读 | BUG-P1-001 |
| 16 | app.py | ~298 | process_sub_step（读端） | 只读 | BUG-P0-003 |
| 17 | app.py | ~? | scan/worker | 只读 | BUG-P0-002 |

**说明**：这3处虽然只读，但涉及已知Bug，替换前需先修Bug，否则改完验证时发现行为异常分不清是Bug还是替换引的。

### Phase 2：有事务/写操作（Week 5-6，高优先级）

| # | 文件 | 行号 | 路由/函数 | 类型 | 事务 |
|---|------|------|---------|------|:----:|
| 18 | app.py | ~298 | process_sub_step（写端） | INSERT/UPDATE | ✅ 显式事务 |
| 19 | app.py | ~300 | process/{id} PUT | UPDATE | ✅ 显式事务 |
| 20 | app.py | ~310 | process/{id}/publish | UPDATE | ✅ 显式事务 |
| 21 | app.py | ~320 | process/{id}/complete | UPDATE | ✅ 显式事务 |
| 22 | app.py | ~330 | process/substeps POST | INSERT | ✅ 显式事务 |
| 23 | app.py | ~340 | process/{id}/sync | UPDATE | ✅ 显式事务 |
| 24 | app.py | ~350 | quality POST | INSERT | ✅ 显式事务 |
| 25 | app.py | ~360 | quality PUT | UPDATE | ✅ 显式事务 |
| 26 | app.py | ~370 | quality_inspection POST | INSERT | ✅ 显式事务 |
| 27 | app.py | ~380 | message/send | INSERT | ✅ 显式事务 |
| 28 | app.py | ~390 | approval/{id} POST | UPDATE | ✅ 显式事务 |
| 29 | app.py | ~400 | scan/verify | INSERT | ✅ 显式事务 |

**说明**：以上12处涉及写操作，是数据库连接泄漏最严重的地方，也是Gate1（pytest）测试重点覆盖的区域。storage_layer的自动连接归还在这些地方价值最大。

### Phase 3：report_record_admin（Week 5-6）

| # | 文件 | 路由/函数 | 类型 | 事务 |
|---|------|---------|------|:----:|
| 30-49 | report_record_admin.py | 各路由 | MIXED | 部分事务 |

**说明**：20处来自 report_record_admin.py，按同上的 Phase 0→2 顺序替换。

### Phase 4：其他文件（Week 7-8）

| # | 文件 | 说明 |
|---|------|------|
| 50 | _core.py | dispatch_center内部，逻辑复杂（>100行） |
| 51 | feature_flags.py | 配置读取，风险低 |
| 52+ | 潜在遗漏 | 通过 grep "pymysql.connect" 复查确认 |

### Phase S（特殊处理，悲观审计H1新增）

> ⚠️ **悲观审计第1轮新增，第2轮修正**：scan.py 的连接泄漏问题**不在51处范围内**，但必须处理。
> ⚠️ **重要修正**：scan.py 连的是**容器数据库**（`CONTAINER_MYSQL_CFG`），不是主系统的 `storage_layer`。
> 不能用 `g.storage.get_connection()`（会连错数据库），需要为容器DB建立独立连接池。

| # | 文件 | 问题 | 位置 | 类型 | 说明 |
|---|------|------|------|:----:|------|
| S1 | `api/scan.py` | 连接泄漏（异常路径不归还） | L224-242 | 🔴 高危 | `_get_conn()` 直连容器DB，异常路径 `conn.close()` 不执行 |

**scan.py 连接泄漏源码证据**：

```python
# api/scan.py L3-4 + L18-19 + L219-242
# 注释说明：扫码模块从容器中心获取数据，不直接调用主数据库
"""
扫码模块 - 从容器中心获取数据
不直接调用主数据库，数据来源：中间容器池
"""
from core.config import CONTAINER_MYSQL_CFG
from core.db import get_direct_connection

def _get_conn():
    return get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)

def scan_worker(worker_id):
    try:
        conn = _get_conn()         # ← 连容器DB，不是主DB
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.close()                # ← 🔴 try块里，异常时泄漏！
        return success(...)
    except Exception as e:
        logger.exception("scan_worker error")
        return fail(...)           # ← 🔴 异常路径：conn未close！
```

**修复方案（为容器DB建立独立连接池）**：

```python
# api/scan.py

# 方案A（推荐）：为容器DB建立DBUtils连接池
from DBUtils.PooledDB import PooledDB
import pymysql

_CONTAINER_POOL = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=2,
    maxcached=5,
    blocking=True,
    **CONTAINER_MYSQL_CFG
)

def _get_conn():
    return _CONTAINER_POOL.connection()

def scan_worker(worker_id):
    conn = _get_conn()  # 从容器池取
    try:
        with conn.cursor(DictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        # with退出自动关闭游标
        return success(...)
    except Exception as e:
        logger.exception("scan_worker error")
        return fail(...)
    finally:
        conn.close()  # 归还到池，不是真正关闭
```

**为什么不能用 g.storage**：
- `g.storage` 是主系统的存储层（`MYSQL_CFG`）
- scan.py 的数据来自容器中心（`CONTAINER_MYSQL_CFG`），是两个不同的数据库
- 两者不能混用

---

## 四、替换验证检查表

每替换一处，必须完成以下检查：

### 技术验证（开发自测）

```
[ ] 替换后跑该路由的手动测试（用真实数据）
[ ] 替换后跑关联的 pytest（如果有）
[ ] 检查该路由在 app.py 中的事务逻辑是否完整
[ ] 确认没有遗漏的 cursor.close() / conn.close()
[ ] 确认异常路径（try/except）正确释放连接
```

### 数据一致性验证

```
[ ] 替换前记录：某查询的返回值条数/字段
[ ] 替换后对比：返回值条数/字段完全一致
[ ] 边界值测试：空结果/单条/大批量（>100条）
```

### 兼容性验证（STORAGE_COMPATIBILITY）

```
[ ] pymysql.err.OperationalError 能正确抛出
[ ] pymysql.err.IntegrityError 能正确抛出
[ ] cursor.fetchone() 返回 dict 类型（DictCursor）
[ ] 游标自动关闭（with 语法）
```

---

## 五、替换失败应急方案

### 5.1 替换后该路由报错

```
立即回退：
  git checkout {改动的文件} -- src_file.py
  # 手动恢复该文件到改前版本

然后：
  1. 确认是替换引的错还是原有Bug
  2. 修好后用 git diff 确认改动
  3. 再次替换，注意兼容性检查
```

### 5.2 替换后数据不一致

```
立即停手，不要继续替换其他路由

然后：
  1. 对比改前改后的返回值
  2. 确认 DictCursor vs TupleCursor 差异
  3. 确认字段映射是否一致
  4. 更新 STORAGE_COMPATIBILITY 矩阵
```

### 5.3 替换后连接泄漏更严重

```
立即检查 storage_layer 的 release_connection 是否在所有路径调用

storage_layer 规范：
  def get_connection():
      return g.storage.get_connection()

  try:
      with conn.cursor() as cur:
          cur.execute(...)
          result = cur.fetchone()
      # with退出自动关闭cursor
  finally:
      g.storage.release_connection(conn)
      # finally保证异常时也归还
```

---

## 六、特殊场景处理

### 6.1 batch_no 分支（最易漏改）

app.py中某些路由有 `batch_no` 判断分支，里面也有 `pymysql.connect`，替换时不要漏掉：

```python
# 替换前：batch_no 分支里的直连
if batch_no:
    conn2 = pymysql.connect(...)  # ← 容易漏
    cur2 = conn2.cursor()
    cur2.execute(...)
    conn2.close()

# 替换后：
if batch_no:
    conn2 = g.storage.get_connection()  # ← 统一池
    try:
        with conn2.cursor() as cur2:
            cur2.execute(...)
    finally:
        g.storage.release_connection(conn2)
```

### 6.2 auth.logout 的 conn 关闭

logout 路由有时会更新 last_login 字段，有事务。替换时注意事务完整性。

### 6.3 health 路由的特殊性

health 路由通常用 `SELECT 1`，但如果用了 `SHOW PROCESSLIST` 等管理命令，不走 storage_layer（因为 storage_layer 本身也要查数据库，会循环依赖）。这种情况保留 `pymysql.connect` 直连。

---

## 七、替换节奏

| 阶段 | 时间 | 替换数量 | 通过Gate标准 |
|------|------|:-------:|------------|
| Phase 0 | Week 3 第1-2天 | 14处 | pytest ≥ 90% + 手动验证 |
| Phase 1 | Week 3 第3-4天 | 3处 | 配合Bug修复一起验证 |
| Phase 2 | Week 4 | 15处 | pytest ≥ 95% + 全量手动验证 |
| Phase 3 | Week 5-6 | 20处 | pytest ≥ 95% + G1放量签字 |
| Phase 4 | Week 7-8 | 其余 | 全量回归 + G3放量签字 |
| **Phase S** | **Week 2（与Phase0并行）** | **1处（scan.py）** | **连接泄漏修复验证** |

**核心原则**：每批次替换完成后，必须跑全量回归测试（特别是本批次涉及的路由），确认无异常后才能进入下一批次。

---

**维护人**: 开发团队
**最后更新**: 2026-06-28（悲观审计第1轮修复：补充Phase S scan.py连接泄漏）
**审查时机**: 每次替换批次完成后
