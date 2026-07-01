# -*- coding: utf-8 -*-
"""
质检模块 - 提交质检记录，联动调度中心流程状态
"""
from flask import Blueprint, request, jsonify
from .auth import success, fail
import random
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('quality', __name__, url_prefix='/api/quality')


def _quality_conn():
    import os
    from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
    from core.db import get_direct_connection
    return get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)


@bp.route('/list', methods=['GET'])
def quality_list():
    try:
        conn = _quality_conn()
        c = conn.cursor()
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 20)), 100)
        offset = (page - 1) * page_size
        c.execute("SELECT COUNT(*) as total FROM quality_records")
        total = c.fetchone()['total']
        c.execute("SELECT * FROM quality_records ORDER BY record_date DESC LIMIT %s OFFSET %s",
                  (page_size, offset))
        records = c.fetchall()
        conn.close()
        return success(data={'records': records, 'total': total, 'page': page, 'page_size': page_size})
    except Exception as e:
        return fail(message=str(e))


@bp.route('/<int:order_id>/create', methods=['POST'])
def create_quality(order_id):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        data = {}

    result = data.get('result', '合格')
    inspector = data.get('inspector', '')
    order_no = data.get('order_no', '').strip()
    process_id = data.get('process_id', '').strip()
    inspection_type = data.get('inspection_type', '')

    import datetime
    record = {
        'order_no': order_no or str(order_id),
        'result': result,
        'inspection_type': inspection_type,
        'inspector': inspector,
        'process_name': data.get('process_name', process_id or ''),
        'record_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    try:
        conn = _quality_conn()
        c = conn.cursor()
        c.execute('''INSERT INTO quality_records (order_no, result, inspection_type,
                     inspector, process_name, record_date) VALUES (%s,%s,%s,%s,%s,%s)''',
                  (record['order_no'], record['result'],
                   record['inspection_type'], record['inspector'],
                   record['process_name'], record['record_date']))
        conn.commit()
        conn.close()
    except Exception as e:
        return fail(message=f'写入数据库失败: {e}')

    dispatch_msg = ''
    if order_no and process_id:
        try:
            from dispatch_center import on_quality_record_completed
            ok, dispatch_msg = on_quality_record_completed(order_no, process_id, result, inspector)
            if ok:
                logger.info(f'[质检联动] {order_no} 流程状态已更新: {dispatch_msg}')
            else:
                logger.warning(f'[质检联动] {order_no} 流程更新失败: {dispatch_msg}')
        except Exception as e:
            logger.warning(f'[质检联动] {order_no} 调度中心联动异常: {e}')
            dispatch_msg = f'调度中心联动异常: {e}'

    order_status = '已完成' if result == '合格' else '质检中'
    return success(message='质检记录已保存', data={
        'quality_id': record['id'],
        'order_status': order_status,
        'dispatch_result': dispatch_msg,
    })

@bp.route('/types', methods=['GET'])
def quality_types():
    return success(data={
        'types': ['来料检验', '首检', '巡检', '终检'],
        'results': ['合格', '不合格', '待复检']
    })
