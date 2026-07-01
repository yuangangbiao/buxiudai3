# -*- coding: utf-8 -*-
"""
排产流程模块
支持从工单发布到排产确认的完整流程
"""
import logging
import json
import os
import requests
from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)

schedule_bp = Blueprint('schedule', __name__, url_prefix='/api/schedule')

# 调度中心/微信服务器地址（从环境变量读取，支持配置化）
_DISPATCH_CENTER_URL = os.environ.get('DISPATCH_CENTER_URL', 'http://127.0.0.1:5003')
_WECHAT_SERVER_URL = os.environ.get('WECHAT_SERVER_URL', 'http://127.0.0.1:5003')

SCHEDULE_STATUS = {
    'CREATED': 'created',
    'PUBLISHED': 'published',
    'WAITING_SCHD': 'waiting_schedule',
    'SCHEDULED': 'scheduled',
    'SCHED_NOTIFIED': 'sched_notified',
    'CONFIRMED': 'confirmed',
    'REJECTED': 'rejected'
}

MSG_TYPE = {
    'ORDER_PUBLISH': 'ORDER_PUBLISH',
    'SCHEDULE_NOTIFY': 'SCHEDULE_NOTIFY',
    'SCHEDULE_SUBMIT': 'SCHEDULE_SUBMIT',
    'SCHEDULE_CONFIRM': 'SCHEDULE_CONFIRM',
    'SCHEDULE_REJECT': 'SCHEDULE_REJECT'
}

_container_center_client = None


def get_container_center_client():
    """获取容器中心客户端实例"""
    global _container_center_client
    if _container_center_client is None:
        try:
            from container_center_client import ContainerCenterClient
            base_url = os.getenv('CONTAINER_CENTER_API_URL')
            if base_url:
                _container_center_client = ContainerCenterClient(base_url=base_url)
                logger.info(f"[Schedule] 容器中心客户端初始化成功: {base_url}")
            else:
                logger.warning("[Schedule] CONTAINER_CENTER_API_URL 未配置，容器中心客户端未初始化")
        except Exception as e:
            logger.error(f"[Schedule] 容器中心客户端初始化失败: {e}")
            _container_center_client = None
    return _container_center_client


def get_container_integration():
    """获取容器集成实例（已废弃，始终返回 None）"""
    return None


def get_storage():
    """获取存储实例"""
    integration = get_container_integration()
    if integration and integration.is_available:
        return integration._container_center.storage
    return None


def generate_schedule_id(prefix: str = 'SCH') -> str:
    """生成排产记录ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique = str(uuid.uuid4())[:4].upper()
    return f"{prefix}-{timestamp}-{unique}"

def get_wechat_bot():
    """获取微信机器人实例"""
    try:
        from wechat_server import group_bot
        return group_bot
    except ImportError as e:
        logger.error(f"无法导入群机器人实例: {e}")
        return None

def get_main_system_db_connection():
    """获取主系统数据库连接"""
    import sys
    import os
    
    # 添加主系统路径到模块搜索路径
    main_system_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if main_system_path not in sys.path:
        sys.path.insert(0, main_system_path)
    
    try:
        from models.database import get_connection
        return get_connection()
    except Exception as e:
        logger.error(f"获取主系统数据库连接失败: {e}")
        return None


def get_customer_from_group(order_no: str) -> str:
    """
    从主系统数据库获取客户信息
    
    Args:
        order_no: 订单号或订单号
        
    Returns:
        客户名称，如果未找到返回'待定'
    """
    try:
        conn = get_main_system_db_connection()
        if not conn:
            logger.warning("无法连接主系统数据库,使用默认值")
            return '待定'
        
        cursor = conn.cursor()
        
        # 首先尝试从生产订单表查找(通过订单号)
        cursor.execute("""
            SELECT o.customer_name, o.customer_group
            FROM production_orders po
            LEFT JOIN orders o ON po.order_id = o.id
            WHERE po.order_no = %s
            LIMIT 1
        """, (order_no,))
        
        result = cursor.fetchone()
        if result:
            customer_name = result.get('customer_name')
            customer_group = result.get('customer_group')
            # 优先使用客户名称,如果没有则使用客户分组
            if customer_name:
                return customer_name
            if customer_group:
                return customer_group
        
        # 如果生产订单没找到,尝试直接从订单表查找(通过订单号)
        cursor.execute("""
            SELECT customer_name, customer_group
            FROM orders
            WHERE order_no = %s
            LIMIT 1
        """, (order_no,))
        
        result = cursor.fetchone()
        if result:
            customer_name = result.get('customer_name')
            customer_group = result.get('customer_group')
            if customer_name:
                return customer_name
            if customer_group:
                return customer_group
        
        # 尝试前缀匹配
        cursor.execute("""
            SELECT o.customer_name, o.customer_group
            FROM production_orders po
            LEFT JOIN orders o ON po.order_id = o.id
            WHERE po.order_no LIKE %s
            LIMIT 1
        """, (f"{order_no}%",))
        
        result = cursor.fetchone()
        if result:
            customer_name = result.get('customer_name')
            customer_group = result.get('customer_group')
            if customer_name:
                return customer_name
            if customer_group:
                return customer_group
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"从主系统数据库获取客户信息失败: {e}")
    
    return '待定'


def get_order_info_from_main_system(order_no: str) -> Dict:
    """
    从主系统数据库获取订单完整信息
    
    Args:
        order_no: 订单号或订单号
        
    Returns:
        订单信息字典
    """
    order_info = {}
    
    try:
        conn = get_main_system_db_connection()
        if not conn:
            return order_info
        
        cursor = conn.cursor()
        
        # 首先尝试从生产订单表查找(通过订单号)
        cursor.execute("""
            SELECT o.*, po.order_no, po.priority as production_priority
            FROM production_orders po
            LEFT JOIN orders o ON po.order_id = o.id
            WHERE po.order_no = %s
            LIMIT 1
        """, (order_no,))
        
        result = cursor.fetchone()
        if result:
            order_info = dict(result)
            order_info['order_no'] = result.get('order_no')
        
        # 如果生产订单没找到,尝试直接从订单表查找(通过订单号)
        if not order_info:
            cursor.execute("""
                SELECT * FROM orders WHERE order_no = %s LIMIT 1
            """, (order_no,))
            
            result = cursor.fetchone()
            if result:
                order_info = dict(result)
        
        # 尝试前缀匹配
        if not order_info:
            cursor.execute("""
                SELECT o.*, po.order_no
                FROM production_orders po
                LEFT JOIN orders o ON po.order_id = o.id
                WHERE po.order_no LIKE %s OR o.order_no LIKE %s
                LIMIT 1
            """, (f"{order_no}%", f"{order_no}%"))
            
            result = cursor.fetchone()
            if result:
                order_info = dict(result)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"从主系统数据库获取订单信息失败: {e}")
    
    return order_info


@schedule_bp.route('/publish', methods=['POST'])
def api_publish_order():
    """
    发布工单到容器中心（阶段1）

    请求体:
    {
        "order_no": "ORD-2024-001",
        "product_name": "不锈钢网带",
        "quantity": 1000,
        "delivery_date": "2024-12-31",
        "priority": "normal",
        "source": "desktop"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400

        order_no = data.get('order_no')
        if not order_no:
            return jsonify({'code': 400, 'message': 'order_no不能为空'}), 400

        storage = get_storage()
        if not storage:
            return jsonify({'code': 500, 'message': '存储未初始化'}), 500

        # 从主系统获取订单信息
        main_system_order_info = get_order_info_from_main_system(order_no)
        
        # 优先使用主系统数据,如果没有则使用请求数据
        customer_name = data.get('customer_name') or main_system_order_info.get('customer_name') or get_customer_from_group(order_no)
        product_name = data.get('product_name') or main_system_order_info.get('product_type', '')
        quantity = data.get('quantity') or main_system_order_info.get('quantity', 0)
        unit = data.get('unit') or main_system_order_info.get('unit', '件')
        delivery_date = data.get('delivery_date') 
        if not delivery_date and main_system_order_info.get('delivery_date'):
            delivery_date = main_system_order_info.get('delivery_date').isoformat() if hasattr(main_system_order_info.get('delivery_date'), 'isoformat') else str(main_system_order_info.get('delivery_date'))
        
        # 获取订单号
        order_no = main_system_order_info.get('order_no') or order_no

        schedule_id = generate_schedule_id('SCH')
        now = datetime.now().isoformat()

        record = {
            'schedule_id': schedule_id,
            'order_no': order_no,
            'status': SCHEDULE_STATUS['PUBLISHED'],
            'product_name': product_name,
            'customer_name': customer_name,
            'customer_group': main_system_order_info.get('customer_group', ''),
            'quantity': quantity,
            'unit': unit,
            'delivery_date': delivery_date or '',
            'priority': data.get('priority', 'normal'),
            'source': data.get('source', 'desktop'),
            'material': main_system_order_info.get('material', ''),
            'surface_treatment': main_system_order_info.get('surface_treatment', ''),
            'schedule_data': None,
            'published_at': now,
            'notified_at': None,
            'submitted_at': None,
            'confirmed_at': None,
            'confirmed_by': None,
            'rejected_at': None,
            'rejected_by': None,
            'reject_reason': None,
            'created_at': now,
            'updated_at': now
        }

        storage.save_schedule_record(record)

        cc_client = get_container_center_client()
        if cc_client:
            try:
                task_content = {
                    'process_name': '排产发布',
                    'customer_name': customer_name,
                    'product_type': product_name,
                    'quantity': quantity,
                    'unit': unit,
                    'planned_qty': quantity,
                    'process_status': '待排产',
                    'operator_name': '系统',
                    'delivery_date': delivery_date or '',
                    'material': main_system_order_info.get('material', ''),
                    'surface_treatment': main_system_order_info.get('surface_treatment', ''),
                }
                result = cc_client.publish_task(
                    task_type='report',
                    title=f'排产发布：{order_no}',
                    content=task_content,
                    operator_id='SYSTEM',
                    priority=data.get('priority', 'normal'),
                    related_order=order_no,
                    related_process='排产发布'
                )
                if result.get('code') == 0:
                    task_id = result.get('data', {}).get('task_id')
                    logger.info(f"[Schedule] 任务发布到容器中心成功: {task_id}")
                    _notify_dispatch_center_new_task(order_no, order_no, task_id)
                else:
                    logger.warning(f"[Schedule] 任务发布到容器中心失败: {result.get('message')}")
            except Exception as e:
                logger.error(f"[Schedule] 任务发布到容器中心异常: {e}")
        else:
            logger.warning("[Schedule] 容器中心客户端未初始化，跳过任务发布")

        bot = get_wechat_bot()
        if bot:
            try:
                # 获取客户群名称
                customer_name = data.get('customer_name', get_customer_from_group(order_no))
                
                message = f"""📋 **新工单发布**

---
**📋 工单**: `{order_no}`
**🏭 客户**: {customer_name}
**📦 产品**: {product_name}
**🎯 数量**: {quantity} {unit}
**📅 交期**: {delivery_date or '待定'}
**⭐ 优先级**: {data.get('priority', 'normal')}
**⏰ 发布时间**: {now}

---
请生产部门尽快制定排产计划！"""
                bot.send_markdown(message)
            except Exception as e:
                logger.warning(f"[Schedule] 发送微信通知失败: {e}")

        # 在调度中心流程编排中注册工单
        try:
            register_data = {
                'customer_name': customer_name,
                'customer_group': main_system_order_info.get('customer_group', ''),
                'product_name': product_name,
                'quantity': quantity,
                'unit': unit,
                'delivery_date': delivery_date or '',
                'priority': data.get('priority', 'normal'),
                'flow_type': 'production',
            }
            resp = requests.post(
                f'{_DISPATCH_CENTER_URL}/api/dispatch-center/workorder/register',
                json=register_data,
                timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '3'))
            )
            if resp.ok:
                result = resp.json()
                if result.get('code') == 0:
                    logger.info(f"[Schedule] 调度中心工单注册成功: {order_no}, process_id={result.get('data', {}).get('process_id')}")
                else:
                    logger.warning(f"[Schedule] 调度中心工单注册返回异常: {result}")
            else:
                logger.warning(f"[Schedule] 调度中心工单注册请求失败: status={resp.status_code}")
        except requests.ConnectionError:
            logger.warning(f"[Schedule] 调度中心连接失败(工单注册降级): {order_no}")
        except Exception as e:
            logger.warning(f"[Schedule] 调度中心工单注册异常(已降级): {e}")

        return jsonify({
            'code': 0,
            'message': '工单发布成功',
            'data': {
                'schedule_id': schedule_id,
                'status': SCHEDULE_STATUS['PUBLISHED'],
                'published_at': now
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


def _notify_dispatch_center_new_task(order_no: str, task_id: str):
    """
    主动通知调度中心有新任务到达

    Args:
        order_no: 订单号
        order_no: 订单号
        task_id: 容器中心任务ID
    """
    try:
        dispatch_notify_data = {
            'event_type': 'task_published',
            'task_id': task_id,
            'source': 'container_center',
            'timestamp': datetime.now().isoformat()
        }
        resp = requests.post(
            f'{_WECHAT_SERVER_URL}/api/dispatch-center/task-notify',
            json=dispatch_notify_data,
            timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5'))
        )
        if resp.ok and resp.json().get('code') == 0:
            logger.info(f"[Schedule] 调度中心任务通知成功: order_no={order_no}, task_id={task_id}")
        else:
            logger.warning(f"[Schedule] 调度中心任务通知失败: {resp.status_code}")
    except requests.ConnectionError:
        logger.warning(f"[Schedule] 调度中心连接失败(任务通知已降级): order_no={order_no}")
    except Exception as e:
        logger.warning(f"[Schedule] 调度中心任务通知异常(已降级): {e}")


@schedule_bp.route('/notify', methods=['POST'])
def api_notify_production():
    """
    向生产部门发送排产通知（阶段2）

    请求体:
    {
        "order_no": "ORD-2024-001",
        "schedule_required_by": "2024-01-16T18:00:00"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400

        order_no = data.get('order_no')
        if not order_no:
            return jsonify({'code': 400, 'message': 'order_no不能为空'}), 400

        storage = get_storage()
        if not storage:
            return jsonify({'code': 500, 'message': '存储未初始化'}), 500

        record = storage.get_schedule_record_by_order(order_no)
        if not record:
            return jsonify({'code': 404, 'message': f'工单不存在: {order_no}'}), 404

        now = datetime.now().isoformat()
        record['status'] = SCHEDULE_STATUS['WAITING_SCHD']
        record['notified_at'] = now
        record['schedule_required_by'] = data.get('schedule_required_by')
        record['updated_at'] = now

        storage.save_schedule_record(record)

        storage.log_schedule_flow(order_no, MSG_TYPE['SCHEDULE_NOTIFY'], {
            'order_no': order_no,
            'schedule_required_by': data.get('schedule_required_by')
        }, 'SYSTEM')

        bot = get_wechat_bot()
        if bot:
            try:
                # 获取客户群名称
                customer_name = record.get('customer_name', get_customer_from_group(order_no))
                order_no = record.get('order_no', order_no)
                
                message = f"""⏰ **排产制定通知**

---
**📋 工单**: `{order_no}`
**🏭 客户**: {customer_name}
**📦 产品**: {record.get('product_name', '')}
**🎯 数量**: {record.get('quantity', 0)} {record.get('unit', '件')}
**⏰ 要求完成时间**: {data.get('schedule_required_by', '尽快')}
**📅 通知时间**: {now}

---
请生产部门尽快制定排产计划！"""
                bot.send_markdown(message)
            except Exception as e:
                logger.warning(f"[Schedule] 发送微信通知失败: {e}")

        return jsonify({
            'code': 0,
            'message': '排产通知已发送',
            'data': {
                'order_no': order_no,
                'status': SCHEDULE_STATUS['WAITING_SCHD'],
                'notified_at': now
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@schedule_bp.route('/submit', methods=['POST'])
def api_submit_schedule():
    """
    生产部门提交排产信息（阶段3）

    请求体:
    {
        "order_no": "ORD-2024-001",
        "schedule": {
            "processes": [
                {"name": "来料", "worker": "张三", "start": "01-20", "end": "01-21"},
                {"name": "编织", "worker": "李四", "start": "01-22", "end": "01-25"}
            ],
            "total_days": 7,
            "estimated_complete": "2024-01-27"
        },
        "submitted_by": "生产部"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400

        order_no = data.get('order_no')
        if not order_no:
            return jsonify({'code': 400, 'message': 'order_no不能为空'}), 400

        schedule = data.get('schedule')
        if not schedule:
            return jsonify({'code': 400, 'message': 'schedule不能为空'}), 400

        storage = get_storage()
        if not storage:
            return jsonify({'code': 500, 'message': '存储未初始化'}), 500

        record = storage.get_schedule_record_by_order(order_no)
        if not record:
            return jsonify({'code': 404, 'message': f'工单不存在: {order_no}'}), 404

        if record.get('status') not in [SCHEDULE_STATUS['PUBLISHED'], SCHEDULE_STATUS['WAITING_SCHD']]:
            return jsonify({'code': 400, 'message': f'当前状态不允许提交排产: {record.get("status")}'}), 400

        now = datetime.now().isoformat()
        record['status'] = SCHEDULE_STATUS['SCHEDULED']
        record['schedule_data'] = json.dumps(schedule, ensure_ascii=False)
        record['submitted_at'] = now
        record['submitted_by'] = data.get('submitted_by', '生产部')
        record['updated_at'] = now

        storage.save_schedule_record(record)

        storage.log_schedule_flow(order_no, MSG_TYPE['SCHEDULE_SUBMIT'], {
            'order_no': order_no,
            'schedule': schedule,
            'submitted_by': data.get('submitted_by')
        }, data.get('submitted_by', '生产部'))

        bot = get_wechat_bot()
        if bot:
            try:
                # 获取客户群名称
                customer_name = record.get('customer_name', get_customer_from_group(order_no))
                order_no = record.get('order_no', order_no)
                
                processes_text = '\n'.join([
                    f"  • {p['name']}: {p['worker']} ({p['start']} ~ {p['end']})"
                    for p in schedule.get('processes', [])
                ])
                message = f"""✅ **排产已提交**

---
**📋 工单**: `{order_no}`
**🏭 客户**: {customer_name}
**📦 产品**: {record.get('product_name', '')}
**🎯 数量**: {record.get('quantity', 0)} {record.get('unit', '件')}
**📝 提交部门**: {data.get('submitted_by', '生产部')}
**📅 提交时间**: {now}

---
**📋 排产计划**:
{processes_text}

---
**📅 预计完成**: {schedule.get('estimated_complete', '待定')}
**📊 总天数**: {schedule.get('total_days', '待定')}

---
请桌面端确认排产信息！"""
                bot.send_markdown(message)
            except Exception as e:
                logger.warning(f"[Schedule] 发送微信通知失败: {e}")

        return jsonify({
            'code': 0,
            'message': '排产信息已提交',
            'data': {
                'order_no': order_no,
                'status': SCHEDULE_STATUS['SCHEDULED'],
                'submitted_at': now,
                'schedule': schedule
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@schedule_bp.route('/confirm', methods=['POST'])
def api_confirm_schedule():
    """
    桌面生成端确认排产（阶段4）

    请求体:
    {
        "order_no": "ORD-2024-001",
        "result": "confirmed",
        "confirmed_by": "桌面用户",
        "comments": "排产时间可接受"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400

        order_no = data.get('order_no')
        if not order_no:
            return jsonify({'code': 400, 'message': 'order_no不能为空'}), 400

        result = data.get('result')
        if result not in ['confirmed', 'rejected']:
            return jsonify({'code': 400, 'message': 'result必须是confirmed或rejected'}), 400

        storage = get_storage()
        if not storage:
            return jsonify({'code': 500, 'message': '存储未初始化'}), 500

        record = storage.get_schedule_record_by_order(order_no)
        if not record:
            return jsonify({'code': 404, 'message': f'工单不存在: {order_no}'}), 404

        if record.get('status') != SCHEDULE_STATUS['SCHEDULED']:
            return jsonify({'code': 400, 'message': f'当前状态不允许确认: {record.get("status")}'}), 400

        now = datetime.now().isoformat()

        if result == 'confirmed':
            record['status'] = SCHEDULE_STATUS['CONFIRMED']
            record['confirmed_at'] = now
            record['confirmed_by'] = data.get('confirmed_by', '桌面用户')
            record['confirm_comments'] = data.get('comments', '')
            msg_type = MSG_TYPE['SCHEDULE_CONFIRM']
            success_msg = '排产已确认'
        else:
            record['status'] = SCHEDULE_STATUS['REJECTED']
            record['rejected_at'] = now
            record['rejected_by'] = data.get('confirmed_by', '桌面用户')
            record['reject_reason'] = data.get('comments', data.get('reason', ''))
            msg_type = MSG_TYPE['SCHEDULE_REJECT']
            success_msg = '排产已拒绝'

        record['updated_at'] = now
        storage.save_schedule_record(record)

        storage.log_schedule_flow(order_no, msg_type, {
            'order_no': order_no,
            'result': result,
            'confirmed_by': data.get('confirmed_by'),
            'comments': data.get('comments')
        }, data.get('confirmed_by', '桌面用户'))

        bot = get_wechat_bot()
        if bot:
            try:
                # 获取客户群名称
                customer_name = record.get('customer_name', get_customer_from_group(order_no))
                order_no = record.get('order_no', order_no)
                
                if result == 'confirmed':
                    message = f"""🎉 **排产已确认**

---
**📋 工单**: `{order_no}`
**🏭 客户**: {customer_name}
**📦 产品**: {record.get('product_name', '')}
**🎯 数量**: {record.get('quantity', 0)} {record.get('unit', '件')}
**✅ 确认人**: {data.get('confirmed_by', '桌面用户')}
**📅 确认时间**: {now}

---
排产计划已生效，请按计划执行！"""
                else:
                    message = f"""❌ **排产已拒绝**

---
**📋 工单**: `{order_no}`
**🏭 客户**: {customer_name}
**📦 产品**: {record.get('product_name', '')}
**🎯 数量**: {record.get('quantity', 0)} {record.get('unit', '件')}
**❌ 拒绝人**: {data.get('confirmed_by', '桌面用户')}
**📝 拒绝原因**: {data.get('comments') or data.get('reason', '未说明')}
**📅 拒绝时间**: {now}

---
请生产部门重新制定排产计划！"""
                bot.send_markdown(message)
            except Exception as e:
                logger.warning(f"[Schedule] 发送微信通知失败: {e}")

        return jsonify({
            'code': 0,
            'message': success_msg,
            'data': {
                'order_no': order_no,
                'status': record['status'],
                'result': result,
                'processed_at': now
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@schedule_bp.route('/status/<order_no>', methods=['GET'])
def api_get_schedule_status(order_no):
    """获取工单排产状态"""
    try:
        storage = get_storage()
        if not storage:
            return jsonify({'code': 500, 'message': '存储未初始化'}), 500

        record = storage.get_schedule_record_by_order(order_no)
        if not record:
            return jsonify({'code': 404, 'message': f'工单不存在: {order_no}'}), 404

        result = {
            'order_no': record.get('order_no'),
            'status': record.get('status'),
            'product_name': record.get('product_name'),
            'customer_name': record.get('customer_name'),
            'customer_group': record.get('customer_group'),
            'quantity': record.get('quantity'),
            'unit': record.get('unit', '件'),
            'delivery_date': record.get('delivery_date'),
            'priority': record.get('priority'),
            'material': record.get('material'),
            'surface_treatment': record.get('surface_treatment'),
            'published_at': record.get('published_at'),
            'notified_at': record.get('notified_at'),
            'submitted_at': record.get('submitted_at'),
            'confirmed_at': record.get('confirmed_at'),
            'rejected_at': record.get('rejected_at'),
            'confirmed_by': record.get('confirmed_by'),
            'rejected_by': record.get('rejected_by'),
            'reject_reason': record.get('reject_reason')
        }

        if record.get('schedule_data'):
            try:
                result['schedule'] = json.loads(record['schedule_data'])
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"schedule_data JSON解析失败: {e}")
                result['schedule'] = record['schedule_data']

        return jsonify({
            'code': 0,
            'data': result
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@schedule_bp.route('/pending', methods=['GET'])
def api_get_pending_schedules():
    """获取待排产工单列表"""
    try:
        storage = get_storage()
        if not storage:
            return jsonify({'code': 500, 'message': '存储未初始化'}), 500

        status_filter = request.args.get('status')
        records = storage.get_schedule_records(status_filter)

        return jsonify({
            'code': 0,
            'data': {
                'total': len(records),
                'records': records
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@schedule_bp.route('/history/<order_no>', methods=['GET'])
def api_get_schedule_history(order_no):
    """获取工单排产流程日志"""
    try:
        storage = get_storage()
        if not storage:
            return jsonify({'code': 500, 'message': '存储未初始化'}), 500

        logs = storage.get_schedule_flow_logs(order_no)

        return jsonify({
            'code': 0,
            'data': {
                'order_no': order_no,
                'total': len(logs),
                'logs': logs
            }
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500

@schedule_bp.route('/health', methods=['GET'])
def api_schedule_health():
    """排产服务健康检查"""
    try:
        storage = get_storage()
        if not storage:
            return jsonify({
                'code': 500,
                'status': 'unhealthy',
                'message': '存储未初始化'
            }), 500

        health = storage.health_check()
        records = storage.get_all_schedule_records()

        stats = {
            'total': len(records),
            'published': len([r for r in records if r.get('status') == 'published']),
            'waiting_schedule': len([r for r in records if r.get('status') == 'waiting_schedule']),
            'scheduled': len([r for r in records if r.get('status') == 'scheduled']),
            'confirmed': len([r for r in records if r.get('status') == 'confirmed']),
            'rejected': len([r for r in records if r.get('status') == 'rejected'])
        }

        return jsonify({
            'code': 0,
            'status': 'healthy',
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e), 'status': 'error'}), 500
