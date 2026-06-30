# 操作日志设计

## 一、现有日志表

项目已有 `data_regression_history` 表记录修改历史：

```sql
CREATE TABLE data_regression_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    data_type VARCHAR(50),           -- schedule/material/outsource
    record_id VARCHAR(64),            -- 记录ID
    order_no VARCHAR(64),             -- 订单号
    step_name VARCHAR(100),          -- 工序名
    field_before TEXT,                -- 修改前值
    field_after TEXT,                -- 修改后值
    action VARCHAR(20),              -- update/withdraw/revert
    operator VARCHAR(64),            -- 操作人
    reason VARCHAR(255),             -- 修改原因
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_data_type (data_type),
    INDEX idx_record_id (record_id),
    INDEX idx_order_no (order_no)
);
```

## 二、日志记录时机

### 2.1 必须记录的操作

| 操作 | 表 | 字段 | 时机 |
|------|-----|------|------|
| 调度修正 | schedule_records | title/status/priority | UPDATE 后 |
| 调度撤回 | schedule_records | status | UPDATE 后 |
| 物料确认 | material_records | status/content | UPDATE 后 |
| 物料到货 | material_records | status | UPDATE 后 |
| 物料撤回 | material_records | status | UPDATE 后 |
| 外协修正 | outsource_records | title/status/priority | UPDATE 后 |
| 外协撤回 | outsource_records | status | UPDATE 后 |

### 2.2 日志记录代码模板

```python
def _log_regression(data_type, record_id, order_no, step_name, 
                    field_before, field_after, action, operator, reason):
    """记录修改历史"""
    import pymysql
    from core.config import CONTAINER_MYSQL_CFG
    
    conn = pymysql.connect(**CONTAINER_MYSQL_CFG)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO data_regression_history 
        (data_type, record_id, order_no, step_name, field_before, field_after, 
         action, operator, reason, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """, (data_type, record_id, order_no, step_name, 
          json.dumps(field_before, ensure_ascii=False),
          json.dumps(field_after, ensure_ascii=False),
          action, operator, reason))
    conn.commit()
    conn.close()
```

## 三、日志查询 API

### 3.1 查询单条记录的历史

```
GET /api/<type>/history_full?record_id=<id>
```

### 3.2 查询订单的所有修改历史

```
GET /api/regression/history?order_no=<order_no>&type=<type>
```

## 四、日志保留策略

| 类型 | 保留时间 | 说明 |
|------|----------|------|
| 调度修改 | 90 天 | 订单周期内 |
| 物料修改 | 180 天 | 采购周期较长 |
| 外协修改 | 180 天 | 外协周期较长 |

### 清理脚本

```sql
-- 90天后清理
DELETE FROM data_regression_history 
WHERE data_type = 'schedule' 
  AND created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

## 五、告警规则

| 规则 | 条件 | 动作 |
|------|------|------|
| 频繁修改 | 同一记录 1 小时内修改 > 3 次 | 微信通知 |
| 大幅变更 | quantity 变更 > 50% | 微信通知 |
| 撤回异常 | 撤回后 5 分钟内重新创建 | 微信通知 |

### 告警代码

```python
def _check_alert(data_type, record_id, action, field_after):
    """检查是否需要告警"""
    if action == 'withdraw':
        # 检查是否频繁撤回
        cur.execute("""
            SELECT COUNT(*) FROM data_regression_history
            WHERE record_id = %s AND action = 'withdraw'
              AND created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
        """, (record_id,))
        count = cur.fetchone()[0]
        if count >= 3:
            send_wechat_alert(f"频繁撤回: {record_id}")
```
