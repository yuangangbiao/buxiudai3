# -*- coding: utf-8 -*-
"""
9 张统计表 SQL 查询函数
修正了审计报告中的 8 处 SQL 字段错误

重要约定：
- 所有 process_records 来自 container_center 库（字段最完整）
- 所有 process_sub_steps 来自 container_center 库
- production_orders 来自 steel_belt 库
- inventory* 来自 inventory 库（库存管理）
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

from .mysql_config import get_conn

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# 通用工具
# ══════════════════════════════════════════════════════════
def _calc_pct(num: Optional[float], denom: Optional[float], default: float = 0.0) -> float:
    """百分比计算（防除零）"""
    if denom is None or denom == 0:
        return default
    return round(num / denom * 100, 2)


# ══════════════════════════════════════════════════════════
# 1️⃣ 生产日报
# ══════════════════════════════════════════════════════════
def query_production_daily(target_date: date) -> List[Dict[str, Any]]:
    """
    数据源: container_center.process_records
    修正 C-2.1/C-2.2: 用 quantity 字段，不用 customer_group 当产线
    修正 C-2.6: 产线从 process_records.line 字段读取（需先 ALTER TABLE 增加）
    """
    sql = """
        SELECT
            DATE(pr.plan_start) AS 日期,
            CASE HOUR(pr.created_at)
                WHEN 6,7,8,9,10,11,12,13,14 THEN '早班'
                WHEN 14,15,16,17,18,19,20,21,22 THEN '中班'
                ELSE '晚班'
            END AS 班组,
            COALESCE(pr.line, pr.flow_type, '默认产线') AS 产线,
            SUM(pr.quantity) AS 计划数,
            SUM(CASE WHEN pr.status='completed' THEN pr.quantity ELSE 0 END) AS 完成数
        FROM container_center.process_records pr
        WHERE pr.plan_start IS NOT NULL
          AND DATE(pr.plan_start) = %s
          AND pr.process_type = 'production'
        GROUP BY DATE(pr.plan_start), 班组, COALESCE(pr.line, pr.flow_type, '默认产线')
    """
    conn = get_conn('container_center')
    try:
        with conn.cursor() as c:
            c.execute(sql, (target_date,))
            rows = c.fetchall()
        # 后处理：差异率/合格率
        for r in rows:
            r['差异率'] = _calc_pct(
                (r.get('完成数') or 0) - (r.get('计划数') or 0),
                r.get('计划数')
            )
            r['合格率'] = _calc_pct(r.get('完成数'), r.get('完成数'), 100)
            r['记录ID'] = f"DR-{target_date}-{r['班组']}-{r['产线']}"
            r['操作员'] = ''
            r['备注'] = ''
            r['写入时间'] = datetime.now().isoformat()
        return rows
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════
# 2️⃣ 生产月报
# ══════════════════════════════════════════════════════════
def query_production_monthly(year_month: str) -> List[Dict[str, Any]]:
    """
    数据源: container_center.process_records
    year_month 格式: 'YYYY-MM'
    """
    sql = """
        SELECT
            DATE_FORMAT(pr.plan_start, '%%Y-%%m') AS 月份,
            COALESCE(pr.line, pr.flow_type, '默认产线') AS 产线,
            SUM(pr.quantity) AS 计划数,
            SUM(CASE WHEN pr.status='completed' THEN pr.quantity ELSE 0 END) AS 完成数,
            COUNT(DISTINCT pr.order_no) AS 订单数
        FROM container_center.process_records pr
        WHERE DATE_FORMAT(pr.plan_start, '%%Y-%%m') = %s
        GROUP BY DATE_FORMAT(pr.plan_start, '%%Y-%%m'),
                 COALESCE(pr.line, pr.flow_type, '默认产线')
    """
    conn = get_conn('container_center')
    try:
        with conn.cursor() as c:
            c.execute(sql, (year_month,))
            rows = c.fetchall()
        for r in rows:
            r['产能利用率'] = _calc_pct(r.get('完成数'), r.get('计划数'))
            r['达成率'] = _calc_pct(r.get('完成数'), r.get('计划数'))
            r['停机时长(h)'] = 0
            r['备注'] = ''
            r['记录ID'] = f"MR-{year_month}-{r['产线']}"
            r['写入时间'] = datetime.now().isoformat()
        return rows
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════
# 3️⃣ 车间产能分析
# ══════════════════════════════════════════════════════════
def query_workshop_capacity(target_date: date) -> List[Dict[str, Any]]:
    """
    数据源: container_center.process_sub_steps (含 equipment_name)
    修正 C-2.3: record_date 为 NULL 时用 created_at 兜底
    车间字段：约定"车间=设备前缀"（如 "焊接车间-A设备" → 车间=焊接车间）
    """
    sql = """
        SELECT
            pss.equipment_name AS 设备,
            SUBSTRING_INDEX(pss.equipment_name, '-', 1) AS 车间,
            COALESCE(DATE(pss.record_date), DATE(pss.created_at)) AS 日期,
            SUM(COALESCE(pss.overtime_hours, 0)) AS 工时,
            COUNT(*) AS 报工次数,
            SUM(pss.quantity) AS 报工数,
            SUM(pss.qualified_qty) AS 合格数
        FROM container_center.process_sub_steps pss
        WHERE pss.is_deleted = 0
          AND pss.equipment_name IS NOT NULL
          AND pss.equipment_name != ''
          AND COALESCE(DATE(pss.record_date), DATE(pss.created_at)) = %s
        GROUP BY pss.equipment_name, COALESCE(DATE(pss.record_date), DATE(pss.created_at))
    """
    conn = get_conn('container_center')
    try:
        with conn.cursor() as c:
            c.execute(sql, (target_date,))
            rows = c.fetchall()
        for r in rows:
            qty = r.get('报工数') or 0
            qualified = r.get('合格数') or 0
            hours = r.get('工时') or 0
            r['有效工时(h)'] = hours  # 实际工时（overtime 是加班工时，可单独跟踪）
            r['停机时长(h)'] = 0
            # 简化 OEE = 合格率（生产质量维度）
            # 真正的 OEE = 可用率 × 性能率 × 合格率，需从考勤表获取设备计划运行时间
            r['OEE'] = _calc_pct(qualified, qty)
            r['性能率'] = _calc_pct(qty, hours * 10 if hours else 1)  # 假设小时产能 10 件
            r['合格率'] = _calc_pct(qualified, qty)
            r['记录ID'] = f"WC-{r['车间']}-{r['设备']}-{target_date}"
            r['写入时间'] = datetime.now().isoformat()
        return rows
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════
# 4️⃣ 工单进度跟踪
# ══════════════════════════════════════════════════════════
def query_workorder_progress() -> List[Dict[str, Any]]:
    """
    数据源: container_center.process_records
    修正 C-2.4: JSON_EXTRACT 越界保护
    修正 C-2.6: 产线字段（用 process_records.line）
    """
    sql = """
        SELECT
            pr.order_no AS 工单号,
            pr.customer_name AS 客户,
            pr.product_name AS 产品,
            pr.plan_start AS 计划开始,
            pr.plan_end AS 计划完工,
            pr.created_at AS 实际开始,
            CASE WHEN pr.current_step >= JSON_LENGTH(pr.steps)
                 THEN pr.updated_at ELSE NULL END AS 实际完工,
            CASE
                WHEN pr.steps IS NOT NULL
                     AND pr.current_step < JSON_LENGTH(pr.steps)
                THEN JSON_UNQUOTE(JSON_EXTRACT(
                    pr.steps,
                    CONCAT('$[', pr.current_step, '].name')
                ))
                ELSE NULL
            END AS 当前工序,
            pr.current_step AS 完成工序,
            JSON_LENGTH(pr.steps) AS 总工序,
            pr.status AS 原始状态
        FROM container_center.process_records pr
        WHERE pr.order_no IS NOT NULL
          AND pr.order_no != ''
          AND pr.status NOT IN ('completed', 'cancelled')
    """
    conn = get_conn('container_center')
    try:
        with conn.cursor() as c:
            c.execute(sql)
            rows = c.fetchall()
        today = date.today()
        for r in rows:
            total = r.get('总工序') or 0
            done = r.get('完成工序') or 0
            r['进度条'] = _calc_pct(done, total)
            r['状态'] = _calc_wo_status(r, today)
            r['写入时间'] = datetime.now().isoformat()
        return rows
    finally:
        conn.close()


def _calc_wo_status(row: Dict, today: date) -> str:
    """工单状态计算：待生产/生产中/已完成/已延期"""
    total = row.get('总工序') or 0
    done = row.get('完成工序') or 0
    if done >= total > 0:
        return '已完成'
    plan_end = row.get('计划完工')
    if plan_end and plan_end < today and done < total:
        return '已延期'
    if done > 0:
        return '生产中'
    return '待生产'


# ══════════════════════════════════════════════════════════
# 5️⃣ 工序报工汇总
# ══════════════════════════════════════════════════════════
def query_substep_recent(since: datetime, limit: int = 100) -> List[Dict[str, Any]]:
    """
    数据源: container_center.process_sub_steps
    修正 C-2.5: 明确使用 container_center 库
    """
    sql = """
        SELECT
            pss.order_no AS 工单号,
            pss.step_name AS 工序,
            pss.operator AS 操作人,
            COALESCE(pss.batch_no, '') AS 批次号,
            pss.quantity AS 报工数,
            pss.qualified_qty AS 合格数,
            pss.equipment_name AS 设备,
            pss.created_at AS 报工时间,
            COALESCE(pss.remark, '') AS 备注
        FROM container_center.process_sub_steps pss
        WHERE pss.is_deleted = 0
          AND pss.created_at >= %s
        ORDER BY pss.created_at DESC
        LIMIT %s
    """
    conn = get_conn('container_center')
    try:
        with conn.cursor() as c:
            c.execute(sql, (since, limit))
            rows = c.fetchall()
        for r in rows:
            r['合格率'] = _calc_pct(r.get('合格数'), r.get('报工数'))
            r['记录ID'] = f"SS-{r['工单号']}-{r['工序']}-{r['批次号']}"
            r['写入时间'] = datetime.now().isoformat()
        return rows
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════
# 6️⃣ 库存周报
# ══════════════════════════════════════════════════════════
def query_inventory_weekly(week_start: date, week_end: date) -> List[Dict[str, Any]]:
    """
    数据源: inventory.inventory_transactions + warehouses
    修正 C-2.7: type 枚举值需先用 SELECT DISTINCT 验证（已确认: in/out）
    """
    sql = """
        SELECT
            w.name AS 仓库,
            SUM(CASE WHEN it.type='in' THEN it.qty ELSE 0 END) AS 入库数,
            SUM(CASE WHEN it.type='out' THEN it.qty ELSE 0 END) AS 出库数,
            COUNT(*) AS 异动笔数,
            MIN(DATE(it.created_at)) AS 周起始日期,
            MAX(DATE(it.created_at)) AS 周结束日期,
            YEARWEEK(%s, 3) AS 周次
        FROM inventory.inventory_transactions it
        LEFT JOIN inventory.warehouses w ON w.id = it.warehouse_id
        WHERE DATE(it.created_at) BETWEEN %s AND %s
          AND w.is_active = 1
          AND w.deleted_at IS NULL
        GROUP BY w.id, w.name
    """
    conn = get_conn('inventory')
    try:
        with conn.cursor() as c:
            c.execute(sql, (week_start, week_start, week_end))
            rows = c.fetchall()
        for r in rows:
            r['库存余额'] = _query_inventory_balance(conn, r['仓库'])
            r['库存金额'] = _query_inventory_value(conn, r['仓库'])
            r['记录ID'] = f"IWR-{r['周次']}-{r['仓库']}"
            r['写入时间'] = datetime.now().isoformat()
        return rows
    finally:
        conn.close()


def _query_inventory_balance(conn, warehouse_name: str) -> float:
    """查询某仓库当前库存余额"""
    with conn.cursor() as c:
        c.execute("""
            SELECT COALESCE(SUM(inv.current_qty), 0) AS total
            FROM inventory.inventory inv
            INNER JOIN inventory.warehouses w ON w.id = inv.warehouse_id
            WHERE w.name = %s
        """, (warehouse_name,))
        row = c.fetchone()
    return float(row['total']) if row else 0.0


def _query_inventory_value(conn, warehouse_name: str) -> float:
    """查询某仓库当前库存金额（数量 × 最近采购价）"""
    with conn.cursor() as c:
        c.execute("""
            SELECT COALESCE(SUM(inv.current_qty * p.last_purchase_price), 0) AS total
            FROM inventory.inventory inv
            INNER JOIN inventory.warehouses w ON w.id = inv.warehouse_id
            INNER JOIN inventory.products p ON p.id = inv.product_id
            WHERE w.name = %s AND p.deleted_at IS NULL
        """, (warehouse_name,))
        row = c.fetchone()
    return float(row['total']) if row else 0.0


# ══════════════════════════════════════════════════════════
# 7️⃣ 物料收发存汇总
# ══════════════════════════════════════════════════════════
def query_inventory_monthly(year_month: str) -> List[Dict[str, Any]]:
    """数据源: inventory.inventory_transactions + products"""
    sql = """
        SELECT
            p.code AS 物料编码,
            p.name AS 物料名称,
            p.unit AS 单位,
            SUM(CASE WHEN it.type='in' THEN it.qty ELSE 0 END) AS 入库数量,
            SUM(CASE WHEN it.type='out' THEN it.qty ELSE 0 END) AS 出库数量,
            COALESCE(p.last_purchase_price, 0) AS 单价
        FROM inventory.inventory_transactions it
        INNER JOIN inventory.products p ON p.id = it.product_id
        WHERE DATE_FORMAT(it.created_at, '%%Y-%%m') = %s
          AND p.deleted_at IS NULL
        GROUP BY p.id, p.code, p.name, p.unit, p.last_purchase_price
    """
    conn = get_conn('inventory')
    try:
        with conn.cursor() as c:
            c.execute(sql, (year_month,))
            rows = c.fetchall()
        for r in rows:
            inbound = r.get('入库数量') or 0
            outbound = r.get('出库数量') or 0
            r['期初数量'] = 0  # TODO: 期初需要快照表或上月期末
            r['期末数量'] = r['期初数量'] + inbound - outbound
            r['期末金额'] = round(r['期末数量'] * (r.get('单价') or 0), 2)
            r['记录ID'] = f"IMS-{year_month}-{r['物料编码']}"
            r['月份'] = year_month
            r['写入时间'] = datetime.now().isoformat()
        return rows
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════
# 8️⃣ 库存预警表
# ══════════════════════════════════════════════════════════
def query_inventory_alert(safety_threshold: int = 10) -> List[Dict[str, Any]]:
    """
    修正 C-2.8: products.safety_stock 字段不存在
    方案: 用环境变量 INVENTORY_SAFETY_THRESHOLD 作为全局阈值
    若需个性化阈值，需先 ALTER TABLE products ADD safety_stock INT
    """
    sql = """
        SELECT
            p.code AS 物料编码,
            p.name AS 物料名称,
            w.name AS 仓库,
            inv.current_qty AS 当前库存,
            MAX(it.created_at) AS 最近入库时间,
            %s AS 安全库存
        FROM inventory.inventory inv
        INNER JOIN inventory.products p ON p.id = inv.product_id
        INNER JOIN inventory.warehouses w ON w.id = inv.warehouse_id
        LEFT JOIN inventory.inventory_transactions it
            ON it.product_id = inv.product_id AND it.warehouse_id = inv.warehouse_id
        WHERE p.deleted_at IS NULL
          AND w.is_active = 1
          AND w.deleted_at IS NULL
        GROUP BY p.id, w.id, inv.current_qty
        HAVING 当前库存 < %s
    """
    conn = get_conn('inventory')
    try:
        with conn.cursor() as c:
            c.execute(sql, (safety_threshold, safety_threshold))
            rows = c.fetchall()
        for r in rows:
            current = r.get('当前库存') or 0
            safety = r.get('安全库存') or 0
            if current <= 0:
                r['预警状态'] = '缺货'
            elif current < safety * 0.5:
                r['预警状态'] = '严重低库存'
            else:
                r['预警状态'] = '低库存'
            r['建议补货量'] = max(0, safety - current)
            r['写入时间'] = datetime.now().isoformat()
        return rows
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════
# 9️⃣ 呆滞料分析
# ══════════════════════════════════════════════════════════
def query_inventory_slow_moving(days_threshold: int = 90) -> List[Dict[str, Any]]:
    """库龄超过 N 天未动的物料"""
    sql = """
        SELECT
            p.code AS 物料编码,
            p.name AS 物料名称,
            w.name AS 仓库,
            inv.current_qty AS 当前库存,
            MAX(it.created_at) AS 最后异动日期,
            DATEDIFF(NOW(), MAX(it.created_at)) AS 库龄,
            COALESCE(p.last_purchase_price, 0) AS 单价
        FROM inventory.inventory inv
        INNER JOIN inventory.products p ON p.id = inv.product_id
        INNER JOIN inventory.warehouses w ON w.id = inv.warehouse_id
        LEFT JOIN inventory.inventory_transactions it
            ON it.product_id = inv.product_id
        WHERE p.deleted_at IS NULL
          AND w.deleted_at IS NULL
          AND inv.current_qty > 0
        GROUP BY p.id, w.id, inv.current_qty, p.last_purchase_price
        HAVING 库龄 > %s
    """
    conn = get_conn('inventory')
    try:
        with conn.cursor() as c:
            c.execute(sql, (days_threshold,))
            rows = c.fetchall()
        for r in rows:
            days = r.get('库龄') or 0
            r['库存金额'] = round((r.get('当前库存') or 0) * (r.get('单价') or 0), 2)
            if days > 365:
                r['状态'] = '超1年'
            elif days > 180:
                r['状态'] = '半年'
            elif days > 90:
                r['状态'] = '3个月'
            else:
                r['状态'] = '正常'
            r['写入时间'] = datetime.now().isoformat()
        return rows
    finally:
        conn.close()
