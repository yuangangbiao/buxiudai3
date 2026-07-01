# -*- coding: utf-8 -*-
"""
报工模块 - 从容器中心读取任务，提交报工（MySQL 迁移版）
"""
import logging
import json, os
from datetime import datetime
from flask import Blueprint, request
from .decorators import success, fail

logger = logging.getLogger(__name__)
bp = Blueprint('process', __name__, url_prefix='/api/process')


def _get_cc():
    """获取容器中心实例（延迟初始化）"""
    from container_center_v5 import ContainerCenter
    return ContainerCenter()


class CCAdapter:
    """适配器：将 ContainerCenter.storage 包装为 sqlite3 游标兼容接口"""
    def __init__(self):
        self._cc = _get_cc()
        self._conn = self._cc._conn
        self._rows = []

    def execute(self, sql, params=None):
        c = self._conn.cursor()
        c.execute(sql, params or ())
        self._rows = c.fetchall()
        return self

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def close(self):
        pass


@bp.route('/my-tasks', methods=['GET'])
def my_tasks():
    worker_id = request.args.get('worker_id', 'OP001')
    try:
        cur = CCAdapter()
        # dispatch_commands 表已删除，直接读 data_packages
        cur.execute("""
            SELECT id, title, content, data_type FROM data_packages
            WHERE data_type IN ('report','task','work_order')
            ORDER BY id DESC LIMIT 20
        """)
        rows = cur.fetchall()
        
        task_list = []
        for r in rows:
            content = json.loads(r['content']) if isinstance(r.get('content'), str) else (r.get('content') or {})
            task_list.append({
                'process_id': r['pkg_id'] if 'pkg_id' in r.keys() else r['id'],
                'process_name': content.get('process_name', r['title'] or '未知工序'),
                'order_no': content.get('order_no', ''),
                'customer_name': content.get('customer_name', ''),
                'product_type': content.get('product_type', ''),
                'planned_qty': content.get('planned_qty', content.get('quantity', 0)),
                'completed_qty': content.get('completed_qty', 0),
                'status': content.get('status', '进行中'),
                'order_no': content.get('order_no', ''),
            })
        cur.close()
        return success(data={'tasks': task_list, 'total': len(task_list)})
    except Exception as e:
        logger.exception("my_tasks error")
        return fail(message=str(e))


@bp.route('/<int:record_id>/report', methods=['POST'])
def report_progress(record_id):
    print(f"[DEBUG-NEW] report_progress called with id={record_id}", flush=True)
    body = request.get_json(silent=True)
    if body is None and request.data:
        import json as _json
        try:
            body = _json.loads(request.data.decode('utf-8'))
        except Exception:
            body = request.form.to_dict() if request.form else {}
    if not body:
        return fail(message="请求体必须是有效的JSON对象", code=400)
    
    qty = body.get('quantity', 0)
    qualified = body.get('qualified', 0)
    hours = body.get('hours', 0)
    remark = body.get('remark', '')
    worker = body.get('worker', '')
    
    try:
        cc = _get_cc()
        cur = CCAdapter()
        
        # 读取当前包
        cur.execute("SELECT * FROM data_packages WHERE id=%s", (str(record_id),))
        pkg = cur.fetchone()
        if not pkg:
            return fail(message=f"任务 {record_id} 不存在")
        
        if not pkg:
            return fail(message=f"任务 {record_id} 不存在")
        
        content = json.loads(pkg['content']) if isinstance(pkg['content'], str) else (pkg['content'] or {})
        content['completed_qty'] = content.get('completed_qty', 0) + qty
        content['qualified_qty'] = content.get('qualified_qty', 0) + qualified
        content['work_hours'] = content.get('work_hours', 0) + hours
        if worker:
            content['worker'] = worker
        
        # 判断状态
        planned = content.get('planned_qty', 0)
        if content['completed_qty'] >= planned and planned > 0:
            content['status'] = '已完成'
        else:
            content['status'] = '进行中'
        
        # 更新容器中心
        cur.execute("UPDATE data_packages SET content=%s, title=%s, status=%s, updated_at=NOW() WHERE id=%s",
                    (json.dumps(content, ensure_ascii=False), f"{content.get('process_name','')}:{content['completed_qty']}/{planned}", content['status'], str(record_id)))
        
        # 记录同步日志
        cur.execute("INSERT INTO sync_logs (action, package_id, detail, created_at) VALUES (%s,%s,%s,%s)",
                    ('REPORT', str(record_id), f"报工+{qty} {remark}", datetime.now().isoformat()))
        conn.commit()
        cur.close()
        
        # 同时写入 MySQL（严格按 order_id + process_code 匹配）
        try:
            from core.db import get_direct_connection
            mc = get_direct_connection(
                host=os.getenv('MYSQL_HOST', 'localhost'),
                port=int(os.getenv('MYSQL_PORT', 3306)),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database=os.getenv('CONTAINER_MYSQL_DATABASE', 'container_center')
            )
            mcur = mc.cursor()
            
            _order_no = content.get('order_no', '') or pkg.get('related_order', '')
            _process_name = content.get('process_name', '') or pkg.get('related_process', '')
            _process_code = content.get('process_code', '')
            if not _process_code and _process_name:
                from core.config import get_process_code
                _process_code = get_process_code(_process_name)
            
            mcur.execute("SELECT id FROM orders WHERE order_no=%s LIMIT 1", (_order_no,))
            _orow = mcur.fetchone()
            if _orow and _process_code:
                _order_id = _orow[0]
                mcur.execute(
                    "UPDATE process_records SET completed_qty=completed_qty+%s, qualified_qty=qualified_qty+%s, status=%s, device_remark=%s WHERE order_id=%s AND process_code=%s",
                    (qty, qualified, content['status'], remark, _order_id, _process_code)
                )
                if mNone.rowcount == 0:
                    return fail(message=f'工序不存在: order_no={_order_no} process_code={_process_code}', code=404)
            else:
                return fail(message=f'工单或工序信息缺失: order_no={_order_no} process_code={_process_code}', code=404)
            mcur.execute(
                "UPDATE mobile_task_records SET completed_qty=completed_qty+%s, status=%s, device_remark=%s WHERE id=%s%s",
                (qty, content['status'], remark, record_id)
            )
            mc.commit()
            mc.close()
        except Exception as e:
            logger.warning(f"同步MySQL失败(可忽略): {e}")
        
        return success(message=f"报工成功: +{qty}", data=content)
    except Exception as e:
        logger.exception("report_progress error")
        return fail(message=str(e))


@bp.route('/history', methods=['GET'])
def history():
    worker_id = request.args.get('worker_id', 'OP001')
    try:
        cc = _get_cc()
        cur = CCAdapter()
        cur.execute("""
            SELECT sl.*, dp.title=%s FROM sync_logs sl
            LEFT JOIN data_packages dp ON sl.package_id = dp.id
            WHERE sl.action='REPORT'
            ORDER BY sl.created_at DESC LIMIT 50
        """)
        rows = cur.fetchall()
        records = []
        for r in rows:
            records.append({
                'id': r['id'],
                'process_name': r['title'] or '',
                'order_no': '',
                'completed_qty': 0,
                'report_time': r['created_at'] or '',
                'report_type': 'PROGRESS'
            })
        cur.close()
        return success(data={'records': records, 'total': len(records), 'page': 1, 'page_size': 20})
    except Exception as e:
        logger.exception("history error")
        return fail(message=str(e))
