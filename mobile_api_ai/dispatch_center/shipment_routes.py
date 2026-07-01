# -*- coding: utf-8 -*-
"""
发货管理路由 (5003 调度中心)

将桌面端 ShipmentView 的功能暴露为 REST API，供移动端 / 外部系统 / 回归测试调用。

设计原则:
1. 路由层只做参数解析 + 调用 ShipmentDAO + 返回 JSON，不做业务逻辑
2. 错误统一返回 {"code": <非0>, "message": "..."}，正常返回 {"code": 0, "data": ...}
3. 数据库连接由 ShipmentDAO 管理，路由层不直接持有 conn
4. **强制切换到 steel_belt 库** — shipments/finished_goods/shipment_tracks 在该库，
   5003 默认主库是 container_center，所以每个查询前必须 conn.select_db('steel_belt')
5. 物流追踪 API 走可选模块 utils.logistics_tracker（如不存在则降级返回 503）
"""
import logging
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# 业务数据所在数据库（5003 主库是 container_center, 但发货表在 steel_belt）
SHIPMENT_DB = "steel_belt"

# 蓝图
shipment_bp = Blueprint('shipment', __name__, url_prefix='/api/dispatch-center/shipping')


def _ok(data=None):
    """成功响应"""
    return jsonify({"code": 0, "data": data if data is not None else []})


def _err(message, http_status=500):
    """错误响应"""
    return jsonify({"code": http_status, "message": message}), http_status


def _get_shipment_conn():
    """获取 ShipmentDAO 用的连接 — 强制连 steel_belt 库"""
    try:
        from models.database import get_connection
        conn = get_connection()
        # 5003 默认主库是 container_center, 强制切到业务库
        current_db = conn.db.decode() if isinstance(conn.db, bytes) else conn.db
        if current_db != SHIPMENT_DB:
            conn.select_db(SHIPMENT_DB)
        return conn
    except Exception as e:
        logger.error(f"[Shipping] 获取连接失败: {e}")
        return None


def _get_dao():
    """延迟导入 ShipmentDAO，避免循环依赖"""
    try:
        from models.shipment import ShipmentDAO
        return ShipmentDAO
    except Exception as e:
        logger.error(f"[Shipping] 加载 ShipmentDAO 失败: {e}")
        return None


def _get_filters_from_request():
    """从请求中解析 filters 字典"""
    return {
        "status": request.args.get("status", "全部"),
        "keyword": request.args.get("keyword", "").strip(),
        "date_from": request.args.get("date_from", ""),
        "date_to": request.args.get("date_to", ""),
    }


# ── 1. 待发货列表 ──────────────────────────────────────────
@shipment_bp.route('/pending', methods=['GET'])
def pending():
    """获取待发货列表 (status=PENDING)"""
    conn = _get_shipment_conn()
    if not conn:
        return _err("数据库连接不可用", 503)
    try:
        sql = """
            SELECT s.*, o.order_no, o.customer_name, o.product_type
            FROM shipments s
            JOIN orders o ON s.order_id = o.id
            WHERE s.status = '待发货'
            AND s.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
        """
        params = []
        kw = request.args.get("keyword", "").strip()
        if kw:
            sql += " AND (o.order_no LIKE %s OR o.customer_name LIKE %s OR s.shipment_no LIKE %s)"
            kw_pat = f"%{kw}%"
            params.extend([kw_pat, kw_pat, kw_pat])
        sql += " ORDER BY s.created_at DESC LIMIT 200"
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return _ok([dict(r) for r in rows])
    except Exception as e:
        logger.exception("[Shipping] /pending 异常")
        return _err(f"查询失败: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── 2. 发货单列表（带筛选） ─────────────────────────────────
@shipment_bp.route('/list', methods=['GET'])
def list_shipments():
    """获取全部发货单，支持状态/关键词/日期筛选"""
    conn = _get_shipment_conn()
    if not conn:
        return _err("数据库连接不可用", 503)
    try:
        sql = """
            SELECT s.*, o.order_no, o.customer_name, o.product_type
            FROM shipments s
            JOIN orders o ON s.order_id = o.id
            WHERE s.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
        """
        params = []
        status = request.args.get("status", "全部")
        if status and status != "全部":
            sql += " AND s.status=%s"
            params.append(status)
        kw = request.args.get("keyword", "").strip()
        if kw:
            kw_pat = f"%{kw}%"
            sql += " AND (o.order_no LIKE %s OR o.customer_name LIKE %s OR s.shipment_no LIKE %s)"
            params.extend([kw_pat, kw_pat, kw_pat])
        date_from = request.args.get("date_from", "")
        if date_from:
            sql += " AND s.ship_date >= %s"
            params.append(date_from)
        date_to = request.args.get("date_to", "")
        if date_to:
            sql += " AND s.ship_date <= %s"
            params.append(date_to)
        limit = int(request.args.get("limit", 200))
        sql += " ORDER BY s.created_at DESC LIMIT %s"
        params.append(limit)
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return _ok([dict(r) for r in rows])
    except Exception as e:
        logger.exception("[Shipping] /list 异常")
        return _err(f"查询失败: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── 3. 新建发货单 ──────────────────────────────────────────
@shipment_bp.route('/create', methods=['POST'])
def create_shipment():
    """创建发货单

    Body JSON 字段:
        finished_goods_id (int, 必填)
        ship_quantity (float, 必填 > 0)
        warehouse (str, 默认"成品仓库")
        logistics_company (str)
        tracking_no (str)
        ship_date (str, YYYY-MM-DD)
        recipient / recipient_phone / recipient_address (str)
        freight (float, 默认 0)
        remark (str)
    """
    conn = _get_shipment_conn()
    if not conn:
        return _err("数据库连接不可用", 503)
    data = request.get_json(silent=True) or {}
    try:
        fg_id = data.get("finished_goods_id")
        if not fg_id:
            return _err("finished_goods_id 必填", 400)

        qty = float(data.get("ship_quantity") or 0)
        if qty <= 0:
            return _err("ship_quantity 必须大于 0", 400)

        # 校验成品库存存在
        with conn.cursor() as cur:
            cur.execute("""
                SELECT fg.id, fg.order_id, fg.unit, fg.quantity
                FROM finished_goods fg WHERE fg.id=%s AND fg.status='在库'
            """, (fg_id,))
            fg = cur.fetchone()
        if not fg:
            return _err(f"成品库存 id={fg_id} 不存在或已出库", 404)

        # 尝试调用 ShipmentDAO.create; 失败时直接 INSERT
        shipment_no = _new_shipment_no()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO shipments (
                        shipment_no, order_id, finished_goods_id, warehouse,
                        ship_quantity, unit, logistics_company, tracking_no,
                        ship_date, recipient, recipient_phone, recipient_address,
                        freight, status, remark
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '待发货', %s)
                """, (
                    shipment_no,
                    fg.get("order_id"),
                    fg_id,
                    data.get("warehouse", "成品仓库"),
                    qty,
                    fg.get("unit") or "米",
                    data.get("logistics_company", ""),
                    data.get("tracking_no", ""),
                    data.get("ship_date", ""),
                    data.get("recipient", ""),
                    data.get("recipient_phone", ""),
                    data.get("recipient_address", ""),
                    float(data.get("freight") or 0),
                    data.get("remark", ""),
                ))
                new_id = cur.lastrowid
            conn.commit()
            return _ok({"id": new_id, "shipment_no": shipment_no})
        except Exception as e:
            conn.rollback()
            return _err(f"创建失败: {e}")
    except Exception as e:
        logger.exception("[Shipping] /create 异常")
        return _err(f"创建异常: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── 4. 确认发货 ──────────────────────────────────────────
@shipment_bp.route('/confirm-ship', methods=['POST'])
def confirm_ship():
    """确认发货（status: 待发货 → 已发货，扣减成品库存）

    Body JSON:
        shipment_id (int, 必填) 或 shipment_no (str, 必填，二选一)
    """
    conn = _get_shipment_conn()
    if not conn:
        return _err("数据库连接不可用", 503)
    data = request.get_json(silent=True) or {}
    try:
        shipment_id = data.get("shipment_id")
        if not shipment_id and data.get("shipment_no"):
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM shipments WHERE shipment_no=%s", (data["shipment_no"],))
                row = cur.fetchone()
            if not row:
                return _err(f"发货单 {data['shipment_no']} 不存在", 404)
            shipment_id = row.get("id") if isinstance(row, dict) else row[0]
        if not shipment_id:
            return _err("shipment_id 或 shipment_no 必填", 400)

        # 1. 读取发货单
        with conn.cursor() as cur:
            cur.execute("""
                SELECT order_id, finished_goods_id, ship_quantity, status
                FROM shipments WHERE id=%s
            """, (shipment_id,))
            row = cur.fetchone()
        if not row:
            return _err(f"发货单 {shipment_id} 不存在", 404)
        if row.get("status") == "已发货":
            return _err("该发货单已发货", 400)
        if row.get("status") == "已收货":
            return _err("该发货单已收货", 400)

        order_id = row.get("order_id")
        fg_id = row.get("finished_goods_id")
        ship_qty = float(row.get("ship_quantity") or 0)

        # 2. 扣减成品库存
        if fg_id:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE finished_goods
                    SET quantity = quantity - %s,
                        status = CASE WHEN quantity - %s <= 0 THEN '已出库' ELSE status END
                    WHERE id=%s AND quantity >= %s
                """, (ship_qty, ship_qty, fg_id, ship_qty))
                if cur.rowcount == 0:
                    conn.rollback()
                    return _err(f"库存不足: 无法扣减 {ship_qty}", 400)

        # 3. 更新发货单状态
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE shipments SET status='已发货',
                ship_date=COALESCE(NULLIF(ship_date,''), DATE(NOW())),
                updated_at=NOW() WHERE id=%s
            """, (shipment_id,))

        # 4. 更新订单状态
        if order_id:
            with conn.cursor() as cur:
                cur.execute("UPDATE orders SET status='已发货', updated_at=NOW() WHERE id=%s", (order_id,))

        conn.commit()
        return _ok({"shipment_id": shipment_id, "status": "已发货"})
    except Exception as e:
        conn.rollback()
        logger.exception("[Shipping] /confirm-ship 异常")
        return _err(f"确认发货异常: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── 5. 确认收货 ──────────────────────────────────────────
@shipment_bp.route('/confirm-receive', methods=['POST'])
def confirm_receive():
    """确认收货（status: 已发货 → 已收货，订单标记完成）

    Body JSON:
        shipment_id (int, 必填) 或 shipment_no (str, 必填，二选一)
    """
    conn = _get_shipment_conn()
    if not conn:
        return _err("数据库连接不可用", 503)
    data = request.get_json(silent=True) or {}
    try:
        shipment_id = data.get("shipment_id")
        if not shipment_id and data.get("shipment_no"):
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM shipments WHERE shipment_no=%s", (data["shipment_no"],))
                row = cur.fetchone()
            if not row:
                return _err(f"发货单 {data['shipment_no']} 不存在", 404)
            shipment_id = row.get("id") if isinstance(row, dict) else row[0]
        if not shipment_id:
            return _err("shipment_id 或 shipment_no 必填", 400)

        with conn.cursor() as cur:
            cur.execute("SELECT order_id, status FROM shipments WHERE id=%s", (shipment_id,))
            row = cur.fetchone()
        if not row:
            return _err(f"发货单 {shipment_id} 不存在", 404)
        if row.get("status") == "已收货":
            return _err("该发货单已收货", 400)
        if row.get("status") != "已发货":
            return _err(f"状态非法: 当前 {row.get('status')}, 需已发货", 400)
        order_id = row.get("order_id")

        with conn.cursor() as cur:
            cur.execute("UPDATE shipments SET status='已收货', updated_at=NOW() WHERE id=%s", (shipment_id,))
            if order_id:
                cur.execute("UPDATE orders SET status='订单完成', updated_at=NOW() WHERE id=%s", (order_id,))
        conn.commit()
        return _ok({"shipment_id": shipment_id, "status": "已收货", "order_status": "订单完成"})
    except Exception as e:
        conn.rollback()
        logger.exception("[Shipping] /confirm-receive 异常")
        return _err(f"确认收货异常: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── 6. 成品库存 ──────────────────────────────────────────
@shipment_bp.route('/finished-goods', methods=['GET'])
def finished_goods():
    """获取成品库存列表（status=在库）"""
    conn = _get_shipment_conn()
    if not conn:
        return _err("数据库连接不可用", 503)
    try:
        order_id = request.args.get("order_id")
        days_limit = int(request.args.get("days_limit", 60))

        if order_id:
            sql = """
                SELECT fg.*, o.order_no, o.customer_name, o.product_type
                FROM finished_goods fg
                JOIN orders o ON fg.order_id = o.id
                WHERE fg.order_id=%s AND fg.status='在库'
            """
            params = [order_id]
        else:
            sql = """
                SELECT fg.*, o.order_no, o.customer_name, o.product_type
                FROM finished_goods fg
                JOIN orders o ON fg.order_id = o.id
                WHERE fg.status='在库'
            """
            params = []

        if days_limit and not order_id:
            sql += " AND fg.in_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)"
            params.append(days_limit)

        sql += " ORDER BY fg.in_date DESC LIMIT 500"

        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return _ok([dict(r) for r in rows])
    except Exception as e:
        logger.exception("[Shipping] /finished-goods 异常")
        return _err(f"查询失败: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── 7. 物流追踪列表 ──────────────────────────────────────────
@shipment_bp.route('/tracking-list', methods=['GET'])
def tracking_list():
    """获取发货单列表 + 最新物流状态（用于追踪 Tab）

    Query:
        status (str, 可选) — 筛选发货单状态，默认 '已发货'
    """
    conn = _get_shipment_conn()
    if not conn:
        return _err("数据库连接不可用", 503)
    try:
        status = request.args.get("status", "已发货")
        kw = request.args.get("keyword", "").strip()

        # LEFT JOIN 单 SQL: shipments + orders + 最新 shipment_tracks
        sql = """
            SELECT s.*, o.order_no, o.customer_name, o.product_type,
                   st.state_text AS track_state,
                   st.query_time AS track_time
            FROM shipments s
            JOIN orders o ON s.order_id = o.id
            LEFT JOIN shipment_tracks st ON st.id = (
                SELECT t.id FROM shipment_tracks t
                WHERE t.shipment_id = s.id
                ORDER BY t.query_time DESC LIMIT 1
            )
            WHERE 1=1
        """
        params = []
        if status and status != "全部":
            sql += " AND s.status=%s"
            params.append(status)
        if kw:
            kw_pat = f"%{kw}%"
            sql += " AND (o.order_no LIKE %s OR o.customer_name LIKE %s OR s.shipment_no LIKE %s OR s.tracking_no LIKE %s)"
            params.extend([kw_pat, kw_pat, kw_pat, kw_pat])
        sql += " ORDER BY s.created_at DESC LIMIT 200"
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return _ok([dict(r) for r in rows])
    except Exception as e:
        logger.exception("[Shipping] /tracking-list 异常")
        return _err(f"查询失败: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── 8. 查询物流（占位实现） ──────────────────────────────────
@shipment_bp.route('/query-tracking', methods=['POST'])
def query_tracking():
    """查询物流动态

    Body JSON:
        tracking_no (str, 必填)
        company_name (str, 可选)
        shipment_id (int, 可选 — 提供则自动保存查询结果到 shipment_tracks)

    说明: utils.logistics_tracker 模块可能未实现。返回 503 提示用户使用桌面端查询。
    """
    data = request.get_json(silent=True) or {}
    tracking_no = (data.get("tracking_no") or "").strip()
    if not tracking_no:
        return _err("tracking_no 必填", 400)

    try:
        from utils.logistics_tracker import get_tracker
    except ImportError:
        return _err(
            "物流追踪 API 模块未配置（utils.logistics_tracker）。"
            "请在桌面端「⚙️ 追踪设置」中配置 API 密钥后使用，或调桌面端查询。",
            503
        )

    try:
        tracker = get_tracker()
        if not tracker.is_configured():
            return _err("物流追踪 API 未配置密钥", 503)

        company_name = data.get("company_name", "")
        result = tracker.query_sync(tracking_no, company_name)

        # 若有 shipment_id，保存查询结果到 steel_belt.shipment_tracks
        if result.get("success") and data.get("shipment_id"):
            conn = _get_shipment_conn()
            if conn:
                try:
                    traces_json = json.dumps(result.get("traces", []), ensure_ascii=False)
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO shipment_tracks
                            (shipment_id, tracking_no, state, state_text, traces, company_code, query_time)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            int(data["shipment_id"]),
                            tracking_no,
                            result.get("state", "0"),
                            result.get("state_text", ""),
                            traces_json,
                            result.get("company", ""),
                        ))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"[Shipping] 保存追踪结果失败: {e}")
                finally:
                    conn.close()
        return _ok(result)
    except Exception as e:
        logger.exception("[Shipping] /query-tracking 异常")
        return _err(f"查询异常: {e}")


# ── 9. 订阅物流推送（占位实现） ──────────────────────────────
@shipment_bp.route('/subscribe-tracking', methods=['POST'])
def subscribe_tracking():
    """订阅物流推送

    Body JSON:
        tracking_no (str, 必填)
        company_name (str, 可选)

    说明: 同 /query-tracking，依赖 utils.logistics_tracker 模块
    """
    data = request.get_json(silent=True) or {}
    tracking_no = (data.get("tracking_no") or "").strip()
    if not tracking_no:
        return _err("tracking_no 必填", 400)

    try:
        from utils.logistics_tracker import get_tracker
    except ImportError:
        return _err(
            "物流追踪 API 模块未配置。请在桌面端「⚙️ 追踪设置」中配置。",
            503
        )

    try:
        tracker = get_tracker()
        if not tracker.is_configured():
            return _err("物流追踪 API 未配置密钥", 503)
        result = tracker.subscribe(tracking_no, data.get("company_name", ""))
        return _ok(result)
    except Exception as e:
        logger.exception("[Shipping] /subscribe-tracking 异常")
        return _err(f"订阅异常: {e}")


# ── 健康检查 ──────────────────────────────────────────
@shipment_bp.route('/health', methods=['GET'])
def health():
    """健康检查端点 + 实际数据库连接验证"""
    conn = _get_shipment_conn()
    db_ok = False
    db_name = None
    shipments_count = 0
    if conn:
        try:
            db_name = conn.db.decode() if isinstance(conn.db, bytes) else conn.db
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM shipments")
                row = cur.fetchone()
                shipments_count = (row.get("c") if row else 0) or 0
            db_ok = True
        except Exception as e:
            logger.warning(f"[Shipping] health DB 探测失败: {e}")
        finally:
            conn.close()
    return _ok({
        "service": "shipping",
        "dao_available": _get_dao() is not None,
        "db_connected": db_ok,
        "db_name": db_name,
        "shipments_count": shipments_count,
    })

