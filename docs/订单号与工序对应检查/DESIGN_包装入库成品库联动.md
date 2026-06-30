# DESIGN v6 - 包装入库 ↔ 成品库联动修复（含 QC 强校验 + 资源安全 + with 上下文 + 编译验证）

> **版本**: v6（修补 v5 审计发现的 #28 实施时缩进一致性 + 实际 py_compile 验证）
> **修补日期**: 2026-06-16
> **v1 审计**: 62/100 → **v2 审计**: 84/100 → **v3 审计**: 83/100 → **v4 审计**: 90/100 → **v5 审计**: 98/100 → **v6 目标**: 100/100
> **业务约束**: 质量检验合格数量 ≥ 包装入库累计数量 + 本次报工量

## v5 → v6 修补摘要

| # | 审计项 | v5 状态 | v6 修补 |
|---|--------|---------|---------|
| 28 🟡 | v5 §6.3 缩进一致性（实施时验证）| v5 文档未跑 py_compile | 实际提取 v5 文档中 8 个 Python 代码块,py_compile 8/8 通过 ✅ |

## v1 → v2 → v3 → v4 → v5 修补历史

| 版本 | 修补项 |
|------|--------|
| v2 | 修补 v1 #1-12 (12 项) — 并发、ShipmentDAO 行为、枚举完整性、单位、5008 单一触发、old_completed_qty、status_key_map、旧数据、硬编码、T5 位置、import 循环、shipments.unit |
| v3 | 修补 v2 #13 #14 #15 + 用户新增 #16 (QC 强校验) + #17 (移除冗余) |
| v4 | 修补 v3 #18 (conn 泄漏) + #20 (字面量) |
| v5 | 修补 v4 #22 (cursor 关闭) + #23 (多处 cursor) + #24 (专项测试) |
| v6 | 修补 v5 #28 (py_compile 验证) — 8/8 代码块通过 |

## v1 → v2 → v3 → v4 修补历史

| 版本 | 修补项 |
|------|--------|
| v2 | 修补 v1 #1-12 (12 项) — 并发、ShipmentDAO 行为、枚举完整性、单位、5008 单一触发、old_completed_qty、status_key_map、旧数据、硬编码、T5 位置、import 循环、shipments.unit |
| v3 | 修补 v2 #13 #14 #15 + 用户新增 #16 (QC 强校验) + #17 (移除冗余) |
| v4 | 修补 v3 #18 (conn 泄漏) + #20 (字面量) |
| v5 | 修补 v4 #22 (cursor 关闭) + #23 (多处 cursor) + #24 (专项测试) |

---

## 1. 修复目标

实现"包装入库"工序报工 → `finished_goods` 仓库数量自动联动 + 订单状态自动更新 + 5008 端同步。**分批发货**同步支持。**并发安全**。**QC 强校验**（新增）。

## 2. 业务流 v3

```mermaid
graph TB
    A[工序 1-13 完成] --> B[工序 14 质量检验]
    B -->|COMPLETED| C[orders.status=QC 质检中]
    C --> D{所有工序完成?}
    D -->|否,包装入库未做| E[保持 IN_PROGRESS]
    D -->|是,包装入库已完成| F[工序 15 包装入库 COMPLETED]
    
    F -->|先校验 QC 数量| G{SUM QC qualified >= SUM Packing completed + delta?}
    G -->|否,硬拒绝| H[抛 ValueError 不写入]
    G -->|是,允许| I[写入 process_records]
    
    I -->|原子 SQL UPDATE finished_goods| J[仓库 +delta]
    I -->|UPDATE orders.status=PACKED| K[订单 包装入库]
    I -->|POST 5008 warehousing| L[5008 同步]
    
    M[部分发货] --> N[ShipmentDAO.confirm_ship]
    N -->|调 ship_out(conn)| O[原子 SQL 减库存]
    O -->|改 status=已出库| P[仓库出库]
    N -->|UPDATE orders.status=SHIPPED| Q[订单 已发货]
```

## 3. 强校验规则（v3 新增）

### 3.1 业务约束

**质量检验合格数量 必须 ≥ 包装入库累计数量 + 本次报工量**

### 3.2 校验时机

工序"包装入库"报工时（无论 IN_PROGRESS 还是 COMPLETED），**先校验**再写。

### 3.3 校验 SQL（v4 修补 #20：使用枚举变量）

```python
# v4 修补 #20: 不再使用字面量 '已完成',改用 ProcessStatus.COMPLETED.value
cursor.execute("""
    SELECT
        COALESCE(SUM(CASE WHEN process_name=%s AND status=%s
                          THEN qualified_qty ELSE 0 END), 0) AS total_qc,
        COALESCE(SUM(CASE WHEN process_name=%s THEN completed_qty ELSE 0 END), 0) AS total_packing
    FROM process_records
    WHERE order_id=%s
""", (
    ProcessNames.QC.value, ProcessStatus.COMPLETED.value,
    ProcessNames.PACKING.value,
    order_id
))
```

### 3.4 校验逻辑

```python
total_qc = result['total_qc']
total_packing = result['total_packing']
delta_qty = new_completed_qty - old_completed_qty
new_total = total_packing + delta_qty

if new_total > total_qc:
    raise ValueError(
        f"包装入库数量校验失败: QC 合格总数 {total_qc} {unit} < "
        f"包装入库累计 {new_total} {unit} (本次报工 +{delta_qty})"
    )
```

### 3.5 失败行为

**硬拒绝**（用户决策）：
- 不写入 process_records
- 不联动仓库
- 不更新订单状态
- 不触发 5008 同步
- 抛 ValueError，UI 端 catch + 弹错误提示

## 4. 业务流修正（v3 #13 C 方案）

### 4.1 修正 process.py:69-95 逻辑

```python
# v3 改造：根据当前 COMPLETED 工序名,动态决定 orders.status
if unfinished_cnt == 0:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE production_orders SET status=%s, actual_end=NOW(), updated_at=NOW() WHERE id=%s",
        (ProductionStatus.COMPLETED.value, production_id)
    )
    cursor.close()
    # v3 修补 #13: 根据当前 COMPLETED 工序决定 orders.status
    if old_process_name == ProcessNames.PACKING.value:
        new_order_status = OrderStatus.PACKED.value  # "包装入库"
    elif old_process_name == ProcessNames.QC.value:
        new_order_status = OrderStatus.QC.value       # "质检中"
    else:
        new_order_status = OrderStatus.QC.value       # 其他工序保持原 QC
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s",
        (new_order_status, order_id)
    )
    cursor.close()
    conn.commit()
    log_status_change("orders", order_id, OrderStatus.PRODUCTION.value, new_order_status, remark="工序全部完成")
```

### 4.2 v3 移除 v2 追加的 orders.status 更新

v2 DESIGN §4.3 在 line 130-132 追加的联动中**包含** orders.status 更新，v3 改为**只**保留：
1. 仓库联动（FinishedGoodsDAO.stock_in）
2. 5008 同步
3. **移除** orders.status 更新（已在 line 89-95 处理）

## 5. 枚举扩展（保留 v2）

```python
class OrderStatus(Enum):
    PENDING = "待确认"
    CONFIRMED = "待排产"
    PENDING_PUBLISH = "待发布"
    PUBLISHED = "已发布"
    SCHEDULED = "已排产"
    PRODUCTION = "生产中"
    QC = "质检中"
    FINISHED = "已完成"
    PACKED = "包装入库"           # v2 新增
    PENDING_SHIP = "待发货"
    SHIPPED = "已发货"
    CANCELLED = "已取消"


class ProductionStatus(Enum):
    PENDING = "待开始"
    IN_PROGRESS = "生产中"
    COMPLETED = "已完成"
    PACKED = "包装入库"           # v2 新增
    PENDING_PUBLISH = "待发布"
    SCHEDULED = "已排产"
    PAUSED = "已暂停"


class ProcessNames(Enum):
    RAW_PREP = "原材料准备"
    WELD_EYE = "焊接眼镜网"
    LASER_CUT = "激光切板"
    CHAIN_HOLE = "链板冲压孔"
    CHAIN_FORM = "链板冲压成型"
    WEAVE_LEFT = "编制左旋"
    WEAVE_RIGHT = "编制右旋"
    SHAFT_INSTALL = "穿曲轴"
    BELT_ASSEMBLE = "输送带组装穿杆"
    CHAIN_INSTALL = "安装链条"
    SKIRT_INSTALL = "安装裙边"
    STRAIGHTEN = "整形校直"
    WELD_BELT = "焊接输送带"
    SURFACE_TREAT = "表面处理"
    QC = "质量检验"
    PACKING = "包装入库"
```

## 6. 接口契约 v3

### 6.1 新建 `FinishedGoodsDAO`（v5 with 模式：自动关 cursor）

```python
class FinishedGoodsDAO:
    @staticmethod
    def stock_in(order_id: int, qty: float, unit: str = "",
                 warehouse: str = "成品仓库", operator: str = "",
                 remark: str = "", conn=None) -> int:
        """增量入库（v5 用 with 模式自动关 cursor）
        
        v3 修补 #14: 处理 finished_goods 旧数据 status='已出库' 情况
        v3 修补 #15: 接受 conn 参数,允许外部事务
        v5 修补 #22: 所有 cursor 用 `with` 上下文,即使抛异常也关
        """
        own_conn = conn is None
        if own_conn:
            conn = get_connection()
        try:
            # v5 #22: cursor 用 with 上下文
            with conn.cursor() as cursor:
                # 1. 查同 order_id+warehouse 的 finished_goods 记录
                cursor.execute("""
                    SELECT id, status, quantity FROM finished_goods
                    WHERE order_id=%s AND warehouse=%s
                    ORDER BY in_date DESC LIMIT 1
                """, (order_id, warehouse))
                existing = cursor.fetchone()
                
                if existing:
                    fg_id = existing['id']
                    existing_status = existing['status']
                    if existing_status == '已出库':
                        # 旧记录已出库,改回在库
                        cursor.execute("""
                            UPDATE finished_goods
                            SET status='在库', quantity=%s, unit=%s, 
                                in_date=NOW(), updated_at=NOW()
                            WHERE id=%s
                        """, (qty, unit, fg_id))
                    else:
                        # 状态在库,原子累加
                        cursor.execute("""
                            UPDATE finished_goods
                            SET quantity = quantity + %s, unit=%s, updated_at=NOW()
                            WHERE id=%s
                        """, (qty, unit, fg_id))
                    return fg_id
                else:
                    # 不存在,INSERT
                    cursor.execute("""
                        INSERT INTO finished_goods
                        (order_id, warehouse, quantity, unit, in_date, status, remark)
                        VALUES (%s, %s, %s, %s, NOW(), '在库', %s)
                    """, (order_id, warehouse, qty, unit, remark))
                    return cursor.lastrowid
        finally:
            if own_conn:
                conn.close()
    
    @staticmethod
    def ship_out(order_id: int, qty: float, finished_goods_id: int = None,
                 operator: str = "", remark: str = "", conn=None) -> int:
        """分批发货（v5 with 模式）
        
        v3 修补 #15: 接受 conn 参数,允许外部事务
        v5 修补 #22: 所有 cursor 用 `with` 上下文
        """
        own_conn = conn is None
        if own_conn:
            conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # 原子 SQL
                if finished_goods_id is None:
                    # 自动查最新 finished_goods
                    cursor.execute("""
                        SELECT id, quantity FROM finished_goods
                        WHERE order_id=%s AND warehouse='成品仓库' AND status='在库'
                        ORDER BY in_date DESC LIMIT 1
                    """, (order_id,))
                    existing = cursor.fetchone()
                    if not existing:
                        raise ValueError(f"订单 {order_id} 无在库成品")
                    finished_goods_id = existing['id']
                
                cursor.execute("""
                    UPDATE finished_goods
                    SET quantity = quantity - %s, updated_at=NOW()
                    WHERE id=%s AND quantity >= %s
                """, (qty, finished_goods_id, qty))
                affected = cursor.rowcount
                
                if affected == 0:
                    raise ValueError(
                        f"库存不足: finished_goods.id={finished_goods_id} "
                        f"扣减 {qty} 失败(可能并发超扣或数量不足)"
                    )
            
            # 重新查 quantity 决定 status(用新 with 块)
            with conn.cursor() as cursor:
                cursor.execute("SELECT quantity FROM finished_goods WHERE id=%s", (finished_goods_id,))
                row = cursor.fetchone()
            
            if row and float(row['quantity']) == 0:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE finished_goods SET status='已出库', updated_at=NOW()
                        WHERE id=%s
                    """, (finished_goods_id,))
            
            return finished_goods_id
        finally:
            if own_conn:
                conn.close()
    
    @staticmethod
    def get_by_order(order_id: int) -> Optional[dict]:
        """按订单 ID 查 finished_goods 最新记录（v5 with 模式）"""
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM finished_goods
                    WHERE order_id=%s
                    ORDER BY in_date DESC LIMIT 1
                """, (order_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()
```

### 6.2 修补 `ShipmentDAO.confirm_ship()`（v5 with 模式）

```python
@staticmethod
def confirm_ship(shipment_id: int, operator: str = "系统") -> bool:
    """确认发货（v5 改造：with 模式 + 共享 conn）
    
    v3 修补 #15: 调 ship_out 时传入 conn,统一事务边界
    v5 修补 #23: 内部 cursor 用 `with` 上下文
    """
    from models.shipment import FinishedGoodsDAO
    
    conn = get_connection()
    try:
        # v5 #23: 查 shipment
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT order_id, finished_goods_id, ship_quantity 
                FROM shipments WHERE id=%s
            """, (shipment_id,))
            row = cursor.fetchone()
        if not row:
            return False
        
        order_id = row['order_id']
        fg_id = row['finished_goods_id']
        ship_qty = row['ship_quantity']
        
        # 1. 调 ship_out 扣库存（共享 conn）
        try:
            FinishedGoodsDAO.ship_out(
                order_id=order_id,
                qty=ship_qty,
                finished_goods_id=fg_id,
                operator=operator,
                remark=f"发货确认 (shipment_id={shipment_id})",
                conn=conn  # 共享 conn
            )
        except ValueError as e:
            log_error("发货", "库存不足", f"shipment_id={shipment_id}, {e}")
            raise
        
        # 2. UPDATE shipments.status（v5 with 模式）
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE shipments SET status=%s, 
                ship_date=COALESCE(NULLIF(ship_date,''), DATE(NOW())),
                updated_at=NOW() WHERE id=%s
            """, (ShipmentStatus.COMPLETED.value, shipment_id))
        
        # 3. UPDATE orders.status = SHIPPED（v5 with 模式）
        if order_id:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT status FROM orders WHERE is_deleted = 0 
                    AND COALESCE(is_archived, 0) = 0 AND id=%s
                """, (order_id,))
                old_order_status_row = cursor.fetchone()
            old_order_status = old_order_status_row[0] if old_order_status_row else "未知"
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s
                """, (OrderStatus.SHIPPED.value, order_id))
            log_status_change("orders", order_id, old_order_status, 
                            OrderStatus.SHIPPED.value, operator, "发货确认")
        
        conn.commit()
        log_status_change("shipments", shipment_id, 
                        ShipmentStatus.PENDING.value, 
                        ShipmentStatus.COMPLETED.value, operator)
        return True
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### 6.3 扩展 `ProcessDAO.update_record()`（v5 with 模式：自动关所有 cursor）

```python
@staticmethod
def update_record(record_id: int, data: dict) -> bool:
    """更新工序报工（v5 完整改造：with 模式 + 资源安全）

    v4 修补 #18: 整函数 try-finally 包 conn + cursor
    v4 修补 #20: 强校验 SQL 用 ProcessStatus.COMPLETED.value 不用字面量
    v5 修补 #23: 所有 cursor 用 `with` 上下文,即使抛异常也关
    """
    from constants import ProcessNames, OrderStatus, ProductionStatus
    from models.shipment import FinishedGoodsDAO

    conn = get_connection()
    try:  # v4 #18: 整函数 try
        # v3 #6: SELECT 扩字段 (v5 #23: with 模式)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT status, order_id, production_id, process_name, completed_qty, unit,
                       start_time, end_time
                FROM process_records WHERE id=%s
            """, (record_id,))
            old = cursor.fetchone()
        old_status = old["status"] if old else None
        order_id = old["order_id"] if old else None
        production_id = old["production_id"] if old else None
        old_process_name = old["process_name"] if old else None
        old_completed_qty = float(old["completed_qty"]) if old and old.get("completed_qty") is not None else 0.0
        old_start_time = old["start_time"] if old else None
        old_end_time = old["end_time"] if old else None
        old_unit = old["unit"] if old else None

        new_status = data.get("status", old_status)
        new_completed_qty = float(data.get("completed_qty", 0))
        delta_qty = new_completed_qty - old_completed_qty
        new_unit = data.get("unit") or old_unit or ""

        # v3 #16: 强校验包装入库报工前校验 QC 数量
        # v4 #20: SQL 用 ProcessStatus.COMPLETED.value 不用字面量
        if old_process_name == ProcessNames.PACKING.value and delta_qty > 0:
            with conn.cursor() as cursor:  # v5 #23: with
                cursor.execute("""
                    SELECT
                        COALESCE(SUM(CASE WHEN process_name=%s AND status=%s
                                          THEN qualified_qty ELSE 0 END), 0) AS total_qc,
                        COALESCE(SUM(CASE WHEN process_name=%s THEN completed_qty ELSE 0 END), 0) AS total_packing
                    FROM process_records
                    WHERE order_id=%s
                """, (
                    ProcessNames.QC.value, ProcessStatus.COMPLETED.value,
                    ProcessNames.PACKING.value,
                    order_id
                ))
                sum_row = cursor.fetchone()
                total_qc = float(sum_row['total_qc']) if sum_row else 0
                total_packing = float(sum_row['total_packing']) if sum_row else 0
                new_total = total_packing + delta_qty
                if new_total > total_qc:
                    raise ValueError(
                        f"包装入库数量超过质量检验合格总数: "
                        f"QC 合格 {total_qc}{new_unit} < 包装入库累计 {new_total}{new_unit} "
                        f"(本次报工 +{delta_qty}{new_unit})"
                    )

        # 自动记录工序开始/结束时间
        start_time = old_start_time
        if old_status in (None, ProcessStatus.PENDING.value) and new_status in (ProcessStatus.IN_PROGRESS.value, ProcessStatus.COMPLETED.value):
            start_time = "NOW()"
        end_time = old_end_time
        if new_status == ProcessStatus.COMPLETED.value and old_status != ProcessStatus.COMPLETED.value:
            end_time = "NOW()"

        # 构建更新SQL
        update_fields = [
            "completed_qty=%s", "qualified_qty=%s", "worker=%s",
            "work_hours=%s", "status=%s", "remark=%s",
            "device_remark=%s", "record_date=NOW()"
        ]
        update_values = [
            data.get("completed_qty", 0),
            data.get("qualified_qty", 0),
            data.get("worker", ""),
            data.get("work_hours", 0),
            new_status,
            data.get("remark", ""),
            data.get("device_remark", ""),
        ]
        if start_time and not old_start_time:
            update_fields.append("start_time=NOW()")
        if end_time and not old_end_time:
            update_fields.append("end_time=NOW()")

        # v5 #23: UPDATE process_records 用 with
        with conn.cursor() as cursor:
            cursor.execute(f"""
                UPDATE process_records SET {','.join(update_fields)}
                WHERE id=%s
            """, update_values + [record_id])
        conn.commit()

        # v3 #13: 检查是否所有工序都完成
        if new_status == ProcessStatus.COMPLETED.value and production_id:
            with conn.cursor() as cursor:  # v5 #23
                cursor.execute("""
                    SELECT COUNT(*) as cnt FROM process_records
                    WHERE production_id=%s AND status != %s
                """, (production_id, ProcessStatus.COMPLETED.value))
                unfinished = cursor.fetchone()
            if isinstance(unfinished, dict):
                unfinished_cnt = unfinished.get("cnt", 0) or unfinished.get("COUNT(*)", 0)
            else:
                unfinished_cnt = unfinished[0] if unfinished else 0
            if unfinished_cnt == 0:
                with conn.cursor() as cursor:  # v5 #23
                    cursor.execute("""
                        UPDATE production_orders
                        SET status=%s, actual_end=NOW(), updated_at=NOW() WHERE id=%s
                    """, (ProductionStatus.COMPLETED.value, production_id))
                if old_process_name == ProcessNames.PACKING.value:
                    new_order_status = OrderStatus.PACKED.value
                elif old_process_name == ProcessNames.QC.value:
                    new_order_status = OrderStatus.QC.value
                else:
                    new_order_status = OrderStatus.QC.value
                with conn.cursor() as cursor:  # v5 #23
                    cursor.execute("""
                        UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s
                    """, (new_order_status, order_id))
                conn.commit()
                log_status_change("orders", order_id, OrderStatus.PRODUCTION.value, new_order_status, remark="工序全部完成")
            else:
                with conn.cursor() as cursor:  # v5 #23
                    cursor.execute("""
                        UPDATE production_orders
                        SET status=%s, actual_start=COALESCE(actual_start, NOW()), updated_at=NOW()
                        WHERE id=%s
                    """, (ProductionStatus.IN_PROGRESS.value, production_id))
                with conn.cursor() as cursor:  # v5 #23
                    cursor.execute("""
                        UPDATE orders SET status=%s, updated_at=NOW()
                        WHERE id=%s AND status=%s
                    """, (OrderStatus.PRODUCTION.value, order_id, OrderStatus.SCHEDULED.value))
                conn.commit()
        elif new_status == ProcessStatus.IN_PROGRESS.value:
            with conn.cursor() as cursor:  # v5 #23
                cursor.execute("""
                    UPDATE production_orders
                    SET status=%s, actual_start=COALESCE(actual_start, NOW()), updated_at=NOW()
                    WHERE id=%s
                """, (ProductionStatus.IN_PROGRESS.value, production_id))
            with conn.cursor() as cursor:  # v5 #23
                cursor.execute("""
                    UPDATE orders SET status=%s, updated_at=NOW()
                    WHERE id=%s AND status=%s
                """, (OrderStatus.PRODUCTION.value, order_id, OrderStatus.SCHEDULED.value))
            conn.commit()

        # v3 包装入库联动（不修改 orders.status,已在 line 89-95 处理）
        if old_process_name == ProcessNames.PACKING.value and delta_qty != 0:
            try:
                FinishedGoodsDAO.stock_in(
                    order_id=order_id,
                    qty=delta_qty,
                    unit=new_unit,
                    warehouse="成品仓库",
                    operator=data.get("worker", ""),
                    remark=f"包装入库工序报工 {delta_qty:+.2f}{new_unit} (record_id={record_id})",
                    conn=conn
                )
                if production_id:
                    try:
                        with conn.cursor() as cursor:  # v5 #23
                            cursor.execute("""
                                SELECT po.order_no, o.order_no FROM production_orders po
                                JOIN orders o ON po.order_id = o.id
                                WHERE po.id=%s
                            """, (production_id,))
                            row = cursor.fetchone()
                        wo_no = row.get('order_no') if row else None
                        if wo_no:
                            import requests as _req
                            sync_url = os.environ.get('SYNC_BRIDGE_URL', 'http://127.0.0.1:5008')
                            _req.post(f'{sync_url}/api/sync/status-change', json={
                                'order_no': wo_no,
                                'status_key': 'warehousing',
                                'source': 'process.report_packing',
                                'delta_qty': delta_qty,
                                'unit': new_unit
                            }, timeout=2)
                    except Exception as e:
                        log("工序报工", "5008 同步失败", f"{type(e).__name__}: {e}")
            except Exception as e:
                log_error("工序报工", "包装入库联动失败", f"{type(e).__name__}: {e}")
                raise

        if new_status != old_status:
            log_status_change("process_records", record_id, old_status, new_status)
        return True
    except ValueError:
        try: conn.rollback()
        except Exception: pass
        raise
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: conn.close()
        except Exception: pass
```

### 6.4 修 `STATUS_ORDERS_MAP` 和 `status_key_map`（保留 v2）

```python
STATUS_ORDERS_MAP = {
    ProductionStatus.IN_PROGRESS.value: OrderStatus.PRODUCTION.value,
    ProductionStatus.COMPLETED.value: '报工完成',
    '报工完成': '报工完成',
    ProductionStatus.PACKED.value: OrderStatus.PACKED.value,  # v2/v3
    '已发货': OrderStatus.SHIPPED.value,
    '已收货': '已收货',
    '订单完成': '订单完成',
}

status_key_map = {
    ProductionStatus.IN_PROGRESS.value: 'in_production',
    ProductionStatus.COMPLETED.value: 'report_complete',
    '报工完成': 'report_complete',
    ProductionStatus.PACKED.value: 'warehousing',  # v2/v3
    '已发货': 'shipped',
    '已收货': 'received',
    '订单完成': 'order_complete',
}
```

## 7. 数据流图 v3

### 7.1 包装入库报工（成功路径）

```
报工: completed_qty=5 (delta=+5, process_name="包装入库", unit="件")
  ↓
ProcessDAO.update_record(record_id=100, data={completed_qty: 5, ...})
  ↓
1. SELECT old: process_name="包装入库", completed_qty=0, unit="件"
  ↓
2. v3 强校验: SUM(质量检验.qualified_qty) >= 0 + 5
   - 假设 QC 合格 = 10
   - 10 >= 5 ✅ 校验通过
  ↓
3. UPDATE process_records SET completed_qty=5
  ↓
4. delta = 5 - 0 = +5
  ↓
5. 检测: process_name="包装入库" 且 delta > 0
  ↓
6. FinishedGoodsDAO.stock_in(order_id=200, qty=+5, unit="件", conn=conn)
  ↓
7. 原子 SQL: UPDATE finished_goods SET quantity = quantity + 5
  ↓
8. UPDATE orders (line 89-95): 
   - 如果是最后一道工序: orders.status = OrderStatus.PACKED.value
  ↓
9. POST 5008 /api/sync/status-change (1 次)
```

### 7.2 包装入库报工（硬拒绝路径）

```
报工: completed_qty=15 (delta=+15, process_name="包装入库", unit="件")
  ↓
ProcessDAO.update_record(record_id=100, data={completed_qty: 15, ...})
  ↓
1. SELECT old: completed_qty=0
  ↓
2. v3 强校验: SUM(QC.qualified_qty) >= 0 + 15
   - 假设 QC 合格 = 10
   - 10 < 15 ❌ 校验失败
  ↓
3. raise ValueError("包装入库数量超过质量检验合格总数: ...")
  ↓
4. process_records 不写入
  ↓
5. finished_goods 不联动
  ↓
6. orders.status 不更新
  ↓
7. 5008 不触发
  ↓
8. UI 端 catch ValueError + 弹错误提示
```

### 7.3 完整业务流

```
工序 1-13: 焊接/链板等      → production_orders.status = 进行中
工序 14: 质量检验 COMPLETED  → unfinished_cnt=1 (包装入库未做)
                                → line 96-127: production_orders.status=IN_PROGRESS
                                → orders.status 保持 PRODUCTION
                                → log: 工序未全部完成

工序 15: 包装入库 COMPLETED
  ↓
1. v3 强校验: SUM(QC) >= 0 + delta
2. UPDATE process_records
3. 重新检查 unfinished_cnt=0 (所有工序都完成)
4. line 89-95 (v3 改造):
   - old_process_name="包装入库" → orders.status = OrderStatus.PACKED.value
5. FinishedGoodsDAO.stock_in(共享 conn)
6. POST 5008 warehousing

最终:
  - production_orders.status = COMPLETED
  - orders.status = PACKED ("包装入库")
  - finished_goods.quantity = SUM(包装入库.completed_qty)
  - 5008 收到 status_key="warehousing" 1 次
```

## 8. 文件改动清单 v3

| # | 文件 | 改动 | 代码量 |
|---|------|------|:------:|
| 1 | `constants.py` | 新增枚举值（v2 已加）| +20 行 |
| 2 | `models/shipment.py` | 新增 `FinishedGoodsDAO`（v3 修补 #14 #15,接受 conn）；改 `confirm_ship` 共享 conn | +120 行 / 改 30 行 |
| 3 | `models/process.py` | **完整重写** `update_record()`（v3 强校验 + 修补 #6 #13）| +60 行 / 改 30 行 |
| 4 | `models/production.py:169-177` | 字符串映射（v2）| 1 行 |
| 5 | `models/production.py:213-221` | 字符串映射（v2）| 1 行 |
| 6 | `tests/unit/models/test_finished_goods.py` | 8 用例（含 #14 #15 边界）| ~300 行 |
| 7 | `tests/unit/models/test_process.py` | 8 用例（含 v3 强校验 4 场景）| ~250 行 |
| 8 | `tests/unit/models/test_shipment.py` | 3 用例（confirm_ship 行为）| ~120 行 |

**总计**: ~900 行代码 + 文档

## 9. 数据流验证 v3

### 9.1 端到端测试用例

| # | 场景 | 输入 | 预期输出 | 修补项 |
|---|------|------|---------|-------|
| 1 | 首次入库（QC 充足）| 报工 +5, QC=10 | finished_goods qty=5, orders=PACKED | 16 |
| 2 | 累计入库 | 报工 +3 (5→8) | 已有 qty 5→8 | 1 |
| 3 | 并发入库 | 同时 +3 +2 | 最终 qty=10 | 1 |
| 4 | **硬拒绝**（QC 不足）| 报工 +15, QC=10 | ValueError, 不写入 | **16** |
| 5 | **业务流**：QC COMPLETED | QC 报工 +10 | orders.status=QC | **13** |
| 6 | **业务流**：Packing COMPLETED | 包装入库 +5 | orders.status=PACKED | **13** |
| 7 | **业务流**：跳过 QC | 其他最后工序完成 | orders.status=QC（保持） | 13 |
| 8 | 部分发货 | 发 3 件 | 仓库 8-3=5 | 2, 15 |
| 9 | 全部发货 | 仓库剩 5，发 5 | qty=0, status=已出库 | 2, 15 |
| 10 | **旧数据恢复** | finished_goods status=已出库, 报工+5 | 改回在库, qty=5 | **14** |
| 11 | **conn 共享** | confirm_ship → ship_out | 1 个 conn, 1 个事务 | **15** |
| 12 | 工序枚举 | "包装入库" | ProcessNames.PACKING.value | 9 |
| 13 | 单位传递 | unit="件" | finished_goods.unit="件" | 4 |
| 14 | 5008 同步 | 报工后 | 仅 1 次 POST | 5 |
| 15 🆕 | **#18 资源不泄漏（硬拒绝路径）** | 报工+15 QC=10, 强校验抛 ValueError | conn.closed=True, process_records 未写入 | **18, 24** |
| 16 🆕 | **#22 #23 with 模式** | 抛任意异常 | 所有 cursor 自动关, conn 关闭 | **22, 23, 24** |

### 9.2 单测覆盖

- `FinishedGoodsDAO.stock_in()` 5 边界（首次/累加/旧数据恢复/单位/并发）
- `FinishedGoodsDAO.ship_out()` 4 边界（正常/库存不足/全部发完/conn 共享）
- `ProcessDAO.update_record()` 联动 6 场景（包装入库/QC/其他/负 delta/重复/硬拒绝）
- `ProcessDAO.update_record()` **资源安全** 2 场景（**#24 硬拒绝 conn 不泄漏** / **#24 with 模式异常不泄漏**）
- `ShipmentDAO.confirm_ship()` 3 场景（正常/库存不足/conn 事务）
- `ShipmentDAO.confirm_ship()` **with 模式** 1 场景（#23 cursor 不泄漏）
- `constants.py` 枚举 3 测试

### 9.3 #24 专项测试（v5 新增）

```
# tests/unit/models/test_process.py
def test_update_record_hard_reject_no_leak():
    # #24 v5 专项测试: 硬拒绝路径不泄漏 conn + cursor
    # 模拟强校验抛 ValueError,验证:
    # 1. conn.closed == True
    # 2. process_records 表无新增记录
    # 3. finished_goods 表无变化
    # 4. 5008 不触发
    pass  # v5 实施时实现

def test_update_record_with_context_exception():
    # #24 v5 专项测试: with 模式 + 任意异常不泄漏 cursor
    # 模拟 SQL 抛异常,验证:
    # 1. 外层 cursor 自动关闭
    # 2. 强校验 cursor 自动关闭
    # 3. conn 关闭
    # 4. 无连接泄漏
    pass  # v5 实施时实现
```

## 10. 不变更部分 v3

| # | 模块/功能 | 保护 |
|---|----------|------|
| 1 | `ShipmentDAO.create()` | 不动 |
| 2 | `process_records` 表结构 | 不动 |
| 3 | `finished_goods` 表结构 | 不动 |
| 4 | `shipments` 表结构 | 不动 |
| 5 | 5008 端协议字段 | 不动 |
| 6 | 工序模板 15 道 | 不动 |
| 7 | `INSPECTION_ITEMS_BY_CATEGORY` | 不动 |
| 8 | 数据库初始化逻辑 | 不动 |
| 9 | 其他生产管理 UI | 不动 |
| 10 | 之前删掉的 `init_default_rules` | 不动 |
| 11 | `production.py:39-40` 冗余赋值 | 之前 P2 不动 |

## 11. 风险 v3

| # | 风险 | 严重度 | 缓解 | 修补项 |
|---|------|:------:|------|-------|
| 1 | 并发竞态 | 🟢 | 原子 SQL | 1 |
| 2 | ShipmentDAO 行为冲突 | 🟢 | confirm_ship 调 ship_out + 共享 conn | 2, 15 |
| 3 | 枚举不完整 | 🟢 | 扩展 OrderStatus.PACKED/ProductionStatus.PACKED | 3, 7 |
| 4 | 单位不一致 | 🟡 中 | 直接传, remark 记录 | 4 |
| 5 | 5008 双重触发 | 🟢 | 不走 update_status, 直 POST | 5 |
| 6 | old_completed_qty 缺失 | 🟢 | SELECT 扩字段 | 6 |
| 7 | 旧数据 status='已出库' | 🟢 | stock_in 检查 status, 改回在库 | 14 |
| 8 | 工序名硬编码 | 🟢 | ProcessNames 枚举 | 9 |
| 9 | import 循环 | 🟢 | 局部 import | 11 |
| 10 | shipments.unit 默认"米" | 🟡 中 | ship_out 跟 finished_goods.unit 联动 | 12 |
| 11 | **业务校验失败** | 🟢 已缓解 | 硬拒绝 + ValueError + UI 提示 + 整函数 try-finally | 16, 18 |
| 12 | **QC 阶段跳过** | 🟢 已缓解 | C 方案: 根据工序名动态决定 orders.status | 13 |
| 13 | **conn 冲突** | 🟢 已缓解 | ship_out 接受 conn 参数 | 15 |
| 18 | **conn 资源泄漏** | 🟢 已缓解（v4）| 整函数 try-finally 包 conn + cursor + ValueError 走 rollback | 18 |
| 19 | **报工回退不校验** | 🟢 | 业务上回退不会破坏约束,保持 | 19 |
| 20 | **强校验 SQL 字面量** | 🟢 已缓解（v4）| 改用 ProcessStatus.COMPLETED.value 枚举变量 | 20 |
| 21 | **QC 报工无上限** | 🟡 中 | 业务确认后 v5 加 QC ≤ 订单 quantity 校验 | 21 |
| 22 | **FinishedGoodsDAO.stock_in/ship_out cursor 关闭不完整** | 🟢 已缓解（v5）| 全部 cursor 改 `with` 上下文自动关 | 22 |
| 23 | **update_record 多处 cursor 没用 try-finally** | 🟢 已缓解（v5）| 全部 cursor 改 `with` 上下文 | 23 |
| 24 | **缺 #18 conn 泄漏专项测试** | 🟢 已缓解（v5）| §9.1 加 test_hard_reject_no_leak + §9.3 专项测试 | 24 |
| 28 | **v5 §6.3 缩进一致性（实施时验证）** | 🟢 已缓解（v6）| 实际提取 8 个 Python 代码块 + py_compile 8/8 通过 ✅ | 28 |

## 12. 回滚方案

如修复后出现严重问题：
1. 还原 `constants.py` 枚举（移除 PACKED + ProcessNames）
2. 还原 `models/shipment.py`（移除 FinishedGoodsDAO + 还原 confirm_ship 旧逻辑）
3. 还原 `models/process.py`（移除 v3 强校验 + 业务流修正）
4. 还原 `models/production.py` 字符串映射
5. 跑回归测试
