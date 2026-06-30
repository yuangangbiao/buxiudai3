# Bug Hunting Round 2 — 2026-06-18

## 目标
工序任务 + 扫码工人模块漏洞测试

## 环境
- 5003: standalone_dispatch_server (dispatch_center 蓝图)
- 5008: app.py (process + scan 蓝图)
- container_center @ 127.0.0.1:3306

---

## Bug #1 — my-tasks 过滤条件过严，18条任务漏查

### 严重度
**P1** — 工人看不到自己的工序任务

### 症状
`GET /api/process/my-tasks?worker_id=YuanGangBiao` 返回 0 条任务，但数据库有 18 条 data_packages。

### 根因
`api/process.py` 的 SQL 过滤条件：
```sql
WHERE data_type IN ('report','task','work_order')
```
实际数据包含更多类型：
| data_type | 条数 | 能否查到 |
|-----------|------|---------|
| `flow_step` | 9 | ❌ 被过滤 |
| `process_report` | 6 | ❌ 被过滤 |
| `quality_task` | 1 | ❌ 被过滤 |
| `report/task/work_order` | 0 | - |

### 修复
```sql
WHERE data_type IN ('report','task','work_order','flow_step','process_report','quality_task')
```
Commit: `06f1077e`

---

## Bug #2 — scan-worker 返回假数据，不验证工人

### 严重度
**P0** — 任意输入都返回伪造工人信息，可能导致报工/考勤挂错人

### 症状
```
GET /api/scan/worker/NONEXISTENT999 → 200, data={worker_id:"NONEXISTENT999", name:"NONEXISTENT999"}
GET /api/scan/worker/张三           → 200, data={worker_id:"张三", name:"张三"}
GET /api/scan/worker/'; DROP TABLE -- → 200, data={worker_id:"...", name:"..."}
```

### 根因
`api/scan.py` 硬编码返回假数据：
```python
def scan_worker(worker_id):
    return success(data={
        'worker_id': worker_id,
        'name': worker_id,
        'role': '工人'
    })
```

### 修复
查 `workers` 表，按 `wechat_userid` 匹配：
```python
cur.execute(
    "SELECT id, wechat_userid, name, role, phone, department FROM workers WHERE wechat_userid = %s",
    (worker_id,))
row = cur.fetchone()
if not row:
    return fail(code=404, message="工人不存在")
return success(data={
    'worker_id': row['wechat_userid'],
    'name': row['name'],
    'role': row['role'] or '员工',
    ...
})
```
Commit: `06f1077e`

---

## 验证结果

| 测试 | 结果 |
|------|------|
| `my-tasks?worker_id=YuanGangBiao` | ✅ 18条任务 |
| `scan-worker/YuanGangBiao` | ✅ 苑岗彪/员工 |
| `scan-worker/NONEXISTENT999` | ✅ 404 |
| `scan-worker/OP003`（无微信ID）| ✅ 404 |
