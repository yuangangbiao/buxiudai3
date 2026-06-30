# 架构漏洞报告 v3.6.8

> **扫描日期**: 2026-06-25
> **扫描范围**: mobile_api_ai/app.py, cloud_poller.py, dispatch_center/_core.py, container/task_pool.py, core/db.py
> **扫描方法**: 静态分析 + 源码交叉验证
> **覆盖**: P3 待审(5项) + 新发现(12项) = 17项

---

## 一、P3 待审项目（来自专家团队会议纪要）

| 编号 | 问题 | 优先级 | 备注 |
|------|------|:------:|------|
| P3-1 | **物料短缺列表不走连接池** | 高 | 高并发下连接耗尽 |
| P3-2 | **缓存 TTL 7 套散落** | 中 | 配置不一致 |
| P3-3 | **get_packages_count_group 硬编码 5 表** | 低 | 可扩展性差 |
| P3-4 | **跨 worker 数据竞争**（A5+A10）| 高 | 多进程内存不同步 |
| P3-5 | **4 个 conftest 协调冲突**（A6）| 中 | 测试隔离失败 |

---

## 二、新发现架构漏洞

### 🔴 高危（立即修复）

#### ARC-1: app.py 2247 行——上帝文件

**位置**: `mobile_api_ai/app.py`

**问题**: 一个文件包含 40+ 个路由处理函数，涵盖：
- 报工 CRUD（process_sub_step/withdraw/history/update）
- 报工记录管理（report_record CRUD × 3 表 × 4 操作）
- 质检记录管理（quality_record × 4 操作）
- 物料记录管理（material_record × 4 操作）
- 外协记录管理（outsource_record × 4 操作）
- 排产记录管理（schedule_record × 4 操作）
- 物料流程（material_confirm/arrived/delivered）
- 入库（warehousing_pending/confirm）
- 扫码报工、队列管理……
- 启动逻辑（StorageFactory、StatsEngine、report-queue-worker）

**风险**:
- 单点故障（任何 bug 导致整个文件不可编辑）
- 无法独立测试单个模块
- 新人 onboarding 成本极高
- 多人协作 git 冲突不可避免

**建议**: 按领域拆分为独立蓝图：
```
mobile_api_ai/api/
├── report.py        # 报工 CRUD
├── report_record.py # 调度中心报工记录管理（质量/物料/外协/排产）
├── material.py      # 物料流程 + 入库
├── scanner.py       # 扫码报工
└── queue.py         # 队列管理
```

---

#### ARC-2: 所有管理接口无身份认证

**位置**: `mobile_api_ai/app.py` 多处

```python
# L521-622: report_record_update — 调度员修改报工记录
# L623-687: report_record_admin_withdraw — 调度员撤回报工
# L772-850: quality_record_update — 调度员修改质检记录
# L853-925: quality_record_admin_withdraw — 调度员撤回质检记录
# L1009-1073: material_record_update — 物料修正
# L1076-1127: material_record_admin_withdraw — 物料撤回
# L1208-1269: outsource_record_update — 外协修正
# L1271-1320: outsource_record_admin_withdraw — 外协撤回
# L1401-1461: schedule_record_update — 排产修正
# L1464-1511: schedule_record_admin_withdraw — 排产撤回
```

**问题**: `admin_user = body.get('admin_user', '').strip()` 仅作为字符串参数传入，无任何验证机制：
- 任何知道接口 URL 的人可以冒充任意调度员
- 可修改/撤回任意订单的报工记录
- 无审计日志（虽然有 history 表，但前提是请求来源可信）

**P2-3 的影响**: 全局异常处理器捕获了错误响应，但无法防止恶意正常请求

**修复建议**: 在 `core/auth.py` 实现 `require_admin(request)` 装饰器：
```python
def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token: return jsonify({'code': 401}), 401
        # 验证 JWT + 检查 role=admin
        payload = verify_jwt(token)
        if payload.get('role') != 'admin':
            return jsonify({'code': 403}), 403
        return f(*args, **kwargs)
    return decorated
```

---

#### ARC-3: SQL 注入——LIKE 模式拼接

**位置**: `mobile_api_ai/app.py`

**根因**: `f"%{order_no}%"` 直接内联到 SQL，F-string 拼接：

```python
# L490: report_record_list
where.append("s.order_no LIKE %s"); params.append(f"%{order_no}%")

# L734-744: quality_record_list
where.append("qr.order_no LIKE %s"); params.append(f"%{order_no}%")

# L970-972: material_record_list
where.append("(dp.related_order LIKE %s OR dp.title LIKE %s)")
params.append(f"%{order_no}%"); params.append(f"%{order_no}%")
```

**分析**: 当前绑定变量用法正确（`params.append(...)` 绑定参数，`%s` 占位符），`f"%{...}%"` 是 Python 字符串拼接，不构成注入。

**但是**：如果 order_no 包含 `%` 或 `_`（LIKE 通配符），查询语义会改变，可能导致：
- `%` 匹配任意字符（误扩范围）
- `_` 匹配单个字符（误缩范围）

**风险等级**: 低（不会导致数据泄露或破坏，但可能返回错误数据）

**修复**: LIKE 之前 escape 通配符：
```python
params.append(f"%{order_no.replace('%', r'\%').replace('_', r'\_')}%")
```

---

#### ARC-4: 连接泄漏——except 块 return 前未关闭连接

**位置**: `mobile_api_ai/app.py` 多处

**模式**: 在 `except` 块中 `return` 前忘记调用 `conn.close()`：

```python
# L454: withdraw_sub_step
except Exception as e:
    conn.rollback()
    logger.error(...)
    conn.close()   # ✅ 有
    return jsonify(...), 500  # OK

# L599: report_record_update (宽边界事务回滚)
except Exception as e:
    conn.rollback()
    logger.error(...)
    conn.close()   # ✅ 有
    return jsonify(...), 500  # OK

# L667: report_record_admin_withdraw (撤回事务回滚)
except Exception as e:
    conn.rollback()
    logger.error(...)
    conn.close()   # ✅ 有
    return jsonify(...), 500  # OK
```

**深入核查**: 经验证，上述 3 处都有 `conn.close()`。但需全量扫描确认。

**风险**: 如果 conn.close() 缺失，MySQL 连接会保持 `TIME_WAIT` 状态，高频请求下耗尽连接池。

---

### 🟡 中危（近期修复）

#### ARC-5: cloud_poller 退出超时环境变量未验证

**位置**: `mobile_api_ai/cloud_poller.py` L525

```python
self.poll_thread.join(timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
```

**问题**:
- `os.environ.get('REQUEST_TIMEOUT_FAST', '5')` 返回字符串 `'5'`，`int('5')` → 5 秒，**看起来正常**
- 但如果 `.env` 中误配置为 `REQUEST_TIMEOUT_FAST=`（空字符串），`int('')` 会抛出 `ValueError` 导致程序崩溃
- 实际上在 Python 中 `int('')` 会在运行时抛异常，而不是编译时

**风险**: 环境变量配置错误时服务无法启动。

**修复**:
```python
timeout_str = os.environ.get('REQUEST_TIMEOUT_FAST', '5')
try:
    _timeout = max(1, int(timeout_str))
except (ValueError, TypeError):
    _timeout = 5
self.poll_thread.join(timeout=_timeout)
```

---

#### ARC-6: cloud_poller 重初始化后旧实例资源泄漏

**位置**: `mobile_api_ai/cloud_poller.py` L507-517

```python
def init_cloud_poller():
    global _cloud_poller
    if _cloud_poller:
        _cloud_poller.stop()      # 停止旧实例
    _cloud_poller = CloudPoller()
    _cloud_poller.start()
```

**问题**: `stop()` 调用了 `self._executor.shutdown(wait=False)`（L526），但 `wait=False` 意味着正在执行的任务被直接中断，未完成的工作丢失。

**风险**: 重初始化时丢消息（如果 cloud_poller 负责某种消息投递）。

**需确认**: cloud_poller 的 `_poll_loop` 具体业务角色——如果仅用于健康检查，影响较小。

---

#### ARC-7: cloud_poller _poll_loop 无线程守卫

**位置**: `mobile_api_ai/cloud_poller.py` L516-517

```python
self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
self.poll_thread.start()
```

**对比 dispatch_center（已修复 P2-5）**:
```python
if self._persist_thread is not None and self._persist_thread.is_alive():
    pass  # 旧线程仍在则不创建新的
else:
    self._persist_thread = threading.Thread(target=self._throttled_persist, daemon=True)
    self._persist_thread.start()
```

**cloud_poller 的区别**: `init_cloud_poller()` 有 `if _cloud_poller:` 全局守卫（只初始化一次），但 `_poll_loop` 本身没有防止自身被并发启动的检查。

**风险**: 低（因为全局初始化只发生一次），但与 P2-5 模式不一致，建议对齐。

---

#### ARC-8: report-queue-worker 内存记录漂移

**位置**: `mobile_api_ai/app.py` L2151-2237

```python
def _start_report_queue_worker():
    t = threading.Thread(target=_worker, daemon=True, name='report-queue-worker')
    t.start()

_start_report_queue_worker()  # 模块加载时立即启动
```

**问题**:
- 在 `app = create_app()` 后立即启动（L2239）
- Worker 从 `dequeue_pending_reports()` 拿数据，但处理后的 `data_packages` 完成量更新逻辑（L2196-2208）是在内存中循环查找而非批量操作：
```python
pkgs = cc.storage.get_packages(limit=500)  # 每次取 500 条
for pkg in pkgs:
    if pkg.get('related_order') == order_no and (...):  # 内存遍历
```
- 这与 P2-6 的 N+1 问题本质相同：应该按 `order_no` 直接 UPDATE，而非加载 500 条再遍历

**风险**: 低（不会导致错误，但效率低）

---

### 🟢 低危（观察/技术债）

#### ARC-9: TaskPool 模块级实例化

**位置**: `mobile_api_ai/container/task_pool.py` L471

```python
task_pool = TaskPool()  # 模块加载时立即创建
```

**问题**: `TaskPool.__init__` 会尝试连接数据库（根据 storage_config）：
```python
# L155-174: storage_config 为 None 时走 MySQL 路径
self.storage = MySQLStorage()
self.storage.connect()  # 连接数据库
```

**风险**: 如果 MySQL 不可用，模块加载失败，导致所有依赖 `task_pool` 的代码（如 `container_api_server.py`）全部无法导入。

**现状**: `task_pool.py` 有 fallback 逻辑（SQLite），但需要确认 fallback 路径在生产环境是否正常工作。

---

#### ARC-10: str(e) 在 app.py 中仍大量存在

**位置**: `mobile_api_ai/app.py` 至少 30 处

P2-3 只覆盖了 `desktop_web/server.py`，但 `mobile_api_ai/app.py` 的 2247 行中有大量 `str(e)`：

L271, L350, L459, L518, L620, L686, L715, L769, L849, L924, L953, L1006, L1073, L1127, L1155, L1206, L1269, L1320, L1348, L1398, L1461, L1511, L1539, L1614, L1650, L1680, L1702, L1757, L1781, L1819, L1861, L1872, L1891, L2007, L2043, L2088

**影响**: 异常时返回 `str(e)` 可能泄露：
- 数据库表名/列名（KeyError on missing column）
- SQL 语法错误（OperationalError）
- 网络超时信息

---

#### ARC-11: desktop_web/server.py str(e) 仍有 2 处未处理

**位置**: `desktop_web/server.py` L1103, L2843

L1103: `errors.append({'row': idx + 2, 'msg': str(e)[:80]})` — 批量导入错误收集，80 字符截断，相对安全。

L2843: `errors.append({'row': idx + 2, 'msg': f'单行处理失败: {str(e)[:100]}'})` — 同样截断。

**评估**: 已截断到 80/100 字符，风险较低，但建议统一改为 `'单行处理失败，请检查数据格式'`。

---

#### ARC-12: app.py 无 rate limiting（管理接口）

**位置**: `mobile_api_ai/app.py` 全部管理接口

虽然 `limiter` 已初始化（L51: `limiter.init_app(app)`），但：
- 没有任何 `@limiter.limit(...)` 装饰器应用在管理接口上
- `report_record_update`、`quality_record_update` 等高危操作无并发限制
- 恶意用户可以短时间内大量修改/撤回记录

**对比**: 报工接口（process_sub_step）有幂等去重，但管理接口无此保护。

---

## 三、漏洞优先级矩阵

```
         严重性
         高    中    低
    ┌─────┬─────┬─────┐
 影 高 │     │ARC-5│ARC-7│
 响 中 │ARC-1│ARC-3│ARC-9│
 度 低 │     │ARC-6│ARC-11│
    │     │ARC-8│     │
    └─────┴─────┴─────┘

修复状态：
  ARC-2  ✅ 已修复（10个管理接口加JWT认证）
  ARC-4  ✅ 已修复（质量记录端点except块补conn.close()）
  ARC-10 ✅ 已修复（app.py 35处str(e)替换）
  ARC-12 ✅ 已修复（10个管理接口加rate limit）
```

## 四、已修复项目（v3.6.8 本次修复）

### ✅ ARC-2: 管理接口 JWT 认证
- **文件**: mobile_api_ai/api/decorators.py + mobile_api_ai/app.py
- **修复**: 新增 `require_admin` 装饰器，验证 Bearer JWT token 并检查 role ∈ {管理员, 操作员}
- **覆盖**: 10 个管理端点（report/quality/material/outsource/schedule × update+withdraw）
- **效果**: 无效/过期令牌 → 401；权限不足 → 403

### ✅ ARC-10: app.py str(e) 泄露点替换
- **文件**: mobile_api_ai/app.py
- **修复**: 35 处 `str(e)` → 业务友好错误消息
- **覆盖**: 所有端点 except 块（L271/350/459/518/616/683/711/765/846/921/949/1002/1069/1123/1151/1202/1265/1316/1344/1395/1458/1508/1536/1611/1647/1676/1699/1754/1778/1816/1858/1869/1888/2040/2085）
- **保留**: L2222 `mark_report_failed(qid, str(e)[:255])` — 内部日志，安全截断

### ✅ ARC-12: 管理接口频率限制
- **文件**: mobile_api_ai/app.py
- **修复**: 10 个管理端点加 `@limiter.limit("10 per minute")`
- **效果**: 每分钟最多 10 次，防止高频恶意调用

### ✅ ARC-5: 环境变量验证
- **文件**: mobile_api_ai/cloud_poller.py
- **修复**: `REQUEST_TIMEOUT_FAST` 空值/非法值 → 捕获异常并降级为 5 秒

### ✅ ARC-4: 连接泄漏扫描
- **文件**: mobile_api_ai/app.py
- **修复**: quality_record_update 和 quality_record_admin_withdraw 的 except 块补 `conn.close()`
- **扫描范围**: 80 个 except 块全部审查

## 五、待修复项目

### 本周修复

| 编号 | 动作 | 文件 |
|------|------|------|
| ARC-1 | app.py 按领域拆分为独立蓝图 | mobile_api_ai/api/ |
| ARC-6 | cloud_poller shutdown(wait=True) | cloud_poller.py |

### 观察（可延期）

| 编号 | 动作 | 优先级 |
|------|------|:------:|
| ARC-3 | LIKE 通配符 escape | 低 |
| ARC-7 | cloud_poller 线程守卫对齐 | 低 |
| ARC-8 | Worker 内 N+1 优化 | 低 |
| ARC-9 | TaskPool 延迟初始化 | 低 |
| ARC-11 | desktop_web str(e) 截断统一 | 低 |

---

## 六、附录：文件规模统计

| 文件 | 行数 | 路由数 | 状态 |
|------|-----:|------:|------|
| mobile_api_ai/app.py | ~2260 | ~45 | 🟡 需拆分 |
| mobile_api_ai/cloud_poller.py | ~740 | 0 | 🟢 已修复 ARC-5 |
| desktop_web/server.py | ~2910 | ~90 | 🟢 已修复 P2 |
| dispatch_center/_core.py | ~970 | 0 | 🟢 已修复 P2-5/6 |
| container/task_pool.py | ~490 | 0 | 🟢 需审查 fallback |
