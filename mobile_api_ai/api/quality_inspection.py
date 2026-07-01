# -*- coding: utf-8 -*-
"""
手机端质检报工 API 蓝图 — 10 端点
"""
import json, logging, uuid, os
from datetime import datetime
from flask import Blueprint, request, jsonify
from models.database import get_connection_context
from models.quality import QualityDAO
from models.quality_rule import QualityRuleDAO

logger = logging.getLogger('quality_inspection')
bp = Blueprint('quality_inspection', __name__, url_prefix='/api/quality-inspection')

QUALITY_FLOW = [
    {'key': 'quality_received',  'label': '接收任务'},
    {'key': 'quality_measured',  'label': '逐项检测'},
    {'key': 'quality_reported',  'label': '提交报告'},
    {'key': 'quality_reviewed',  'label': '审核确认'},
    {'key': 'completed',         'label': '完成'},
]

INSPECTION_TYPES = ['首检', '巡检', '终检']
INSPECTION_RESULTS = ['合格', '不合格', '待复检']
HANDLING_METHODS = ['返工', '降级使用', '报废', '特采放行', '无']

# ====== 本地 DAO（直连 container_center，不依赖 steel_belt） ======
def _cc_qr():
    """返回 container_center.quality_records 的 db + cursor（DictCursor）"""
    from models.database import get_connection_context
    class DictCtx:
        def __init__(self, ctx):
            self._ctx = ctx
            self._conn = None
        def __enter__(self):
            self._conn = self._ctx.__enter__()
            return self._conn
        def __exit__(self, *a):
            return self._ctx.__exit__(*a)
        def cursor(self):
            return self._conn.cursor(pymysql.cursors.DictCursor)
    return DictCtx(get_connection_context())

def _qc_create_full(order_no, inspection_type, process_name, inspector, items, overall_result, defect_description='', defect_qty=0, handling_method='', status='quality_reported'):
    with _cc_qr() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO container_center.quality_records (order_no,inspection_type,process_name,inspector,inspection_items,result,defect_description,defect_qty,handling_method,review_status,rework_version,status,record_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())",
            (order_no, inspection_type, process_name, inspector, json.dumps(items, ensure_ascii=False), overall_result, defect_description, defect_qty, handling_method, '', 0, status))
        rid = cursor.lastrowid
        for it in items:
            cursor.execute(
                "INSERT INTO container_center.quality_record_items (record_id,inspection_item,measured_value,standard_value,tolerance,is_passed) VALUES (%s,%s,%s,%s,%s,%s)",
                (rid, it.get('inspection_item',''), it.get('measured_value',''), it.get('standard_value',''), it.get('tolerance',''), 1 if it.get('is_passed', True) else 0))
        conn.commit()
        return rid

def _qc_get(record_id):
    with _cc_qr() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM container_center.quality_records WHERE id=%s", (record_id,))
        return cursor.fetchone()

def _qc_get_items(record_id):
    with _cc_qr() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM container_center.quality_record_items WHERE record_id=%s ORDER BY id", (record_id,))
        return cursor.fetchall()

def _qc_get_all(limit=50):
    with _cc_qr() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM container_center.quality_records ORDER BY id DESC LIMIT %s", (limit,))
        return cursor.fetchall()

def _qc_get_timeline(order_no):
    with _cc_qr() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM container_center.quality_records WHERE order_no=%s ORDER BY rework_version", (order_no,))
        return cursor.fetchall()
# ================================================================


def _ok(**data):
    return jsonify({'code': 0, 'data': data})


def _fail(msg, code=400):
    return jsonify({'code': code, 'message': msg}), 400


def _json_field(row, field, default=None):
    """安全解析 JSON 字段"""
    v = row.get(field, default)
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return default
    if isinstance(v, dict):
        return {k: ('' if v2 is None else v2) for k, v2 in v.items()}
    return v or default


# ----------------------------------------------------------------
# 1. 质检任务列表
# ----------------------------------------------------------------
@bp.route('/tasks', methods=['GET'])
def task_list():
    try:
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 20))
        offset = (page - 1) * size

        with get_connection_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(DISTINCT related_order) as cnt FROM container_center.data_packages "
                "WHERE data_type = 'quality_task' "
                "AND related_order IS NOT NULL AND related_order != ''")
            total = cursor.fetchone()['cnt']
            cursor.execute(
                "SELECT related_order, COUNT(*) as task_cnt, "
                "MAX(created_at) as latest, MAX(status) as status "
                "FROM container_center.data_packages "
                "WHERE data_type = 'quality_task' "
                "AND related_order IS NOT NULL AND related_order != '' "
                "GROUP BY related_order ORDER BY latest DESC LIMIT %s OFFSET %s",
                (size, offset))
            rows = cursor.fetchall()

        tasks = []
        for r in rows:
            tasks.append({
                'id': r.get('related_order'),
                'order_no': r.get('related_order'),
                'task_count': r.get('task_cnt', 1),
                'status': r.get('status', 'pending'),
                'created_at': str(r.get('latest', '')),
            })
        return _ok(tasks=tasks, total=total, page=page, size=size)
    except Exception as e:
        logger.error('质检任务列表失败: %s', e, exc_info=True)
        return _fail(str(e), 500)


# ----------------------------------------------------------------
# 2. 订单详情（按工序分开，各自独立提交）
# ----------------------------------------------------------------
@bp.route('/tasks/<order_no>', methods=['GET'])
def task_detail(order_no):
    try:
        with get_connection_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM container_center.data_packages WHERE related_order=%s "
                "AND data_type = 'quality_task' "
                "ORDER BY created_at DESC",
                (order_no,))
            pkgs = cursor.fetchall()

        if not pkgs:
            return _fail('质检任务不存在', 404)

        processes = []
        all_statuses = []
        for pkg in pkgs:
            content = _json_field(pkg, 'content', {})
            items = content.get('inspection_items', [])
            if isinstance(items, str) and items.strip():
                names = [n.strip() for n in items.split(',') if n.strip()]
                items = [{
                    'category': content.get('process_name', '质检项'),
                    'items': [{'name': n, 'standard_value': '', 'tolerance': '无'} for n in names]
                }]
            processes.append({
                'pkg_id': pkg.get('id'),
                'inspection_type': content.get('inspection_type', ''),
                'process_name': content.get('process_name', ''),
                'inspection_items': items,
                'status': pkg.get('status', 'pending'),
                'submitted': pkg.get('status', 'pending') in ('quality_reported','quality_reviewed','completed'),
            })
            all_statuses.append(pkg.get('status', 'pending'))

        current_status = all_statuses[0] if all_statuses else 'pending'
        flow = []
        cur_idx = next((i for i, s in enumerate(QUALITY_FLOW) if s['key'] == current_status), 0)
        for i, step in enumerate(QUALITY_FLOW):
            st = 'completed' if i < cur_idx else ('active' if i == cur_idx else 'pending')
            flow.append({**step, 'status': st})

        return _ok(
            order_no=order_no,
            processes=processes,
            status=current_status,
            flow=flow,
        )
    except Exception as e:
        logger.error('质检任务详情失败: %s', e, exc_info=True)
        return _fail(str(e), 500)


# ----------------------------------------------------------------
# 3. 逐项判定
# ----------------------------------------------------------------
def _judge(standard, measured, tolerance):
    """公差判定引擎 — 与前端 JS 版逻辑一致"""
    if not measured or str(measured).strip() == '':
        return None
    sv = str(standard).strip()
    mv = str(measured).strip()
    if not tolerance or tolerance == '无':
        return mv == sv
    if tolerance.startswith('≥') or tolerance.startswith('≤'):
        try:
            num = float(tolerance[1:])
            mv_num = float(mv)
            return mv_num >= num if tolerance.startswith('≥') else mv_num <= num
        except (ValueError, TypeError):
            return None
    try:
        tv = float(tolerance.replace('±', ''))
        sv_num = float(sv)
        mv_num = float(mv)
        return sv_num - tv <= mv_num <= sv_num + tv
    except (ValueError, TypeError):
        return None


def _safe_body():
    """兼容 UTF-8/GBK 编码的 JSON body 解析"""
    data = request.get_json(silent=True)
    if data is not None:
        return data
    raw = request.get_data()
    if not raw:
        return {}
    try:
        return json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        try:
            return json.loads(raw.decode('gbk'))
        except Exception:
            return {}


@bp.route('/evaluate', methods=['POST'])
def evaluate():
    data = _safe_body()
    standard = data.get('standard_value', '')
    measured = data.get('measured_value', '')
    tolerance = data.get('tolerance', '')
    result = _judge(standard, measured, tolerance)
    return _ok(is_passed=result, measured=measured)


# ----------------------------------------------------------------
# 4. 提交报告
# ----------------------------------------------------------------
@bp.route('/submit', methods=['POST'])
def submit():
    data = _safe_body()
    pkg_id = data.get('task_id', '')
    order_no = data.get('order_no', '')
    inspector = data.get('inspector', '')
    if not order_no:
        return _fail('order_no 不能为空')

    items = data.get('items', [])
    overall_result = data.get('overall_result', '合格')
    judge_mode = data.get('judge_mode', 'record')
    defect_description = data.get('defect_description', '')
    defect_qty = data.get('defect_qty', 0)
    handling_method = data.get('handling_method', '')
    inspection_type = data.get('inspection_type', '')
    process_name = data.get('process_name', '')

    # 校验
    if not items:
        return _fail('检查项不能为空', 422)
    if overall_result == '不合格' and not defect_description:
        return _fail('存在不合格项，请填写不良描述', 422)

    try:
        # 写入 quality_records
        record_id = _qc_create_full(
            order_no=order_no,
            inspection_type=inspection_type,
            process_name=process_name,
            inspector=inspector,
            items=items,
            overall_result=overall_result,
            defect_description=defect_description,
            defect_qty=defect_qty,
            handling_method=handling_method,
            status='quality_reported',
        )

        # 原子锁 data_packages（兼容按 id / order_no+process_name）
        data_pkg_updated = False
        with get_connection_context() as conn:
            cursor = conn.cursor()
            if pkg_id:
                result = cursor.execute(
                    'UPDATE container_center.data_packages SET status=%s WHERE id=%s AND status != %s',
                    ('quality_reported', pkg_id, 'quality_reported'))
                if result == 0:
                    result = cursor.execute(
                        'UPDATE container_center.data_packages SET status=%s WHERE related_order=%s AND status != %s',
                        ('quality_reported', pkg_id, 'quality_reported'))
                if result > 0:
                    data_pkg_updated = True
            else:
                result = cursor.execute(
                    'UPDATE container_center.data_packages SET status=%s WHERE related_order=%s AND data_type=%s AND status NOT IN %s LIMIT 1',
                    ('quality_reported', order_no, 'quality_task', ('quality_reported', 'quality_reported')))
                if result > 0:
                    data_pkg_updated = True
        if pkg_id and not data_pkg_updated:
            return _fail('该任务已被提交，请刷新', 409)

        # Outbox
        with get_connection_context() as conn:
            cursor = conn.cursor()
            payload = json.dumps({
                'record_id': record_id,
                'order_no': order_no,
                'overall_result': overall_result,
                'judge_mode': judge_mode,
            }, ensure_ascii=False)
            cursor.execute(
                'INSERT INTO outbox (event_type, payload) VALUES (%s, %s)',
                ('quality_reported', payload))
            conn.commit()

        logger.info('质检报告已提交: record_id=%s order=%s result=%s',
                     record_id, order_no, overall_result)

        # 通知 8008 桥接（独立线程 + 重试 + 死信）
        import threading, time, uuid
        _payload = {'action':'submit','order_no':order_no,'inspection_type':inspection_type,
                    'process_name':process_name,'inspector':inspector,'items':items,
                    'overall_result':overall_result,'defect_description':defect_description or ''}
        t = threading.Thread(target=_notify_8008, args=(_payload,))
        t.daemon = False
        t.start()

        return _ok(record_id=record_id, status='quality_reported')
    except Exception as e:
        logger.error('提交质检报告失败: %s', e, exc_info=True)
        return _fail(str(e), 500)


# ----------------------------------------------------------------
# 5. 审核
# ----------------------------------------------------------------
@bp.route('/review', methods=['POST'])
def review():
    data = _safe_body()
    record_id = data.get('record_id')
    action = data.get('action', '')  # approved / rejected
    comment = data.get('comment', '')
    reviewer = data.get('reviewer', '')

    if not record_id or action not in ('approved', 'rejected'):
        return _fail('参数错误: record_id + action(approved/rejected) 必填')

    try:
        rec = _qc_get(record_id)
        if not rec:
            return _fail('质检记录不存在', 404)
        if rec.get('review_status') in ('approved', 'rejected'):
            return _fail('该报告已被审核，请勿重复操作', 409)

        with get_connection_context() as conn:
            cursor = conn.cursor()
            if action == 'approved':
                cursor.execute(
                    'UPDATE container_center.quality_records SET review_status=%s, reviewed_by=%s, reviewed_at=NOW(), review_comment=%s WHERE id=%s',
                    ('approved', reviewer, comment, record_id))
                # 推进 Outbox
                cursor.execute(
                    'INSERT INTO outbox (event_type, payload) VALUES (%s, %s)',
                    ('quality_approved', json.dumps({'record_id': record_id})))
            else:
                cursor.execute(
                    'UPDATE container_center.quality_records SET review_status=%s, reviewed_by=%s, reviewed_at=NOW(), review_comment=%s WHERE id=%s',
                    ('rejected', reviewer, comment, record_id))
                # 退回 = 重置任务状态，允许重新编辑
                cursor.execute(
                    'INSERT INTO outbox (event_type, payload) VALUES (%s, %s)',
                    ('quality_rejected', json.dumps({'record_id': record_id})))

            conn.commit()

        # 退回时重置 data_packages 状态
        if action == 'rejected':
            with get_connection_context() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE container_center.data_packages SET status='pending' WHERE related_order=%s AND data_type = 'quality_task'",
                    (rec.get('order_no'),))

        logger.info('质检审核: record_id=%s action=%s by=%s', record_id, action, reviewer)

        # 通知 8008
        import threading, uuid
        _payload = {'action':'review','order_no':rec.get('order_no','')}
        t = threading.Thread(target=_notify_8008, args=(_payload,))
        t.daemon = False
        t.start()

        return _ok(record_id=record_id, action=action)
    except Exception as e:
        logger.error('审核失败: %s', e, exc_info=True)
        return _fail(str(e), 500)


# ----------------------------------------------------------------
# 6. 返工
# ----------------------------------------------------------------
@bp.route('/rework', methods=['POST'])
def rework():
    data = _safe_body()
    record_id = data.get('record_id')
    if not record_id:
        return _fail('record_id 不能为空')

    try:
        rec = _qc_get(record_id)
        if not rec:
            return _fail('质检记录不存在', 404)

        rework_ver = (rec.get('rework_version') or 1) + 1
        if rework_ver > 4:
            return _fail('已达最大返工次数(3次)，请评估是否报废', 422)

        # 创建返工记录
        new_id = _qc_create_full(
            order_no=rec.get('order_no', ''),
            inspection_type=rec.get('inspection_type', ''),
            process_name=rec.get('process_name', ''),
            inspector=rec.get('inspector', ''),
            items=_qc_get_items(record_id),
            overall_result='待复检',
            status='quality_re_received',
        )

        # 更新版本链
        with get_connection_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE container_center.quality_records SET parent_record_id=%s, rework_version=%s WHERE id=%s',
                (record_id, rework_ver, new_id))

        logger.info('创建返工任务: %s → %s (v%s)', record_id, new_id, rework_ver)
        return _ok(record_id=new_id, rework_version=rework_ver)
    except Exception as e:
        logger.error('返工失败: %s', e, exc_info=True)
        return _fail(str(e), 500)


# ----------------------------------------------------------------
# 7. 返工版本链
# ----------------------------------------------------------------
@bp.route('/versions/<order_no>', methods=['GET'])
def versions(order_no):
    try:
        records = _qc_get_timeline(order_no)
        chain = []
        for r in (records or []):
            chain.append({
                'id': r['id'],
                'result': r.get('result', ''),
                'rework_version': r.get('rework_version', 1),
                'parent_record_id': r.get('parent_record_id'),
                'inspector': r.get('inspector', ''),
                'record_date': str(r.get('record_date', '')),
            })
        return _ok(versions=chain, total=len(chain))
    except Exception as e:
        return _fail(str(e), 500)


# ----------------------------------------------------------------
# 8. 照片上传
# ----------------------------------------------------------------
ALLOWED_EXT = {'.jpg', '.jpeg', '.png'}
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads', 'quality')


@bp.route('/photos/upload', methods=['POST'])
def photos_upload():
    if 'file' not in request.files:
        return _fail('请选择文件')

    f = request.files['file']
    ext = os.path.splitext(f.filename or '')[1].lower()
    if ext not in ALLOWED_EXT:
        return _fail('仅支持 jpg/png 格式', 415)

    # 魔术字节校验
    header = f.read(8)
    f.seek(0)
    if ext == '.png' and header[:8] != b'\x89PNG\r\n\x1a\n':
        return _fail('文件内容与扩展名不匹配', 415)
    if ext in ('.jpg', '.jpeg') and header[:2] != b'\xff\xd8':
        return _fail('文件内容与扩展名不匹配', 415)

    if f.content_length and f.content_length > 10 * 1024 * 1024:
        return _fail('文件超过 10MB', 413)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = uuid.uuid4().hex + ext
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    f.save(filepath)

    return _ok(path=f'/static/uploads/quality/{safe_name}', filename=safe_name)


# ----------------------------------------------------------------
# 9. 历史记录
# ----------------------------------------------------------------
@bp.route('/history', methods=['GET'])
def history():
    order_no = request.args.get('order_no', '')
    result = request.args.get('result', '全部')
    limit = int(request.args.get('limit', 50))

    try:
        if order_no:
            records = _qc_get_timeline(order_no) or []
        else:
            records = _qc_get_all(limit=limit) or []
            if result != '全部':
                records = [r for r in records if r.get('result') == result]

        out = []
        for r in records:
            out.append({
                'id': r.get('id'),
                'order_no': r.get('order_no', ''),
                'inspection_type': r.get('inspection_type', ''),
                'process_name': r.get('process_name', ''),
                'result': r.get('result', ''),
                'review_status': r.get('review_status', ''),
                'inspector': r.get('inspector', ''),
                'record_date': str(r.get('record_date', '')),
                'rework_version': r.get('rework_version', 0) or 0,
                'defect_description': r.get('defect_description', ''),
            })
        return _ok(records=out, total=len(out))
    except Exception as e:
        logger.error('历史查询失败: %s', e, exc_info=True)
        return _fail(str(e), 500)


# ----------------------------------------------------------------
# 10. 类型选项
# ----------------------------------------------------------------
@bp.route('/types', methods=['GET'])
def quality_types():
    return _ok(
        inspection_types=[{'value': t, 'label': t} for t in INSPECTION_TYPES],
        results=[{'value': r, 'label': r} for r in INSPECTION_RESULTS],
        handling_methods=[{'value': m, 'label': m} for m in HANDLING_METHODS],
    )


# ====== 8008 通知函数（独立线程 + 重试 + 死信） ======
import pymysql, requests as _requests

def _notify_8008(payload):
    """独立线程：通知 8008 桥接，失败写死信表"""
    import uuid, time
    url = f'{os.environ.get("SYNC_BRIDGE_URL","http://127.0.0.1:8008")}/api/sync/quality-report'
    payload['msg_id'] = payload.get('msg_id', str(uuid.uuid4()))

    for i in range(3):
        try:
            r = _requests.post(url, json=payload, timeout=5)
            if r.status_code == 200:
                return
            if r.status_code in (400, 401, 403, 404, 405, 409, 422):
                break
        except (_requests.ConnectionError, _requests.Timeout):
            pass
        except Exception:
            break
        time.sleep(2 ** i)

    try:
        from models.database import get_connection_context
        with get_connection_context() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO notification_dlq (order_no, payload, error_msg, created_at) "
                "VALUES (%s, %s, 'NOTIFY_FAILED', NOW())",
                (payload.get('order_no', ''), json.dumps(payload, ensure_ascii=False)))
            conn.commit()
    except Exception:
        pass
