# P0-I: 跨库原子事务设计方案

> **版本**: v1.0
> **创建日期**: 2026-07-01
> **负责人**: TRAE AI
> **优先级**: P0（高）

---

## 一、问题分析

### 1.1 当前问题

报工流程涉及两个数据库：

```
手机端(5008) → process_sub_steps (wechat_container.db)
              ↓ 同步
桌面端(5002) → orders/process_records (steel_belt.db)
```

**当前代码**（`mobile_api_ai/app.py`）：
```python
# 1. 原子写入 process_sub_steps（单事务）
_storage.save_process_sub_step_with_pkg_update(...)

# 2. 异步同步到桌面端（可能失败！）
sync_ok = sync_send('sub-step-report', {...})
if not sync_ok:
    # 降级：放入队列
    cc.storage.enqueue_report(...)
```

**问题**：
- `process_sub_steps` 写入成功
- 同步到 `steel_belt` 失败
- 数据不一致：手机端有记录，桌面端没有

### 1.2 专家共识方案

根据 `专家团队共识报告_v1.md`：
> **分两步走**：短期（1天）加 service token + 告警；中期（3天）加 outbox

---

## 二、短期方案（1天）

### 2.1 加强同步失败告警

**目标**：同步失败时立即告警，不静默丢弃

**修改位置**：`mobile_api_ai/app.py` 第365-375行

```python
# 当前代码
sync_ok = sync_send('sub-step-report', {...})
if not sync_ok:
    cc.storage.enqueue_report(...)  # 静默入队

# 改进后
sync_ok = sync_send('sub-step-report', {...})
if not sync_ok:
    logger.error(f'[P0-I] 同步报工失败: order={order_no}, step={step_name}')
    try:
        cc.storage.enqueue_report(...)
    except Exception as e:
        # P0-I: 同步失败且队列也失败，立即告警
        _send_sync_alert(order_no, step_name, str(e))
```

### 2.2 添加同步健康检查

**位置**：`scripts/check_sync_health.py`

```python
def check_sync_pending():
    """检查待同步队列"""
    # 检查 enqueue_report 的数据量
    cursor.execute("SELECT COUNT(*) FROM sync_queue WHERE status='pending'")
    pending = cursor.fetchone()
    if pending > 100:
        _send_alert(f'同步队列积压: {pending} 条待处理')
```

---

## 三、中期方案（3天）- Outbox模式

### 3.1 Outbox模式原理

```
┌─────────────────────────────────────────────────────────┐
│                    事务内原子写入                          │
│  ┌──────────────────┐    ┌──────────────────┐          │
│  │ process_sub_steps │    │   outbox_events   │          │
│  │   (主业务表)      │    │   (待同步事件)    │          │
│  └──────────────────┘    └──────────────────┘          │
│           ↓                       ↓                      │
│      COMMIT ─────────────────────────────────────────→  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │           Outbox Worker (异步消费)                  │  │
│  │  1. 读取 outbox_events                           │  │
│  │  2. 同步到 steel_belt                             │  │
│  │  3. 删除 outbox_events 或标记 sent                │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 3.2 数据库变更

```sql
-- 新建 outbox_events 表
CREATE TABLE outbox_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,      -- 'sub_step_report'
    payload JSON NOT NULL,                 -- 事件数据
    source_db VARCHAR(50) DEFAULT 'wechat_container',
    target_db VARCHAR(50) DEFAULT 'steel_belt',
    status ENUM('pending', 'sent', 'failed') DEFAULT 'pending',
    retry_count INT DEFAULT 0,
    error_msg TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sent_at DATETIME,
    INDEX idx_status_created (status, created_at)
);
```

### 3.3 代码改造

**1. 修改 save_process_sub_step_with_pkg_update**

```python
def save_process_sub_step_with_pkg_update(self, data, pkg_order, pkg_process, qty_delta):
    with self._pool.connection() as conn:
        try:
            with conn.cursor(DictCursor) as cur:
                # 1. 写入主业务表
                self._upsert_process_sub_step(cur, data)

                # 2. 写入 outbox_events（同一事务！）
                outbox_payload = {
                    'event_type': 'sub_step_report',
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                }
                cur.execute("""
                    INSERT INTO outbox_events (event_type, payload, source_db, target_db)
                    VALUES (%s, %s, 'wechat_container', 'steel_belt')
                """, ('sub_step_report', json.dumps(outbox_payload)))

                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            raise
```

**2. 新增 Outbox Worker**

```python
# outbox_worker.py
class OutboxWorker:
    def __init__(self):
        self.pool = ConnectionPool(...)

    def process_pending(self):
        with self.pool.connection() as conn:
            cur = conn.cursor(DictCursor)
            cur.execute("""
                SELECT * FROM outbox_events
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT 10
            """)
            for row in cur.fetchall():
                try:
                    self._sync_to_target(row)
                    cur.execute("""
                        UPDATE outbox_events
                        SET status = 'sent', sent_at = NOW()
                        WHERE id = %s
                    """, (row['id'],))
                    conn.commit()
                except Exception as e:
                    self._handle_retry(row, str(e))

    def _sync_to_target(self, row):
        """同步到目标数据库"""
        payload = json.loads(row['payload'])
        if row['event_type'] == 'sub_step_report':
            self._sync_sub_step_report(payload['data'])
```

---

## 四、实施方案

### 4.1 短期（今日完成）

| 任务 | 工作量 | 修改文件 |
|------|--------|----------|
| 同步失败告警 | 1小时 | `mobile_api_ai/app.py` |
| 健康检查脚本 | 2小时 | `scripts/check_sync_health.py` |

### 4.2 中期（本周内）

| 任务 | 工作量 | 修改文件 |
|------|--------|----------|
| 创建 outbox_events 表 | 1小时 | 数据库迁移脚本 |
| 修改 save_process_sub_step_with_pkg_update | 4小时 | `mysql_storage.py` |
| 实现 Outbox Worker | 4小时 | `outbox_worker.py` |
| 测试验证 | 4小时 | 测试脚本 |

---

## 五、验收标准

### 5.1 短期验收

- [ ] 同步失败时日志记录错误级别
- [ ] 连续3次同步失败发送企微告警
- [ ] 健康检查脚本可检测队列积压

### 5.2 中期验收

- [ ] Outbox事件与主业务写入在同一事务内
- [ ] Worker可处理 pending 事件
- [ ] 失败事件重试3次后进入 dead_letter
- [ ] 数据一致性验证通过

---

## 六、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 事务回滚导致 outbox 也回滚 | 高 | 单元测试覆盖 |
| Worker处理顺序乱序 | 中 | 按 created_at 顺序处理 |
| 历史数据迁移 | 低 | 迁移脚本+数据验证 |

---

## 七、决策点

| 决策项 | 选项 |
|--------|------|
| 是否立即实施短期方案 | A.是 B.否，直接上outbox |
| Outbox Worker运行位置 | A.独立进程 B.集成到app.py |
| 历史数据处理 | A.不迁移 B.一次性迁移 |
