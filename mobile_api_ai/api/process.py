# -*- coding: utf-8 -*-
"""
报工模块 - 从容器中心 MySQL 读取任务，提交报工
"""
import logging
import json, os
from datetime import datetime
from flask import Blueprint, request
from .decorators import success, fail
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
from core.db import get_direct_connection

logger = logging.getLogger(__name__)
bp = Blueprint('process', __name__, url_prefix='/api/process')


def _get_conn():
    """获取容器中心 MySQL 连接"""
    return get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)


@bp.route('/my-tasks', methods=['GET'])
def my_tasks():
    worker_id = request.args.get('worker_id', '')
    if not worker_id.strip():
        return fail(message="缺少 worker_id 参数", code=400)
    try:
        conn = _get_conn()
        cur = conn.cursor()

        # 查 data_packages: 分配给该工人的 + 全员派发的
        cur.execute("""
            SELECT id, title, content, data_type, related_process, related_order,
                   target_operator, status, completed_qty, is_public
            FROM process_sub_steps
            WHERE (target_operator = %s OR is_public = 1)
              AND data_type IN ('report','task','work_order','flow_step','process_report','quality_task')
              AND status != 'completed'
            ORDER BY created_at DESC
            LIMIT 50
        """, (worker_id,))
        rows = cur.fetchall()

        conn.close()

        task_list = []
        for r in rows:
            content_raw = r.get('content')
            content = json.loads(content_raw) if isinstance(content_raw, str) else (content_raw or {})
            task_list.append({
                'task_id': r['id'],
                'process_name': content.get('process_name', r.get('related_process') or r.get('title') or '未知工序'),
                'order_no': r.get('related_order') or content.get('order_no', ''),
                'customer_name': content.get('customer_name', ''),
                'product_type': content.get('product_type', ''),
                'planned_qty': content.get('planned_qty', content.get('quantity', 0)),
                'completed_qty': content.get('completed_qty', 0),
                'status': r.get('status', '进行中'),
                'source': 'process_sub_steps',
            })

        return success(data={'tasks': task_list, 'total': len(task_list)})
    except Exception as e:
        logger.exception("my_tasks error")
        return fail(500, message=str(e))
