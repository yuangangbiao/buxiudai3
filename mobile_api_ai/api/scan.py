# -*- coding: utf-8 -*-
"""
扫码模块 - 从容器中心获取数据
不直接调用主数据库，数据来源：中间容器池
"""
import logging
import os
from flask import Blueprint, request, jsonify
from .auth import success, fail
from mobile_api_ai.api.limiter import limiter
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
from core.db import get_direct_connection

logger = logging.getLogger(__name__)
bp = Blueprint('scan', __name__, url_prefix='/api/scan')


def _get_conn():
    return get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)


class _ContainerCenterHolder:
    """容器中心惰性单例持有者"""
    _instance = None

    @classmethod
    def get(cls):
        if not cls._instance:
            try:
                from container_center_v5 import ContainerCenter
                cls._instance = ContainerCenter()
                logger.info('容器中心初始化成功 (MySQL)')
            except Exception as e:
                logger.error(f'容器中心初始化失败: {e}')
        return cls._instance


def get_container_center():
    """获取容器中心实例"""
    return _ContainerCenterHolder.get()


def parse_qr_data(qr_data):
    """
    解析二维码数据
    
    支持的格式：
    - WO:WO202604001 (订单号)
    - ORD:ORD202604001 (订单号)
    - WO202604001 (订单号简写)
    
    Returns:
        dict: {type: 'workorder'|'order', value: xxx}
    """
    if qr_data.startswith('WO:'):
        return {'type': 'workorder', 'value': qr_data[3:]}
    elif qr_data.startswith('ORD:'):
        return {'type': 'order', 'value': qr_data[4:]}
    elif qr_data.startswith('WO'):
        return {'type': 'workorder', 'value': qr_data}
    else:
        # 默认视为工单
        return {'type': 'workorder', 'value': qr_data}


def find_task_in_container(container_center, qr_info):
    """
    在容器中查找对应的任务数据
    
    Args:
        container_center: 容器中心实例
        qr_info: 解析后的二维码信息 {type, value}
    
    Returns:
        dict: 任务数据或 None
    """
    try:
        # 获取所有任务
        all_tasks = container_center.get_all_tasks(limit=200)
        
        if qr_info['type'] == 'workorder':
            order_no = qr_info['value']
            # 查找与订单号相关的任务
            for task in all_tasks:
                # 从content中查找订单号
                content = task.get('content', {})
                if isinstance(content, dict):
                    # 检查content中的订单号
                    if content.get('order_no') == order_no:
                        return task
                    # 检查related_order
                    if task.get('related_order') and order_no in task.get('title', ''):
                        return task
        
        elif qr_info['type'] == 'order':
            order_no = qr_info['value']
            # 查找与订单号相关的任务
            for task in all_tasks:
                if task.get('related_order') == order_no:
                    return task
        
        return None
    except Exception as e:
        logger.error(f'[Scan API] 在容器中查找任务失败: {e}')
        return None


def format_task_data(task):
    """
    格式化任务数据，用于返回给前端
    
    Args:
        task: 从容器中获取的任务数据
    
    Returns:
        dict: 格式化后的数据
    """
    content = task.get('content', {}) if isinstance(task.get('content'), dict) else {}
    
    return {
        'task_id': task.get('id', ''),
        'title': task.get('title', ''),
        'status': task.get('status', ''),
        'priority': task.get('priority', 'normal'),
        'order_info': {
            'order_no': content.get('order_no', task.get('related_order', '')),
            'customer_name': content.get('customer_name', ''),
            'product_type': content.get('product_type', ''),
            'quantity': content.get('quantity', 0),
            'unit': content.get('unit', '')
        },
        'current_process': {
            'process_name': content.get('process_name', ''),
            'planned_qty': content.get('planned_qty', 0),
            'status': content.get('process_status', '待开始')
        },
        'operator': {
            'id': task.get('target_operator', ''),
            'name': content.get('operator_name', '')
        },
        'voice_text': content.get('voice_text', ''),
        'created_at': task.get('created_at', ''),
        'distributed_at': task.get('distributed_at', '')
    }


@bp.route('/workorder/<order_no>', methods=['GET'])
@limiter.limit("60 per minute")
def scan_workorder(order_no):
    """扫码工单获取信息 - 从容器获取数据"""
    container_center = get_container_center()
    if not container_center:
        return fail(code=5001, message='容器中心不可用')

    try:
        # 在容器中查找任务
        qr_info = {'type': 'workorder', 'value': order_no}
        task = find_task_in_container(container_center, qr_info)
        
        if not task:
            return fail(code=2001, message=f'工单 {order_no} 在容器中未找到')
        
        # 格式化返回数据
        task_data = format_task_data(task)
        
        return success(data=task_data)
    except Exception as e:
        logger.exception(f'[Scan API] 查询工单失败: {e}')
        return fail(code=5002, message=f'查询失败: {str(e)}')


@bp.route('/task', methods=['POST'])
@limiter.limit("60 per minute")
def scan_workorder_task():
    """
    扫码工单后获取任务 - 从容器获取数据
    
    请求: { qr_data: "WO:WO202604001", operator_id: "OP001" }
    """
    data = request.get_json()
    qr_data = data.get('qr_data', '')
    operator_id = data.get('operator_id', '')

    if not qr_data:
        return fail(code=4001, message='二维码数据不能为空')

    container_center = get_container_center()
    if not container_center:
        return fail(code=5001, message='容器中心不可用')

    try:
        # 解析二维码数据
        qr_info = parse_qr_data(qr_data)
        
        # 在容器中查找任务
        task = find_task_in_container(container_center, qr_info)
        
        if not task:
            return fail(code=2001, message=f'未找到对应的任务，请先在系统中创建任务')
        
        # 格式化返回数据
        task_data = format_task_data(task)
        
        # 如果任务还没分配，并且提供了operator_id，则分配任务
        if operator_id and task.get('status') in ['pending']:
            success_distribute = container_center.distributor.distribute(
                task.get('id'), operator_id
            )
            if success_distribute:
                task_data['status'] = 'distributed'
                logger.info(f'[Scan API] 任务 {task.get("id")} 已分配给 {operator_id}')
        
        return success(data=task_data)
    except Exception as e:
        logger.exception(f'[Scan API] 获取任务失败: {e}')
        return fail(code=5002, message=f'查询失败: {str(e)}')


@bp.route('/worker/<worker_id>', methods=['GET'])
@limiter.limit("60 per minute")
def scan_worker(worker_id):
    """扫码员工获取信息"""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, wechat_userid, name, role, phone, department FROM workers WHERE wechat_userid = %s",
            (worker_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return fail(code=404, message="工人不存在")
        return success(data={
            'worker_id': row['wechat_userid'],
            'name': row['name'],
            'role': row['role'] or '员工',
            'phone': row['phone'] or '',
            'department': row['department'] or '',
        })
    except Exception as e:
        logger.exception("scan_worker error")
        return fail(code=500, message=str(e))


@bp.route('/test/create-sample', methods=['POST'])
@limiter.limit("60 per minute")
def create_sample_task():
    """
    测试接口：创建示例任务到容器中
    
    （开发测试用）
    """
    container_center = get_container_center()
    if not container_center:
        return fail(code=5001, message='容器中心不可用')
    
    data = request.get_json() or {}
    
    order_no = data.get('order_no', 'ORD202604001')
    order_no = data.get('order_no', 'WO202604001')
    process_name = data.get('process_name', '编织')
    quantity = data.get('quantity', 100)
    operator_id = data.get('operator_id')

    if not operator_id:
        return fail(code=4002, message='operator_id为必填参数')
    
    try:
        # 创建示例任务到容器
        pkg = container_center.collect_report(
            order_no=order_no,
            process_name=process_name,
            record_id=0,
            operator_id=operator_id,
            planned_qty=quantity
        )
        
        # 补充数据到content
        pkg.content['order_no'] = order_no
        pkg.content['customer_name'] = '上海机械厂'
        pkg.content['product_type'] = '不锈钢编织网'
        pkg.content['unit'] = '米'
        pkg.content['voice_text'] = f'订单{order_no}，工序{process_name}，数量{quantity}，请确认任务！'
        
        container_center.storage.save_package(pkg.to_dict())
        
        return success(data={
            'task_id': pkg.id,
            'message': '示例任务已创建到容器中'
        })
    except Exception as e:
        logger.error(f'[Scan API] 创建示例任务失败: {e}')
        return fail(code=5003, message=str(e))

