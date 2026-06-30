# FIX-05: DAO 层绕过 — 2 处重复 SQL 提取

## 1. 问题定位

| 项目 | 内容 |
|------|------|
| **文件** | `views/quality_view.py` |
| **出现位置** | **位置 A**: `_open_task_compile()` 第 136-149 行 |
| | **位置 B**: `add_record()` 第 447-460 行 |
| **代码量** | 每处 ~14 行，共 ~28 行 |
| **严重度** | 🔴 高 |

## 2. 问题描述

两处代码执行了**完全相同的 SQL 查询**：

```sql
SELECT order_id, GROUP_CONCAT(DISTINCT order_no SEPARATOR ', ') as wn
FROM production_orders
WHERE order_id IN ({placeholders})
GROUP BY order_id
```

### 位置 A（L136-149）：
```python
conn = get_connection()
try:
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT order_id, GROUP_CONCAT(DISTINCT order_no SEPARATOR ', ') as wn FROM production_orders WHERE order_id IN ({placeholders}) GROUP BY order_id",
        order_ids
    )
    for row in cursor.fetchall():
        work_no_map[row["order_id"]] = row["wn"]
    cursor.close()
finally:
    conn.close()
```

### 位置 B（L447-460）：
```python
conn = get_connection()
try:
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT order_id, GROUP_CONCAT(DISTINCT order_no SEPARATOR ', ') as wn FROM production_orders WHERE order_id IN ({placeholders}) GROUP BY order_id",
        order_ids
    )
    for row in cursor.fetchall():
        work_no_map[row["order_id"]] = row["wn"]
    cursor.close()
finally:
    conn.close()
```

**根本问题**：
1. **DAO 层被绕过**：视图层直接调用 `get_connection()` 操作数据库，违反分层架构
2. **代码重复**：完全相同的 SQL + 连接管理代码出现 2 次
3. **SQL 注入风险**：虽然当前使用参数化查询，但 `f"{placeholders}"` 的字符串拼接模式在复杂度增加时易出错
4. **无上下文管理器**：使用 `conn.close()` 而非 `get_connection_context()`，不符合现有规范（`database.py` 已提供上下文管理器）

## 3. 修复目标

在 `QualityDAO` 中新增 `get_work_no_map(order_ids)` 静态方法，统一封装该查询逻辑，消除 2 处重复代码。

## 4. 具体实现步骤

### Step 1: 在 `models/quality.py` 的 `QualityDAO` 中新增方法

```python
@staticmethod
def get_work_no_map(order_ids: list) -> dict:
    """
    获取订单 ID → 工单号映射。
    
    Args:
        order_ids: 订单 ID 列表
    
    Returns:
        dict: {order_id: "工单号1, 工单号2, ..."}
    """
    if not order_ids:
        return {}
    
    placeholders = ",".join(["%s"] * len(order_ids))
    sql = f"""
        SELECT order_id, GROUP_CONCAT(DISTINCT order_no SEPARATOR ', ') as wn
        FROM production_orders
        WHERE order_id IN ({placeholders})
        GROUP BY order_id
    """
    work_no_map = {}
    
    with get_connection_context() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, order_ids)
            for row in cursor.fetchall():
                work_no_map[row["order_id"]] = row["wn"]
    
    return work_no_map
```

### Step 2: 替换位置 A（`_open_task_compile()` L136-149）

替换为：
```python
work_no_map = QualityDAO.get_work_no_map(order_ids)
```

### Step 3: 替换位置 B（`add_record()` L447-460）

替换为：
```python
work_no_map = QualityDAO.get_work_no_map(order_ids)
```

### Step 4: 清理视图层的 `get_connection` 导入

检查是否在 `quality_view.py` 中还有其他地方使用 `get_connection()`。如果仅这 2 处使用，可删除 L12 的 `from models.database import get_connection` 导入。

## 5. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `models/quality.py` | ✅ 修改 | 在 `QualityDAO` 类中新增 `get_work_no_map()` |
| `views/quality_view.py` | ✅ 修改 | L136-149 → 1 行调用；L447-460 → 1 行调用 |

## 6. 依赖关系

| 前置依赖 | 说明 |
|----------|------|
| 无 | 可独立进行，不依赖其他 FIX |

## 7. 风险与注意事项

- **`get_connection_context()` 的使用**：当前 `QualityDAO` 中全部使用 `conn = get_connection()` / `conn.close()` 模式，此方法使用 `with get_connection_context()` 后成为第一个使用上下文管理器的方法，需确认上下文管理器工作正常
- **返回格式一致性**：新方法返回 `{order_id: "工单号"}` 格式，与原 2 处的 `work_no_map` 完全一致
- **空列表处理**：`order_ids` 可能为空，需处理边界情况
- **`from models.database import get_connection_context`**：需在 `quality.py` 中添加导入

## 8. 验收标准

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | 新增 `get_work_no_map()` 返回正确的 order_id → work_no 映射 | 单元测试 |
| 2 | 空列表传入返回空 dict | 单元测试 |
| 3 | 任务编制对话框的工单下拉菜单显示正常 | 手工测试 |
| 4 | 新增质检记录的工单下拉菜单显示正常 | 手工测试 |
| 5 | 视图层不再直接调用 `get_connection()` | grep 验证 |
| 6 | `get_connection_context()` 上下文管理器正确释放连接 | 检查 |

## 9. 预估工作量

- 修改 models/quality.py：新增 ~18 行
- 修改 views/quality_view.py：删除 ~28 行，新增 ~2 行
- **净减少代码量：~26 行**
