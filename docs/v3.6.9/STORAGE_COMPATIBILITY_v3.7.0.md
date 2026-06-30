# storage_layer 兼容性矩阵 - v3.7.0

> **创建日期**: 2026-06-28
> **关联版本**: v3.7.0 Week 1（Layer1启动前必须完成）
> **性质**: P1 文档，Layer1 改造前必须签字
> **审计来源**: 4专家审计（小圣架构）→ O-2

---

## 一、改造范围（51处生产代码）

### 1.1 按文件分布

| 文件 | 数量 | 批次 | 风险 |
|------|:----:|------|:----:|
| `app.py` | 26处 | 第一批 | 🔴 最高 |
| `api/report_record_admin.py` | 20处 | 第二批 | 🔴 高 |
| `standalone_dispatch_server.py` | 1处 | 第三批 | 🟡 低 |
| `dispatch_center/_core.py` | 1处 | 第三批 | 🟡 低 |
| `wechat_work_bot_bp.py` | 1处 | 第三批 | 🟢 低 |
| `api/legacy_routes.py` | 1处 | 第三批 | 🟢 低 |
| `config/feature_flags.py` | 2处 | 第四批 | 🟢 低 |

---

## 二、storage_layer API 规格

### 2.1 当前API

```python
from mobile_api_ai.storage_layer import create_storage

storage = create_storage()  # 内部读 CONTAINER_MYSQL_CFG，返回 MySQLStorage 实例
conn = storage.get_connection()  # 获取连接（来自PooledDB）
cursor = conn.cursor()          # 获取游标（与pymysql.connect行为一致）
try:
    cursor.execute(sql, params)
    result = cursor.fetchone() / fetchall() / rowcount
finally:
    storage.release_connection(conn)  # 归还连接到池
```

### 2.2 异常类型对比

| 维度 | pymysql.connect() | storage.get_connection() |
|------|-----------------|------------------------|
| 连接失败 | `pymysql.err.OperationalError` | `pymysql.err.OperationalError` ✅ 一致 |
| 参数错误 | `pymysql.err.ProgrammingError` | `pymysql.err.ProgrammingError` ✅ 一致 |
| 连接超时 | `pymysql.err.OperationalError`（connect_timeout=2） | `pymysql.err.OperationalError`（pooled自动重试） |
| 游标类型 | `pymysql.cursors.DictCursor` 或默认 | 默认 `pymysql.cursors.DictCursor` ✅ 一致 |
| 事务控制 | `conn.begin()` / `conn.commit()` / `conn.rollback()` | 同 ✅ |

### 2.3 兼容性结论

> **结论：storage_layer 与 pymysql.connect() 在异常类型和游标行为上完全兼容。**
> 51处代码的 try-except 捕获逻辑无需修改，可直接替换。

---

## 三、51处替换清单（逐文件）

### 3.1 app.py（26处）

> **文件**: `mobile_api_ai/app.py`
> **风险**: 🔴 最高（主服务5008，影响最大）
> **改造前必须**: 建立pytest测试框架 + 性能baseline

| # | 行号 | 函数/路由 | 替换方式 | 风险 | 验证 |
|---|:----:|----------|---------|:----:|------|
| 1 | 322 | auth.bp | get_connection → release_connection | 🔴 | 登录功能回归 |
| 2 | 416 | scan.bp | 同上 | 🔴 | 扫码功能回归 |
| 3 | 506 | process.bp | 同上 | 🔴 | 工序查询回归 |
| 4 | 547 | process.bp | 同上 | 🔴 | 工序修改回归 |
| 5 | 644 | quality.bp | 同上 | 🔴 | 质检功能回归 |
| 6 | 708 | quality.bp | 同上 | 🔴 | 质检查询回归 |
| 7 | 754 | quality.bp | 同上 | 🔴 | 质检列表回归 |
| 8 | 799 | message.bp | 同上 | 🟡 | 消息查询回归 |
| 9 | 879 | approval.bp | 同上 | 🟡 | 审批功能回归 |
| 10 | 952 | health.bp | 同上 | 🟡 | 健康检查回归 |
| 11 | 999 | stats.bp | 同上 | 🟡 | 统计功能回归 |
| 12 | 1042 | stats.bp | 同上 | 🟡 | 统计查询回归 |
| 13 | 1095 | process.bp | 同上 | 🔴 | 工序详情回归 |
| 14 | 1140 | process.bp | 同上 | 🔴 | 工序更新回归 |
| 15 | 1183 | quality_inspection.bp | 同上 | 🔴 | 质检检验回归 |
| 16 | 1223 | quality_inspection.bp | 同上 | 🔴 | 检验列表回归 |
| 17 | 1274 | quality_inspection.bp | 同上 | 🔴 | 检验详情回归 |
| 18 | 1317 | process.bp | 同上 | 🔴 | 工序列表回归 |
| 19 | 1361 | process.bp | 同上 | 🔴 | 工序状态回归 |
| 20 | 1412 | quality.bp | 同上 | 🔴 | 质检新建回归 |
| 21 | 1497 | process.bp | 同上 | 🔴 | 工序子步骤回归 |
| 22 | 1550 | process.bp | 同上 | 🔴 | 子步骤详情回归 |
| 23 | 1784 | process.bp | 同上 | 🔴 | 工序同步回归 |
| 24 | 2010 | process.bp | 同上（if分支内，特殊） | 🔴 | 幂等检查回归 |
| 25 | 2097 | process.bp | 同上 | 🔴 | 工序发布回归 |
| 26 | 2132 | process.bp | 同上 | 🔴 | 工序完工回归 |

**注**：第24处（行2010）在 `batch_no` 非空的if分支内，是唯一不带 `CONTAINER_MYSQL_CFG` 参数前缀的调用，需单独处理。

---

### 3.2 api/report_record_admin.py（20处）

> **文件**: `mobile_api_ai/api/report_record_admin.py`
> **风险**: 🔴 高（admin管理路由）
> **改造方式**: 同 app.py

| # | 行号 | 函数 | # | 行号 | 函数 |
|---|:----:|------|---|:----:|------|
| 1 | 76 | list_report_records | 11 | 648 | get_report_detail |
| 2 | 113 | create_report_record | 12 | 706 | update_report_status |
| 3 | 150 | get_report_record | 13 | 748 | batch_update_status |
| 4 | 193 | update_report_record | 14 | 799 | export_report_data |
| 5 | 236 | delete_report_record | 15 | 845 | get_report_summary |
| 6 | 278 | submit_report_approval | 16 | 891 | get_report_statistics |
| 7 | 330 | approve_report | 17 | 935 | get_report_history |
| 8 | 389 | reject_report | 18 | 979 | restore_report_record |
| 9 | 455 | get_report_comments | 19 | 1015 | batch_delete_reports |
| 10 | 509 | add_report_comment | 20 | 1075 | get_report_by_date_range |

---

### 3.3 其他文件（5处）

| # | 文件 | 行号 | 函数 | 风险 | 备注 |
|---|------|:----:|------|:----:|------|
| 27 | standalone_dispatch_server.py | 107 | auth相关 | 🟡 | 独立部署，影响面小 |
| 28 | dispatch_center/_core.py | 2380 | 核心业务逻辑 | 🟡 | 需确认Part归属 |
| 29 | wechat_work_bot_bp.py | 161 | 微信机器人 | 🟢 | 独立功能 |
| 30 | api/legacy_routes.py | 30 | 遗留兼容路由 | 🟢 | 历史兼容 |
| 31 | config/feature_flags.py | 99 | FeatureFlagManager.reload | 🟢 | 启动时调用，非热路径 |
| 32 | config/feature_flags.py | 146 | FeatureFlagManager.set_flag | 🟢 | 同上 |

---

## 四、Flask 上下文注入模式

### 4.1 全局单例模式（推荐）

```python
# mobile_api_ai/app.py 顶部新增
from mobile_api_ai.storage_layer import create_storage

_storage_instance = None

def get_storage():
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = create_storage()
    return _storage_instance

# Flask before_request 钩子
@app.before_request
def inject_storage():
    from flask import g
    g.storage = get_storage()
```

### 4.2 替换模板

```python
# 替换前（每处共3行）
conn = pymysql.connect(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
cur = conn.cursor()
try:
    cur.execute(sql, params)
    result = cur.fetchone()
finally:
    cur.close()
    conn.close()

# 替换后（每处共3行）
conn = g.storage.get_connection()
try:
    with conn.cursor() as cur:  # 或 cur = conn.cursor()
        cur.execute(sql, params)
        result = cur.fetchone()
finally:
    g.storage.release_connection(conn)
```

### 4.3 特殊处理：app.py:2010（batch_no分支）

```python
# 替换前（行2005-2019）
if batch_no:
    conn = pymysql.connect(...)  # ← 单独创建连接
    try:
        cur.execute(sql, (batch_no,))
        existing = cur.fetchone()
    finally:
        conn.close()

# 替换后
if batch_no:
    conn = g.storage.get_connection()  # ← 复用池化连接
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (batch_no,))
            existing = cur.fetchone()
    finally:
        g.storage.release_connection(conn)
```

---

## 五、兼容性验证清单（每处替换后）

| # | 验证项 | 操作 | 通过标准 |
|---|--------|------|---------|
| 1 | 异常类型 | 故意传入错误SQL | 抛出 pymysql.err.ProgrammingError ✅ |
| 2 | 游标类型 | 查询后检查返回类型 | dict 类型 ✅ |
| 3 | 连接复用 | 连续两次请求 | 使用同一个连接 ✅（从池复用） |
| 4 | 连接归还 | 异常分支 | 连接正确归还到池 ✅ |
| 5 | 事务控制 | 显式 commit | 数据正确持久化 ✅ |
| 6 | 超时处理 | 设置 connect_timeout=2 | 超时正确抛出异常 ✅ |

---

## 六、改造风险矩阵

| 风险 | 描述 | 影响文件 | 缓解措施 |
|------|------|---------|---------|
| 连接未归还 | 异常分支忘记 release_connection | 全部26处 | 使用 `with conn.cursor()` 语法糖 |
| 连接池耗尽 | 高并发下池大小不够 | app.py 全部 | PooledDB(maxconnections=50) 已配置，监控告警 |
| 游标类型不一致 | 默认游标 vs DictCursor | 全部 | storage_layer 默认 DictCursor，一致 |
| 异常处理失效 | try-except 捕获不到新异常 | 全部 | 异常类型兼容，无需修改 except |
| batch_no分支遗漏 | 行2010是if分支内调用 | 仅app.py:2010 | 单独处理，逐行检查 |

---

## 七、签字确认

| 签字人 | 职责 | 签字 |
|--------|------|------|
| 开发负责人 | 逐文件验证替换正确性 | ☐ |
| 架构（小圣） | 验证连接池配置正确性 | ☐ |
| 品控（小贺） | 验证26+20路由回归测试通过 | ☐ |

**改造前必须**: storage_layer 兼容性矩阵全部签字
**最后更新**: 2026-06-28
