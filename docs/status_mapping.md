# data_packages 状态枚举对照表

## 一、data_packages 状态值（来源）

### 1.1 调度任务（data_type='schedule'）

| status 值 | 含义 |
|-----------|------|
| pending | 待处理 |
| in_progress | 进行中 |
| completed | 已完成 |
| withdrawn | 已撤回 |
| cancelled | 已取消 |

### 1.2 物料（type='material'）

| status 值 | 含义 |
|-----------|------|
| material_requested | 物料已申请 |
| material_confirmed | 物料已确认 |
| material_arrived | 物料已到货 |
| material_delivered | 物料已出库 |
| material_shortage | 缺料 |

### 1.3 外协（type='outsource'）

| status 值 | 含义 |
|-----------|------|
| outsource_requested | 外协已申请 |
| outsource_confirmed | 外协已确认 |
| outsource_sent | 已外发 |
| outsource_returned | 已返回 |
| outsource_qc | 质检中 |

---

## 二、目标表状态值（检查）

### 2.1 schedule_records

```sql
SELECT DISTINCT status FROM schedule_records;
```

**预期状态**：pending / in_progress / completed / withdrawn

### 2.2 material_records

```sql
SELECT DISTINCT status FROM material_records;
```

**预期状态**：material_requested / material_confirmed / material_arrived / material_delivered / 缺料

### 2.3 outsource_records

```sql
SELECT DISTINCT status FROM outsource_records;
```

**预期状态**：outsource_requested / outsource_confirmed / outsource_sent / outsource_returned / outsource_qc

---

## 三、状态枚举对照

### 3.1 调度任务

| data_packages | schedule_records | 兼容 |
|---------------|------------------|:----:|
| pending | pending | ✅ |
| in_progress | in_progress | ✅ |
| completed | completed | ✅ |
| withdrawn | withdrawn | ✅ |
| cancelled | (无) | ⚠️ 需处理 |

### 3.2 物料

| data_packages | material_records | 兼容 |
|---------------|------------------|:----:|
| material_requested | 缺料 | ⚠️ 需映射 |
| material_confirmed | material_confirmed | ✅ |
| material_arrived | material_arrived | ✅ |
| material_delivered | material_delivered | ✅ |

### 3.3 外协

| data_packages | outsource_records | 兼容 |
|---------------|-------------------|:----:|
| outsource_requested | outsource_requested | ✅ |
| outsource_confirmed | outsource_confirmed | ✅ |
| outsource_sent | outsource_sent | ✅ |
| outsource_returned | outsource_returned | ✅ |

---

## 四、状态映射函数

```python
def map_schedule_status(old_status):
    """调度状态映射"""
    return old_status  # 保持不变

def map_material_status(old_status):
    """物料状态映射"""
    MAP = {
        '缺料': 'material_requested',  # 兼容旧数据
        'material_requested': 'material_requested',
        'material_confirmed': 'material_confirmed',
        'material_arrived': 'material_arrived',
        'material_delivered': 'material_delivered',
    }
    return MAP.get(old_status, old_status)

def map_outsource_status(old_status):
    """外协状态映射"""
    return old_status  # 保持不变
```

---

## 五、验证 SQL

```sql
-- 检查状态兼容性
SELECT 
    (SELECT COUNT(DISTINCT status) FROM schedule_records) as schedule_count,
    (SELECT COUNT(DISTINCT status) FROM material_records) as material_count,
    (SELECT COUNT(DISTINCT status) FROM outsource_records) as outsource_count;

-- 检查状态值分布
SELECT 'schedule' as type, status, COUNT(*) as cnt FROM schedule_records GROUP BY status
UNION ALL
SELECT 'material', status, COUNT(*) FROM material_records GROUP BY status
UNION ALL
SELECT 'outsource', status, COUNT(*) FROM outsource_records GROUP BY status;
```
