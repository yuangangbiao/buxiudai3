import os
import json
import time
import logging
import threading
import uuid
import requests
from datetime import datetime
from flask import Blueprint, jsonify, request

from core.config import MYSQL_CFG, CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
from core.db import get_direct_connection

logger = logging.getLogger(__name__)

sync_bp = Blueprint('sync_bridge', __name__, url_prefix='/api/sync')


def _get_mysql_connection():
    """steel_belt 写入连接 — 走连接池"""
    from db.steelbelt_pool import get_conn
    return get_conn()


def _get_container_conn():
    """container_center 读取连接 — 走连接池"""
    from storage.mysql_storage import MySQLStorage
    return MySQLStorage.get_connection()

STATUS_KEY_TO_MYSQL = {
    'published': '已发布',
    'scheduled': '已排产',
    'confirmed': '已排产',
    'in_production': '生产中',
    'reported': '生产中',
    'qc_passed': '生产中',
    'report_complete': '报工完成',
    'warehousing': '成品入库',
    'shipped': '已发货',
    'received': '已收货',
    'order_complete': '订单完成',
    'completed': '已完成',
    'cancelled': '已取消',
}


# 修补 T8 (F8.5): status_key → flow_type 同步推断表
# 与 D3.1 决策一致: 5 种 flow_type (production/quality/material_purchase/outsource/repair)
SYNC_STATUS_KEY_TO_FLOW_TYPE = {
    # 质检相关
    'qc_passed': 'quality',
    'qc_review': 'quality',
    'qc_failed': 'quality',
    'report_complete': 'quality',
    # 物料相关
    'material_arrived': 'material_purchase',
    'material_delivered': 'material_purchase',
    'material_requested': 'material_purchase',
    'material_confirmed': 'material_purchase',
    'material_deadline': 'material_purchase',
    # 外协相关
    'outsource_created': 'outsource',
    'outsource_confirmed': 'outsource',
    'outsource_production': 'outsource',
    'outsource_qc': 'outsource',
    'outsource_returned': 'outsource',
    # 报修相关
    'repair_created': 'repair',
    'repair_completed': 'repair',
}


def infer_sync_status_to_flow_type(status_key: str) -> str:
    """T8 推断函数 (模块级, 纯函数)

    Args:
        status_key: status_key 字符串 (如 'qc_passed' / 'material_arrived')

    Returns:
        flow_type 字符串 (5 种之一)
        未知或空 → 兜底 'production'
    """
    if not status_key:
        return 'production'
    return SYNC_STATUS_KEY_TO_FLOW_TYPE.get(status_key.lower(), 'production')


def _resolve_sync_flow_type(flow_type: str, status_key: str = '') -> str:
    """T8 公共解析函数: 显式 flow_type 优先, 推断兜底

    Args:
        flow_type: 调用方显式传入 (可能为空)
        status_key: 用于推断的 status_key

    Returns:
        解析后的 flow_type
    """
    return flow_type or infer_sync_status_to_flow_type(status_key)


def infer_step_name_to_flow_type(step_name: str) -> str:
    """修补 T9 (F9.3): step_name 子串匹配推断函数 (与 status_key 精确匹配互补)

    Args:
        step_name: 工序名称 (如 'QC-Inspection' / '焊接' / '外协加工' / '质量检验')

    Returns:
        flow_type 字符串 (5 种之一)
        未知 → 兜底 'production'
    """
    if not step_name:
        return 'production'
    sl = step_name.lower()
    # 质检相关 (中英文)
    if 'qc' in sl or '质量' in step_name or '检验' in step_name or 'inspection' in sl:
        return 'quality'
    # 外协相关
    if '外协' in step_name or 'outsource' in sl:
        return 'outsource'
    # 物料相关
    if '物料' in step_name or '采购' in step_name or 'material' in sl or 'purchase' in sl:
        return 'material_purchase'
    # 报修相关
    if '报修' in step_name or 'repair' in sl:
        return 'repair'
    return 'production'

SYNC_BRIDGE_SELF_URL = os.environ.get('SYNC_BRIDGE_SELF_URL', 'http://127.0.0.1:8008')

# 报工确认表自检 (TASK-7, F1 同源: 缺列/缺表时建表)
def _ensure_report_request_table():
    """确保 report_request 表存在 — 5003 报工确认落表
    Schema:
        id           INT AUTO_INCREMENT PRIMARY KEY
        order_no     VARCHAR(64) NOT NULL
        operator_id  VARCHAR(64) NOT NULL
        confirmed    TINYINT(1)  DEFAULT 0
        remark       VARCHAR(500)
        source       VARCHAR(32)  DEFAULT 'dispatch_center_5003'
        created_at   DATETIME     DEFAULT NOW()
    """
    conn = None
    try:
        conn = _get_mysql_connection()
        with conn.cursor() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS report_request (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_no VARCHAR(64) NOT NULL,
                    operator_id VARCHAR(64) NOT NULL,
                    confirmed TINYINT(1) DEFAULT 0,
                    remark VARCHAR(500),
                    source VARCHAR(32) DEFAULT 'dispatch_center_5003',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_order_op (order_no, operator_id),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
            logger.info('[SyncBridge] report_request 表自检通过')
    except Exception as e:
        logger.warning('[SyncBridge] report_request 表自检失败 (非致命): %s', e)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

_ensure_report_request_table()


def _get_container_storage():
    """获取容器中心存储实例。

    [F6 v4.0 标注] 本函数虽然名字含 "container"，但实际走的是
    MySQL 容器中心（container_center 库），与早期 site 4 的
    `container_storage.db` SQLite 文件**无关**——后者已在 F6 T4 阶段
    彻底从代码库中清理。`resolve_storage_type()` 在 v4.0 下默认返回
    `mysql`，因此本函数返回的是 MySQLStorage 实例（或 None）。
    """
    try:
        from storage_layer import StorageFactory, StorageType, resolve_storage_type
        return StorageFactory.get_instance(resolve_storage_type())
    except Exception as e:
        logger.warning('[SyncBridge] 获取容器中心存储失败: %s', e)
    return None


# ════════════════════════════════════════
# 同步消息队列（8008桥接自带重试）
# ════════════════════════════════════════

def _enqueue_sync(data: dict, flow_type: str = '') -> int:  # 修补 T8 (F8.1)
    """入队 steel_belt.sync_queue，立即返回。重复数据跳过并记录日志。

    Args:
        data: 同步数据 (含 order_no/step_name/quantity/operator/process_code)
        flow_type: 透传的 flow_type (D3.1 5 种之一, 默认 '' 与 T1 DDL 对齐)
    """
    # 修补 T8 (F8.1): 显式优先 + status_key 推断
    effective_flow_type = _resolve_sync_flow_type(
        flow_type, data.get('status_key', '') or data.get('step_name', '')
    )
    if effective_flow_type:
        # 不写 sync_queue (D-T8.2 SQL 越界), 仅日志记录便于调试
        logger.debug('[SyncBridge] _enqueue_sync flow_type=%s order_no=%s step_name=%s',
                     effective_flow_type, data.get('order_no'), data.get('step_name'))
    conn = _get_mysql_connection()
    try:
        with conn.cursor() as c:
            # 先查重，避免唯一键冲突
            c.execute('''SELECT id FROM sync_queue
                         WHERE order_no=%s AND step_name=%s AND operator=%s
                         AND status IN ('pending','retry')''',
                      (data['order_no'], data['step_name'], data.get('operator', '')))
            existing = c.fetchone()
            if existing:
                logger.warning('[SyncBridge] 重复同步任务跳过: order_no=%s step_name=%s operator=%s',
                               data['order_no'], data['step_name'], data.get('operator', ''))
                return existing['id']

            c.execute('''INSERT INTO sync_queue (order_no,step_name,quantity,operator,process_code,status)
                         VALUES (%s,%s,%s,%s,%s,'pending')''',
                      (data['order_no'], data['step_name'],
                       float(data.get('quantity', 0) or 0),
                       data.get('operator', ''), data.get('process_code', '')))
            qid = c.lastrowid
            conn.commit()
            return qid
    finally:
        conn.close()


def _dequeue_sync(limit=5):
    """取待处理的同步任务"""
    conn = _get_mysql_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM sync_queue WHERE status IN ('pending','retry') "
                      "ORDER BY retry_count ASC, enqueued_at ASC LIMIT %s", (limit,))
            return c.fetchall()
    finally:
        conn.close()


def _mark_sync_done(qid):
    conn = _get_mysql_connection()
    try:
        with conn.cursor() as c:
            c.execute("UPDATE sync_queue SET status='completed',processed_at=NOW() WHERE id=%s", (qid,))
            conn.commit()
    finally:
        conn.close()


def _mark_sync_failed(qid, error, retry_count):
    conn = _get_mysql_connection()
    try:
        with conn.cursor() as c:
            if retry_count >= 3:
                c.execute("UPDATE sync_queue SET status='failed',retry_count=%s,last_error=%s WHERE id=%s",
                          (retry_count, str(error)[:500], qid))
            else:
                backoff = 30 * (2 ** (retry_count - 1)) if retry_count > 0 else 5
                c.execute("UPDATE sync_queue SET status='retry',retry_count=%s,last_error=%s,"
                          "enqueued_at=DATE_ADD(NOW(), INTERVAL %s SECOND) WHERE id=%s",
                          (retry_count, str(error)[:500], backoff, qid))
            conn.commit()
    finally:
        conn.close()


def _sync_queue_worker(stop_event):
    """后台线程：消费 sync_queue"""
    import time
    logger.info('[SyncQueue] Worker 启动')
    while not stop_event.is_set():
        try:
            items = _dequeue_sync(5)
            for item in items:
                qid = item['id']
                try:
                    sync_sub_step_report(
                        item['order_no'], item['step_name'], item['operator'],
                        float(item.get('quantity', 0) or 0), process_code=item.get('process_code',''))
                    _mark_sync_done(qid)
                    logger.info('[SyncQueue] OK qid=%s %s/%s', qid, item['order_no'], item['step_name'])
                except Exception as e:
                    logger.warning('[SyncQueue] FAIL qid=%s %s/%s retry=%s err=%s',
                                   qid, item['order_no'], item['step_name'], item['retry_count'], e)
                    _mark_sync_failed(qid, e, (item['retry_count'] or 0) + 1)
        except Exception as e:
            logger.error('[SyncQueue] Worker异常: %s', e)
        time.sleep(10)


def _sync_to_container_db(order_no, status_key, plan_start=None, plan_end=None, schedule_days=None):
    """同步工单状态到 container_center.process_records — 直连 MySQL，不依赖 StorageFactory"""
    conn = None
    try:
        from core.db import get_direct_connection
        conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
        with conn.cursor() as c:
            # 更新 process_records 状态
            updates = ['status=%s', 'updated_at=NOW()']
            params = [status_key]
            if plan_start:
                updates.append('plan_start=%s')
                params.append(plan_start)
            if plan_end:
                updates.append('plan_end=%s')
                params.append(plan_end)
            # 修补 T9 (F9.1): 写入 flow_type 列 (T1 DDL 加的列 + idx_pr_flow 索引)
            flow_type_value = _resolve_sync_flow_type('', status_key)
            if flow_type_value:
                updates.append('flow_type=%s')
                params.insert(-1, flow_type_value)  # 插在 order_no 之前 (params 末尾是 WHERE 条件值)
            params.append(order_no)
            c.execute(f"UPDATE process_records SET {', '.join(updates)} WHERE order_no=%s", params)
            conn.commit()
            if c.rowcount > 0:
                logger.info('[SyncBridge->容器中心] 工单 %s 状态更新为 %s', order_no, status_key)
            else:
                logger.warning('[SyncBridge->容器中心] 未找到工单 %s 的记录', order_no)
    except Exception as e:
        logger.warning('[SyncBridge->容器中心] 同步失败: %s', e)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _sync_to_mysql(order_no, mysql_status, plan_start=None, plan_end=None):
    if not mysql_status:
        logger.warning('[SyncBridge->MySQL] 未识别的状态，跳过')
        return
    conn = None
    try:
        conn = _get_mysql_connection()
        c = conn.cursor()
        c.execute("SELECT id, status, order_id FROM production_orders WHERE order_no=%s", (order_no,))
        po = c.fetchone()
        if po:
            if po['status'] != mysql_status:
                if plan_start and plan_end:
                    c.execute(
                        "UPDATE production_orders SET status=%s, plan_start=%s, plan_end=%s, actual_start=COALESCE(actual_start, NOW()), updated_at=NOW() WHERE id=%s",
                        (mysql_status, plan_start, plan_end, po['id'])
                    )
                else:
                    c.execute(
                        "UPDATE production_orders SET status=%s, updated_at=NOW() WHERE id=%s",
                        (mysql_status, po['id'])
                    )
                logger.info('[SyncBridge->MySQL] production_orders %s: status=%s', order_no, mysql_status)
            if po.get('order_id'):
                c.execute("SELECT id, status FROM orders WHERE id=%s", (po['order_id'],))
                o = c.fetchone()
                if o and o['status'] != mysql_status:
                    c.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s", (mysql_status, o['id']))
                    logger.info('[SyncBridge->MySQL] orders %s: status=%s', order_no, mysql_status)
        else:
            c.execute("SELECT id, order_no, status FROM orders WHERE order_no=%s", (order_no,))
            o = c.fetchone()
            if o and o['status'] != mysql_status:
                c.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s", (mysql_status, o['id']))
                logger.info('[SyncBridge->MySQL] orders %s: status=%s (直接更新)', order_no, mysql_status)
        conn.commit()
    except Exception as e:
        logger.warning('[SyncBridge->MySQL] 同步失败: %s', e)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def sync_status_change(order_no, status_key, plan_start=None, plan_end=None, schedule_days=None, source='sync_bridge', flow_type=''):  # 修补 T8 (F8.2)
    if not order_no:
        logger.warning('[SyncBridge] 缺少订单号，跳过同步')
        return
    # 修补 T8 (F8.2): 显式 flow_type 优先, status_key 推断兜底
    effective_flow_type = _resolve_sync_flow_type(flow_type, status_key)
    if effective_flow_type:
        logger.debug('[SyncBridge] sync_status_change flow_type=%s order_no=%s status_key=%s',
                     effective_flow_type, order_no, status_key)
    mysql_status = STATUS_KEY_TO_MYSQL.get(status_key)
    _sync_to_container_db(order_no, status_key, plan_start, plan_end, schedule_days)
    _sync_to_mysql(order_no, mysql_status, plan_start, plan_end)
    logger.info('[SyncBridge] 工单 %s 同步完成: key=%s, mysql=%s, source=%s',
                order_no, status_key, mysql_status, source)


def sync_sub_step_report(order_no, step_name, operator, quantity,
                          qualified_qty=None, equipment_name='', remark='', overtime_hours=0, operator_id='', wechat_userid='', process_code='', flow_type=''):  # 修补 T8 (F8.3)
    """同步报工数据到 steel_belt.process_sub_steps + 更新 process_records 进度"""
    if not order_no or not step_name or quantity <= 0:
        logger.warning('[SyncBridge] 参数无效: order_no=%s step_name=%s qty=%s', order_no, step_name, quantity)
        return
    # 修补 T8 (F8.3): 显式 flow_type 优先, step_name 推断兜底 (报工 → quality)
    effective_flow_type = _resolve_sync_flow_type(
        flow_type, step_name if 'qc' in step_name.lower() else ''
    )
    if effective_flow_type:
        logger.debug('[SyncBridge] sync_sub_step_report flow_type=%s order_no=%s step_name=%s',
                     effective_flow_type, order_no, step_name)
    conn = None
    try:
        conn = _get_mysql_connection()
        c = conn.cursor()

        from core.config import get_process_code
        _process_code = process_code or get_process_code(step_name) or step_name

        # 通过 production_orders 找 process_records
        c.execute('''
            SELECT pr.id, pr.production_id
            FROM process_records pr
            INNER JOIN production_orders po ON pr.production_id = po.id
            WHERE po.order_no = %s AND pr.process_code = %s
            LIMIT 1
        ''', (order_no, _process_code))
        row = c.fetchone()
        if row:
            mysql_process_id = row['id']
            mysql_production_id = row['production_id']
        else:
            logger.warning('[SyncBridge] process_record 不存在: order_no=%s code=%s，无法写入子步骤',
                           order_no, _process_code)
            return

        batch_no = f'SHP-{datetime.now().strftime("%Y%m%d")}-{uuid.uuid4().hex[:8].upper()}'
        record_date = datetime.now().strftime('%Y-%m-%d')
        qty = float(quantity)
        qual_qty = float(qualified_qty) if qualified_qty is not None else qty

        # 查操作员
        mysql_operator_id = 0
        mysql_wechat_userid = wechat_userid or ''
        if operator:
            try:
                c.execute("SELECT id, wechat_userid FROM operators WHERE name = %s LIMIT 1", (operator,))
                op_row = c.fetchone()
                if op_row:
                    mysql_operator_id = op_row['id']
                    mysql_wechat_userid = mysql_wechat_userid or op_row.get('wechat_userid', '') or ''
            except Exception:
                pass

        now = datetime.now()
        # [F6 v4.0 标注] 本处为 dispatch_center 事件流专用写入路径，
        # 故意绕过 save_process_sub_step 的"3 键去重 + operator 追加"逻辑。
        # 原因：事件流来自调度中心的"实际扫码报工"动作，每条事件都对应一次完整的
        # 物理报工（不同 batch_no、不同 record_date），应当被全量记录用于追溯；
        # 而 v4.0 的去重逻辑仅适用于"派工"语义（一个工序可派给多个人），两者职责不同。
        c.execute('''
            INSERT INTO process_sub_steps
            (uuid, process_id, process_record_id, order_no, step_name, batch_no,
             quantity, qualified_qty, operator, operator_id, wechat_userid,
             equipment_name, remark, record_date, source,
             overtime_hours, synced, synced_at, created_at, updated_at, created_by, updated_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            str(uuid.uuid4()),
            mysql_process_id,
            mysql_process_id,           # process_record_id = process_id
            order_no,
            step_name,
            batch_no,
            qty, qual_qty,
            operator,
            mysql_operator_id,
            mysql_wechat_userid,
            equipment_name or '',
            remark or '',
            record_date,
            'dispatch_center',
            overtime_hours,
            1, now, now, now,
            operator or '',
            operator or '',
        ))

        # 更新 process_records 工序进度
        planned_qty = 0
        if mysql_process_id > 0:
            try:
                c.execute("SELECT planned_qty FROM process_records WHERE id = %s", (mysql_process_id,))
                proc_row = c.fetchone()
                if proc_row:
                    planned_qty = float(proc_row.get('planned_qty', 0) or 0)
            except Exception:
                planned_qty = 0

            c.execute('''
                SELECT SUM(quantity) as total_qty, SUM(qualified_qty) as total_qualified,
                       SUM(overtime_hours) as total_hours
                FROM process_sub_steps
                WHERE process_id = %s AND step_name = %s AND (is_deleted = 0 OR is_deleted IS NULL)
            ''', (mysql_process_id, step_name))
            summary = c.fetchone()
            total_qty = float(summary['total_qty'] or 0) if summary else 0
            total_qualified = float(summary['total_qualified'] or 0) if summary else 0
            total_hours = float(summary['total_hours'] or 0) if summary else 0

            # 判断状态：完成量 >= 计划量 则为 completed，否则为 in_progress
            new_status = 'completed' if total_qty >= planned_qty and planned_qty > 0 else 'in_progress'

            # 更新 process_records 的 completed_qty、qualified_qty、work_hours（含审计字段）
            # 修补 T9 (F9.2): 写入 flow_type 列 (显式 flow_type 优先, step_name 推断兜底)
            _ft = flow_type or infer_step_name_to_flow_type(step_name)
            _ft = _ft or 'production'  # 兜底 (T1 NOT NULL DEFAULT '', 但同步时已知应写有值)
            c.execute('''
                UPDATE process_records
                SET completed_qty = %s, qualified_qty = %s, work_hours = %s,
                    status = %s, flow_type = %s, updated_at = NOW(), updated_by = %s
                WHERE id = %s
            ''', (total_qty, total_qualified, total_hours, new_status, _ft, operator or '', mysql_process_id))
            logger.info('[SyncBridge->MySQL] 更新工序进度: process_id=%s, step_name=%s, planned=%s, completed=%s, qualified=%s, hours=%s, status=%s, operator=%s',
                       mysql_process_id, step_name, planned_qty, total_qty, total_qualified, total_hours, new_status, operator)

        conn.commit()
        logger.info('[SyncBridge->MySQL] 报工同步成功: order_no=%s, process_id=%s, step_name=%s, qty=%s, operator=%s, batch_no=%s',
                    order_no, mysql_process_id, step_name, qty, operator, batch_no)

    except Exception as e:
        import traceback
        with open(r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\logs\bridge_err.log', 'a', encoding='utf-8') as _ef:
            _ef.write(f'[{datetime.now().isoformat()}] sync FAIL: {e}\n{traceback.format_exc()}\n')
        logger.warning('[SyncBridge->MySQL] 报工同步失败: %s', e)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


@sync_bp.route('/sub-step-report', methods=['POST'])
def api_sync_sub_step_report():
    body = request.get_json(silent=True)
    if body is None:
        logger.warning('[SyncBridge] JSON 解析失败: %s | Content-Type: %s | Data: %s',
                      request.content_type, request.data[:200] if request.data else 'empty')
        return jsonify({'code': 1201, 'message': '请求体必须是有效的 JSON 对象'})
    order_no = body.get('order_no', '') or ''
    step_name = body.get('step_name', '') or ''
    process_code = body.get('process_code', '') or ''
    operator = body.get('operator', '') or ''
    operator_id = body.get('operator_id', '') or ''
    wechat_userid = body.get('wechat_userid', '') or ''
    quantity_raw = body.get('quantity')
    if quantity_raw is None:
        quantity = 0.0
    else:
        try:
            quantity = float(quantity_raw)
        except (TypeError, ValueError):
            logger.warning('[SyncBridge] quantity 格式错误: %s', quantity_raw)
            return jsonify({'code': 1202, 'message': 'quantity 必须是数字'})
    qualified_qty = body.get('qualified_qty')
    equipment_name = body.get('equipment_name', '') or ''
    remark = body.get('remark', '') or ''
    overtime_hours_raw = body.get('overtime_hours')
    if overtime_hours_raw is None:
        overtime_hours = 0.0
    else:
        try:
            overtime_hours = float(overtime_hours_raw)
        except (TypeError, ValueError):
            overtime_hours = 0.0
    # 修补 T8 (F8.4): 接受 request body flow_type
    flow_type = body.get('flow_type', '') or ''
    if not order_no or not step_name or quantity <= 0:
        return jsonify({'code': 1001, 'message': '参数不完整: order_no, step_name, quantity 必填'})
    # 入队代替开线程——队列 worker 自动消费+重试
    qid = _enqueue_sync({
        'order_no': order_no, 'step_name': step_name, 'quantity': quantity,
        'operator': operator, 'process_code': process_code,
    }, flow_type=flow_type)  # 修补 T8 (F8.4) 透传
    return jsonify({'code': 0, 'message': '报工同步已入队', 'queue_id': qid})


@sync_bp.route('/status-change', methods=['POST'])
def api_sync_status_change():
    body = request.get_json(silent=True)
    if body is None:
        logger.warning('[SyncBridge] /status-change JSON 解析失败: %s | Data: %s',
                      request.content_type, request.data[:200] if request.data else 'empty')
        return jsonify({'code': 1201, 'message': '请求体必须是有效的 JSON 对象'})
    order_no = body.get('order_no', '') or ''
    status_key = body.get('status_key', '') or ''
    plan_start = body.get('plan_start')
    plan_end = body.get('plan_end')
    schedule_days = body.get('schedule_days')
    source = body.get('source', 'http_api')
    # 修补 T8 (F8.4): 接受 request body flow_type
    flow_type = body.get('flow_type', '') or ''
    if not order_no or not status_key:
        return jsonify({'code': 1001, 'message': '缺少 order_no 或 status_key'})
    threading.Thread(
        target=sync_status_change,
        args=(order_no, status_key),
        kwargs={'plan_start': plan_start, 'plan_end': plan_end,
                'schedule_days': schedule_days, 'source': source,
                'flow_type': flow_type},  # 修补 T8 (F8.4) 透传
        daemon=True
    ).start()
    return jsonify({'code': 0, 'message': '同步请求已提交'})


# ========== 质量报告同步 ==========

REQUIRED_FIELDS = ['order_no', 'inspection_type', 'process_name', 'overall_result']

def _validate_body(body):
    for f in REQUIRED_FIELDS:
        if not body.get(f):
            return False, f'{f} 必填'
    order_no = body.get('order_no', '')
    if not isinstance(order_no, str) or len(order_no) > 64:
        return False, 'order_no 格式错误'
    items = body.get('items')
    if items is not None and not isinstance(items, list):
        return False, 'items 必须是数组'
    return True, 'ok'


@sync_bp.route('/quality-report', methods=['POST'])
def api_sync_quality_report():
    body = request.get_json(silent=True)
    if body is None:
        raw = request.get_data()
        if raw:
            try: body = json.loads(raw.decode('utf-8'))
            except Exception: body = {}

    ok, err = _validate_body(body)
    if not ok:
        return jsonify({'code': 1001, 'message': err})

    msg_id = body.get('msg_id', '')
    if msg_id:
        conn = _get_mysql_connection()
        try:
            cur = conn.cursor()
            cur.execute("INSERT IGNORE INTO idempotency_keys (msg_id) VALUES (%s)", (msg_id,))
            conn.commit()
            if cur.rowcount == 0:
                conn.close()
                return jsonify({'code': 0, 'message': 'duplicate skipped'})
        finally:
            conn.close()

    try:
        action = body.get('action', 'submit')
        # 修补 T8 (F8.4): 接受 request body flow_type
        flow_type = body.get('flow_type', '') or ''
        # 质检路由固定为 quality (action submit/rework/review 都是质检)
        if not flow_type:
            flow_type = 'quality'
        if flow_type:
            logger.debug('[SyncBridge] api_sync_quality_report flow_type=%s order_no=%s action=%s',
                         flow_type, body.get('order_no'), action)
        if action in ('submit', 'rework'):
            _sync_quality_to_mysql(body)
        elif action == 'review':
            _sync_quality_review_to_mysql(body)
        return jsonify({'code': 0, 'message': 'ok'})
    except Exception as e:
        logger.error('[SyncBridge] 质量同步失败: %s', e)
        if msg_id:
            try:
                conn = _get_mysql_connection()
                conn.cursor().execute("DELETE FROM idempotency_keys WHERE msg_id=%s", (msg_id,))
                conn.commit()
                conn.close()
            except Exception:
                pass
        return jsonify({'code': 500, 'message': str(e)}), 500


def _sync_quality_to_mysql(data: dict):
    _t0 = time.time()
    conn = _get_mysql_connection()
    try:
        cur = conn.cursor()
        cur.execute("START TRANSACTION")
        cur.execute(
            "SELECT id FROM quality_records WHERE order_no=%s AND inspection_type=%s "
            "AND process_name=%s ORDER BY id DESC LIMIT 1 FOR UPDATE",
            (data['order_no'], data.get('inspection_type',''), data.get('process_name','')))
        existing = cur.fetchone()

        items_json = json.dumps(data.get('items', []), ensure_ascii=False)
        items = data.get('items', [])
        ono = data['order_no']; itype = data.get('inspection_type',''); pname = data.get('process_name','')

        if existing:
            cur.execute("DELETE FROM quality_record_items WHERE record_id=%s", (existing['id'],))
            cur.execute(
                "UPDATE quality_records SET result=%s, inspector=%s, inspection_items=%s, "
                "defect_description=%s, review_status='', rework_version=rework_version+1, "
                "record_date=NOW() WHERE id=%s",
                (data['overall_result'], data.get('inspector',''), items_json,
                 data.get('defect_description',''), existing['id']))
            steel_id = existing['id']
        else:
            try:
                cur.execute(
                    "INSERT INTO quality_records (order_no, inspection_type, process_name, "
                    "inspector, inspection_items, result, defect_description, review_status, "
                    "record_date) VALUES (%s,%s,%s,%s,%s,%s,%s,'',NOW())",
                    (ono, itype, pname, data.get('inspector',''), items_json,
                     data['overall_result'], data.get('defect_description','')))
                steel_id = cur.lastrowid
            except Exception:
                cur.execute("ROLLBACK")
                cur.execute("START TRANSACTION")
                cur.execute(
                    "SELECT id FROM quality_records WHERE order_no=%s AND inspection_type=%s "
                    "AND process_name=%s ORDER BY id DESC LIMIT 1 FOR UPDATE",
                    (ono, itype, pname))
                existing2 = cur.fetchone()
                cur.execute("DELETE FROM quality_record_items WHERE record_id=%s", (existing2['id'],))
                cur.execute(
                    "UPDATE quality_records SET result=%s, inspector=%s, inspection_items=%s, "
                    "defect_description=%s, review_status='', rework_version=rework_version+1, "
                    "record_date=NOW() WHERE id=%s",
                    (data['overall_result'], data.get('inspector',''), items_json,
                     data.get('defect_description',''), existing2['id']))
                steel_id = existing2['id']

        for it in items:
            cur.execute(
                "INSERT INTO quality_record_items (record_id, inspection_item, "
                "measured_value, standard_value, tolerance, is_passed) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (steel_id, it.get('inspection_item',''), it.get('measured_value',''),
                 it.get('standard_value',''), it.get('tolerance',''),
                 1 if it.get('is_passed', True) else 0))

        conn.commit()
        _elapsed = int((time.time() - _t0) * 1000)
        logger.info('[quality-sync] order=%s type=%s proc=%s action=%s items=%d ms=%d',
                    data['order_no'], data.get('inspection_type'), data.get('process_name'),
                    data.get('action','submit'), len(data.get('items',[])), _elapsed)
    except Exception:
        conn.rollback()
        logger.error('[quality-sync] FAIL order=%s ms=%d',
                     data['order_no'], int((time.time() - _t0) * 1000))
        raise
    finally:
        conn.close()


def _sync_quality_review_to_mysql(data: dict):
    conn = _get_mysql_connection()
    try:
        cur = conn.cursor()
        cur.execute("START TRANSACTION")
        cur.execute(
            "UPDATE quality_records SET review_status=%s, reviewed_at=NOW() "
            "WHERE order_no=%s",
            (data.get('action',''), data['order_no']))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@sync_bp.route('/sync-process', methods=['POST'])
def api_sync_process():
    """同步容器中心报工数据到 MySQL process_records（MySQL→MySQL 桥接）"""
    import json

    try:
        cc_conn = _get_container_conn()
        cur = cc_conn.cursor()

        # 读取 process_report 类型的 data_packages(旧值 'report' 已迁移)
        cur.execute("SELECT * FROM data_packages WHERE data_type='process_report' ORDER BY id DESC LIMIT 20")
        packages = cur.fetchall()
        cc_conn.close()

        if not packages:
            return jsonify({'code': 0, 'message': '无待同步报工数据', 'synced': 0})
        
        mysql_conn = _get_mysql_connection()
        mc = mysql_conn.cursor()
        synced = 0
        
        for pkg in packages:
            content = json.loads(pkg.get('content', '{}')) if isinstance(pkg.get('content'), str) else (pkg.get('content') or {})
            quantity = content.get('quantity', 0)
            remark = content.get('remark', '') or pkg.get('title', '')

            _order_no = content.get('order_no', '') or pkg.get('related_order', '')
            _process_code = content.get('process_code', '')
            if not _process_code:
                _pname = content.get('process_name', '') or pkg.get('related_process', '')
                if _pname:
                    from core.config import get_process_code
                    _process_code = get_process_code(_pname)

            # 修补 T8 (F8.4): 推断 flow_type (process_report → production)
            _pkg_flow_type = pkg.get('flow_type', '') or _resolve_sync_flow_type('', 'in_production')
            if _pkg_flow_type:
                logger.debug('[SyncBridge] api_sync_process flow_type=%s order_no=%s pkg_id=%s',
                             _pkg_flow_type, _order_no, pkg.get('id'))

            if _order_no and _process_code:
                mc.execute("SELECT id FROM orders WHERE order_no=%s LIMIT 1", (_order_no,))
                _orow = mc.fetchone()
                if _orow:
                    _order_id = _orow[0]
                    mc.execute(
                        "UPDATE process_records SET completed_qty = completed_qty + %s, device_remark=%s, updated_at=NOW() WHERE order_id=%s AND process_code=%s",
                        (quantity, remark, _order_id, _process_code)
                    )
                    if mc.rowcount > 0:
                        synced += 1
                logger.info(f'[SyncBridge] 同步报工: order_no={_order_no} process_code={_process_code} qty={quantity}')
        
        mysql_conn.commit()
        mysql_conn.close()
        return jsonify({'code': 0, 'message': f'同步完成', 'synced': synced})
        
    except Exception as e:
        logger.error(f'[SyncBridge] 同步报工失败: {e}', exc_info=True)
        return jsonify({'code': 500, 'message': str(e)})


# ════════════════════════════════════════
# 报工确认收口 (TASK-7 新增, 5003 /report/confirm 走本端点)
# ════════════════════════════════════════

@sync_bp.route('/report-confirm', methods=['POST'])
def api_sync_report_confirm():
    """报工确认收口 — 落 MySQL report_request 表 (TASK-7)
    ---
    Request:
        order_no    (str, 必填)
        operator_id (str, 必填)
        confirmed   (bool, 必填)
        remark      (str, 可选)
    Response:
        {code: 0, message: 'ok', data: {request_id, confirmed_at, order_no}}
    Source:
        5003 /api/sync/report/confirm → bridge.sync_client.send('report-confirm', payload)
    """
    try:
        body = request.get_json(silent=True) or {}
        order_no = str(body.get('order_no', '')).strip()
        operator_id = str(body.get('operator_id', '')).strip()
        confirmed = bool(body.get('confirmed', False))
        remark = str(body.get('remark', '')).strip()
        timestamp = str(body.get('timestamp', '') or datetime.now().isoformat())
        # 修补 T8 (F8.4): 接受 request body flow_type (报工确认 → report_complete → quality)
        flow_type = body.get('flow_type', '') or _resolve_sync_flow_type('', 'report_complete')
        if flow_type:
            logger.debug('[SyncBridge] api_sync_report_confirm flow_type=%s order_no=%s op=%s confirmed=%s',
                         flow_type, order_no, operator_id, confirmed)

        if not order_no or not operator_id:
            return jsonify({'code': 1001, 'message': 'order_no/operator_id 必填'}), 200

        # 幂等: 同一 order_no+operator_id 5 分钟内同 confirmed 视为重复, 跳过
        conn = _get_mysql_connection()
        try:
            with conn.cursor() as c:
                c.execute(
                    """SELECT id, confirmed, created_at FROM report_request
                       WHERE order_no=%s AND operator_id=%s
                         AND created_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                       ORDER BY id DESC LIMIT 1""",
                    (order_no, operator_id)
                )
                recent = c.fetchone()
                if recent and bool(recent.get('confirmed')) == confirmed:
                    logger.info('[SyncBridge] /report-confirm 幂等跳过: order_no=%s op=%s confirmed=%s',
                                order_no, operator_id, confirmed)
                    return jsonify({
                        'code': 0,
                        'message': 'duplicate skipped',
                        'data': {
                            'request_id': f"REQ-{order_no}-{int(time.time())}",
                            'confirmed_at': str(recent.get('created_at', timestamp)),
                            'order_no': order_no,
                            'duplicate': True,
                        }
                    })

                c.execute(
                    """INSERT INTO report_request
                       (order_no, operator_id, confirmed, remark, created_at, source)
                       VALUES (%s,%s,%s,%s,%s,'dispatch_center_5003')""",
                    (order_no, operator_id, 1 if confirmed else 0, remark, timestamp)
                )
                new_id = c.lastrowid
                conn.commit()
                logger.info('[SyncBridge] /report-confirm OK: id=%s order_no=%s op=%s confirmed=%s',
                            new_id, order_no, operator_id, confirmed)
                return jsonify({
                    'code': 0,
                    'message': 'ok',
                    'data': {
                        'request_id': f"REQ-{new_id}",
                        'confirmed_at': timestamp,
                        'order_no': order_no,
                    }
                })
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        logger.exception('[SyncBridge] /report-confirm 异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500
