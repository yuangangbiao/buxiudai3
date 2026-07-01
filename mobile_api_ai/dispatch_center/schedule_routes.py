# -*- coding: utf-8 -*-
"""
排产流程模块
支持从工单发布到排产确认的完整流程
"""
import logging
import json
import os
import time
import requests
from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import Dict, List, Optional
import uuid

from core.config import DB_PATHS, DB_CONNECT_TIMEOUT, REQUEST_TIMEOUT_QUICK, REQUEST_TIMEOUT_FAST
from template_engine import _render_template

logger = logging.getLogger(__name__)


# [v3.6.1 重构 2026-06-20] _get_mysql_connection 已抽取到 _db.py
# 之前：schedule_routes.py 单独调用 _get_mysql_connection() 但本地未定义 → NameError
# 现在：直接从 ._db 统一引用，避免重复定义
from ._db import _get_mysql_connection  # noqa: F401


schedule_bp = Blueprint('schedule', __name__, url_prefix='/api/schedule')
workorder_bp = Blueprint('workorder', __name__, url_prefix='/api/workorder')

# [缓存 2026-06-15] 排产列表缓存
_SCHEDULE_LIST_CACHE = {
    'data': None,       # 缓存的排产列表数据
    'time': 0,          # 缓存时间戳
    'ttl': 10,          # TTL 10秒
}
_MYSQL_CACHE = {
    'data': None,
    'time': 0,
    'ttl': 10,
}

def _clear_schedule_cache():
    """清除排产列表缓存"""
    _SCHEDULE_LIST_CACHE['data'] = None
    _SCHEDULE_LIST_CACHE['time'] = 0

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
    """获取存储实例，容器集成不可用时回退到本地 SQLite 存储"""
    integration = get_container_integration()
    if integration and integration.is_available:
        return integration._container_center.storage
    from mobile_api_ai.storage_layer import StorageFactory, StorageType, resolve_storage_type
    default_st = resolve_storage_type()
    storage = StorageFactory.get_instance(default_st)
    if storage:
        return storage
    try:
        storage = StorageFactory.create(default_st)
        logger.info(f"[Schedule] 已创建 {default_st.name} 存储")
        return storage
    except Exception as e:
        logger.error(f"[Schedule] 创建 {default_st.name} 存储失败: {e}")
        return None


def generate_schedule_id(prefix: str = 'SCH') -> str:
    """生成排产记录ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique = str(uuid.uuid4())[:4].upper()
    return f"{prefix}-{timestamp}-{unique}"

def get_wechat_bot():
    """获取微信机器人实例"""
    try:
        from bots.factory import get_factory
        factory = get_factory()
        bot = factory.get_group_bot()
        if bot:
            return bot
    except ImportError as e:
        logger.error(f"无法导入群机器人实例: {e}")
        return None
    except Exception as e:
        logger.error(f"获取群机器人实例失败: {e}")
        return None


def _send_app_broadcast(content: str, endpoint: str = '') -> None:
    """
    RE-004: 统一走云端 5006 推 @all App 消息
    失败仅 log，不阻断主业务
    endpoint 为空时自动从调用栈推断
    """
    if not endpoint:
        import inspect
        try:
            frame = inspect.currentframe().f_back
            endpoint = frame.f_code.co_name if frame else 'unknown'
        except Exception:
            endpoint = 'unknown'
    try:
        from cloud_poller import send_to_cloud, get_cloud_poller
        if get_cloud_poller() is None:
            return
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
        import threading

        _broadcast_result = {'error': None}

        def _do_broadcast():
            try:
                send_to_cloud(
                    to_user='@all',
                    content=content,
                    msg_type='markdown',
                    bot_type='app',
                    route_tag='wechat_message',
                )
            except Exception as e:
                _broadcast_result['error'] = e

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_do_broadcast)
            try:
                future.result(timeout=10)
            except FuturesTimeoutError:
                logger.warning(f"[{endpoint}] App @all 消息发送超时（10秒），已跳过")
            except Exception as e:
                if _broadcast_result['error']:
                    logger.warning(f"[{endpoint}] App @all 消息发送失败: {_broadcast_result['error']}")
    except Exception as e:
        logger.warning(f"[{endpoint}] App @all 消息发送失败: {e}")

def get_main_system_db_connection():
    """获取主系统数据库连接"""
    try:
        from models.database import get_connection
        return get_connection()
    except Exception as e:
        logger.error(f"获取主系统数据库连接失败: {e}")
        return None


def get_customer_from_group(order_no: str) -> str:
    """
    获取客户群名称, 走 [_core._get_customer_group_for_order] 5min LRU 缓存版
    [F6 P9 2026-06-10] 改走缓存, 减少直连钢带库次数
    原实现: 直连 3 次 SQL (production_orders / orders / 前缀匹配)
    改后: 1 次 SELECT, 5 分钟内缓存命中 0 跨库

    Args:
        order_no: 订单号

    Returns:
        客户群名称, 如果未找到返回'待定'
    """
    if not order_no:
        return '待定'
    try:
        from dispatch_center._core import _get_customer_group_for_order
        val = _get_customer_group_for_order(order_no)
        return val if val else '待定'
    except Exception as e:
        logger.error(f"获取客户群失败: {order_no}: {e}")
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
    conn = None

    try:
        conn = get_main_system_db_connection()
        if not conn:
            return order_info

        cursor = conn.cursor(pymysql.cursors.DictCursor)

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

    except Exception as e:
        logger.error(f"从主系统数据库获取订单信息失败: {e}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

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

        # 检查是否已存在相同订单的排产记录
        existing_records = storage.get_schedule_records_by_order(order_no)
        is_already_published = len(existing_records) > 0
        if is_already_published:
            logger.info(f"[Schedule] 工单已存在，将重新发布: {order_no}")

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

        def _do_post_publish():
            try:
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
                            _notify_dispatch_center_new_task(
                                order_no, order_no, task_id,
                                process=task_content.get('process_name', ''),
                                operator_id='SYSTEM',
                                operator_name=task_content.get('operator_name', ''),
                                quantity=quantity
                            )
                        else:
                            logger.warning(f"[Schedule] 任务发布到容器中心失败: {result.get('message')}")
                    except Exception as e:
                        logger.error(f"[Schedule] 任务发布到容器中心异常: {e}")
                else:
                    logger.warning("[Schedule] 容器中心客户端未初始化，跳过任务发布")

                bot = get_wechat_bot()
                if bot:
                    try:
                        cn = data.get('customer_name', get_customer_from_group(order_no))
                        message = f"""📋 **新工单发布**

---
**📋 工单**: `{order_no}`
**🏭 客户**: {cn}
**📦 产品**: {product_name}
**🎯 数量**: {quantity} {unit}
**📅 交期**: {delivery_date or '待定'}
**⭐ 优先级**: {data.get('priority', 'normal')}
**⏰ 发布时间**: {now}

---
请生产部门尽快制定排产计划！"""
                        try:
                            bot.send_markdown(message)
                        except Exception as e:
                            logger.warning(f"[Schedule] 发送微信通知失败: {e}")
                        _send_app_broadcast(message)
                    except Exception:
                        pass
            except Exception:
                pass

        import threading as _threading
        _t = _threading.Thread(target=_do_post_publish, daemon=True)
        _t.start()

        # 在调度中心流程编排中注册工单
        try:
            register_data = {
                'customer_name': customer_name,
                # [F6 P9 2026-06-10] 兜底走缓存版, 修调度中心 customer_group 显示空
                'customer_group': main_system_order_info.get('customer_group', '') or get_customer_from_group(order_no),
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
                timeout=REQUEST_TIMEOUT_QUICK
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

        if is_already_published:
            logger.info(f"[Schedule] 工单已发布，已重新推送消息: {order_no}")
            _clear_schedule_cache()
            return jsonify({
                'code': 0,
                'message': '工单已发布',
                'data': {
                    'schedule_id': schedule_id,
                    'status': SCHEDULE_STATUS['PUBLISHED'],
                    'published_at': now,
                    'already_published': True,
                }
            })
        else:
            _clear_schedule_cache()
            return jsonify({
                'code': 0,
                'message': '工单发布成功',
                'data': {
                    'schedule_id': schedule_id,
                    'status': SCHEDULE_STATUS['PUBLISHED'],
                    'published_at': now,
                    'already_published': False,
                }
            })

    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)}), 500


def _notify_dispatch_center_new_task(order_no: str, task_id: str,
                                      process: str = '', operator_id: str = '',
                                      operator_name: str = '', quantity: str = ''):
    """
    主动通知调度中心有新任务到达

    Args:
        order_no: 订单号
        order_no: 订单号
        task_id: 容器中心任务ID
        process: 工序名称
        operator_id: 操作员ID
        operator_name: 操作员名称
        quantity: 数量
    """
    try:
        dispatch_notify_data = {
            'event_type': 'task_published',
            'task_id': task_id,
            'process': process,
            'operator_id': operator_id,
            'operator_name': operator_name,
            'quantity': quantity,
            'source': 'container_center',
            'timestamp': datetime.now().isoformat()
        }
        resp = requests.post(
            f'{_DISPATCH_CENTER_URL}/api/dispatch-center/task-notify',
            json=dispatch_notify_data,
            timeout=REQUEST_TIMEOUT_FAST
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

                message = _render_template('tmpl_schedule_notify', {
                    '订单号': order_no,
                    '产品': record.get('product_name', ''),
                    '数量': record.get('quantity', 0),
                    '截止时间': data.get('schedule_required_by', '尽快'),
                })
                bot.send_markdown(message)
            except Exception as e:
                logger.warning(f"[Schedule] 发送微信通知失败: {e}")
            # RE-004: 推 @all App 消息（统一走云端 5006）
            _send_app_broadcast(message)

        _clear_schedule_cache()
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
                message = _render_template('tmpl_schedule_submitted', {
                    '订单号': order_no,
                    '客户': customer_name,
                    '产品': record.get('product_name', ''),
                    '数量': record.get('quantity', 0),
                    '单位': record.get('unit', '件'),
                    '提交部门': data.get('submitted_by', '生产部'),
                    '提交时间': now,
                    '排产明细': processes_text,
                    '预计完成': schedule.get('estimated_complete', '待定'),
                    '总天数': schedule.get('total_days', '待定'),
                })
                bot.send_markdown(message)
            except Exception as e:
                logger.warning(f"[Schedule] 发送微信通知失败: {e}")
            # RE-004: 推 @all App 消息（统一走云端 5006）
            _send_app_broadcast(message)

        _clear_schedule_cache()
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
                customer_name = record.get('customer_name', get_customer_from_group(order_no))
                order_no = record.get('order_no', order_no)
                if result == 'confirmed':
                    from mobile_api_ai.wechat_msg_dispatcher import send_templated
                    from bots.base import BotType
                    plan_start_str = data.get('plan_start', record.get('plan_start', ''))
                    plan_end_str = data.get('plan_end', record.get('plan_end', ''))
                    days = ''
                    if plan_start_str and plan_end_str:
                        try:
                            from datetime import datetime as dt
                            s = dt.strptime(str(plan_start_str), '%Y-%m-%d')
                            e = dt.strptime(str(plan_end_str), '%Y-%m-%d')
                            days = (e - s).days
                        except Exception:
                            pass
                    send_templated(
                        scenario='process_schedule_confirmed',
                        context={
                            '订单号': order_no,
                            '客户': customer_name,
                            '产品': record.get('product_name', ''),
                            '数量': record.get('quantity', 0),
                            '单位': record.get('unit', '件'),
                            '开始日期': plan_start_str,
                            '结束日期': plan_end_str,
                            '工期': f'{days} 天' if days else '',
                            '确认人': data.get('confirmed_by', '桌面用户'),
                            '确认时间': now,
                        },
                        bot_type=BotType.APP,
                    )
                else:
                    from mobile_api_ai.wechat_msg_dispatcher import send_templated
                    from bots.base import BotType
                    send_templated(
                        scenario='process_schedule_rejected',
                        context={
                            '订单号': order_no,
                            '客户': customer_name,
                            '产品': record.get('product_name', ''),
                            '数量': record.get('quantity', 0),
                            '单位': record.get('unit', '件'),
                            '拒绝人': data.get('confirmed_by', '桌面用户'),
                            '拒绝原因': data.get('comments') or data.get('reason', '未说明'),
                            '拒绝时间': now,
                        },
                        bot_type=BotType.APP,
                    )
            except Exception as e:
                logger.warning(f"[Schedule] 发送微信通知失败: {e}")

        _clear_schedule_cache()
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

@schedule_bp.route('/list', methods=['GET'])
def api_get_schedule_list():
    """获取工单排产列表（从本地存储 + MySQL 兜底获取）

    [优化 2026-06-12] SQL 层分页和过滤，替代原来全量加载 + Python 层过滤/去重/分页
    [优化 2026-06-15] 添加缓存机制，提升响应速度
    """
    try:
        storage = get_storage()
        status_filter = request.args.get('status')
        filter_order_no = request.args.get('orderNo', '').strip()
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))

        # [优化] SQL 层分页
        offset = (page - 1) * page_size

        # [缓存 2026-06-15] 精确搜索时不使用缓存
        if not filter_order_no and not status_filter and page == 1 and page_size == 20:
            now = time.time()
            if _SCHEDULE_LIST_CACHE['data'] is not None and (now - _SCHEDULE_LIST_CACHE['time']) < _SCHEDULE_LIST_CACHE['ttl']:
                logger.debug(f"[缓存] schedule/list 命中 TTL={_SCHEDULE_LIST_CACHE['ttl']}s")
                return jsonify({
                    'code': 0,
                    'data': _SCHEDULE_LIST_CACHE['data']
                })

        records = []
        if storage:
            # [优化] 传递 status 参数，SQL 层过滤
            if filter_order_no:
                # 精确搜索时，使用原有的 search 参数
                records = storage.get_process_records(search=filter_order_no, limit=page_size, offset=offset)
            else:
                records = storage.get_process_records(status=status_filter, limit=page_size, offset=offset)

        # 兜底：如果本地存储为空，尝试 MySQL
        if not records:
            records = _query_mysql_workorders(status_filter)

        if not records:
            return jsonify({'code': 0, 'data': [], 'total': 0, 'page': page, 'page_size': page_size})

        # [修复 2026-06-12] SQL ROW_NUMBER() 已实现去重，直接遍历 records
        # 原来 Python 层的 seen{} 去重逻辑已删除
        result = []
        for r in records:
            order_no = r.get('order_no', '') or r.get('workOrderNo', '')
            if not order_no:
                continue
            content = r.get('content') or {}
            if isinstance(content, str):
                try:
                    import json
                    content = json.loads(content)
                except Exception:
                    content = {}
            plan_start = r.get('plan_start', '') or content.get('plan_start', '')
            plan_end = r.get('plan_end', '') or content.get('plan_end', '')
            result.append({
                'workOrderNo': order_no,
                'orderNo': r.get('order_no', '') or r.get('orderNo', ''),
                'customerGroup': r.get('customer_group', '') or r.get('customerGroup', '') or r.get('customer_group_name', ''),
                'customerName': r.get('customer_name', '') or r.get('customerName', ''),
                'productType': r.get('product_name', '') or r.get('productName', '') or r.get('product_type', ''),
                'productName': r.get('product_name', '') or r.get('productName', ''),
                'quantity': r.get('quantity', 0) or r.get('orderQty', 0),
                'orderQty': r.get('quantity', 0) or r.get('orderQty', 0),
                'status': r.get('status', 'pending'),
                'createTime': r.get('created_at', '') or r.get('createTime', '') or r.get('createdAt', ''),
                'created_at': r.get('created_at', '') or r.get('createTime', ''),
                'order_no': order_no,
                'product_type': r.get('product_name', '') or r.get('product_type', ''),
                'customer_group': r.get('customer_group', '') or r.get('customer_group_name', ''),
                'plan_start': plan_start,
                'plan_end': plan_end
            })

        # [缓存 2026-06-15] 更新缓存（无筛选条件时）
        if not filter_order_no and not status_filter and page == 1 and page_size == 20:
            _SCHEDULE_LIST_CACHE['data'] = result
            _SCHEDULE_LIST_CACHE['time'] = time.time()
            logger.debug(f"[缓存] schedule/list 更新缓存, TTL={_SCHEDULE_LIST_CACHE['ttl']}s")

        return jsonify({
            'code': 0,
            'data': result
        })

    except Exception as e:
        logger.error('获取排产列表异常: %s', e)
        return jsonify({'code': 500, 'message': str(e)}), 500


# ═══════════════════════════════════════════════
# 工单确认排产（来自晨圣报工前端）
# ═══════════════════════════════════════════════

@workorder_bp.route('/confirm_schedule', methods=['POST'])
def api_workorder_confirm_schedule():
    """
    晨圣报工排产确认 API
    接收排产日期，推进工单进入"生产中"状态

    请求体:
    {
        "order_no": "ORD-xxx",
        "plan_start": "2025-06-01",
        "plan_end": "2025-06-10"
    }
    """
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}

    order_no = data.get('order_no', '')
    plan_start = data.get('plan_start', '')
    plan_end = data.get('plan_end', '')

    if not order_no:
        return jsonify({'code': 1001, 'success': False, 'message': '缺少order_no'})

    # 防重复：确认订单在 MySQL 中存在
    # SSOT: 使用本地 orders_local 表验证订单存在
    storage = get_storage()
    if not storage:
        return jsonify({'code': 500, 'success': False, 'message': '存储未初始化'})

    order_local = storage.get_order_local(order_no)
    if not order_local:
        return jsonify({'code': 404, 'success': False, 'message': f'订单 {order_no} 不存在'})

    # 查找流程记录（精确匹配 order_no）
    record = None
    try:
        records = storage.get_process_records(search=order_no)
        if records:
            for r in records:
                if r.get('order_no') == order_no:
                    record = r
                    logger.info(f'[confirm_schedule] 找到流程记录: id={record.get("id")}, status={record.get("status")}')
                    break
        if not record:
            logger.warning(f'[confirm_schedule] 未找到流程记录: {order_no}')
    except Exception as e:
        logger.warning('查找流程记录异常: %s', e)

    # 计算排产天数
    schedule_days = 0
    if plan_start and plan_end:
        try:
            start = datetime.strptime(plan_start, '%Y-%m-%d')
            end = datetime.strptime(plan_end, '%Y-%m-%d')
            schedule_days = (end - start).days
            if schedule_days < 0:
                schedule_days = 0
        except ValueError:
            schedule_days = 0

    # 无论本地是否有记录，都同步到调度中心
    try:
        # 注册工单到调度中心（幂等，已存在则更新）
        dispatch_url = os.environ.get('DISPATCH_CENTER_URL', 'http://127.0.0.1:5003')

        register_data = {
            'order_no': data.get('order_no', order_no),
            'customer_name': data.get('customer_name', ''),
            'customer_group': data.get('customer_group', ''),
            'product_name': data.get('product_name', ''),
            'quantity': data.get('quantity', 1),
            'unit': data.get('unit', '米'),
            'delivery_date': data.get('delivery_date', ''),
            'priority': 'normal',
            'flow_type': 'production',
        }
        # 如果有本地记录，补充更多字段
        if record:
            register_data['order_no'] = record.get('order_no', register_data['order_no'])
            register_data['customer_name'] = record.get('customer_name', register_data['customer_name'])
            # [F6 P9 2026-06-10] 补 customer_group 兜底, 修确认排产时 customer_group 显示空
            register_data['customer_group'] = record.get('customer_group') or get_customer_from_group(order_no) or register_data['customer_group']
            register_data['product_name'] = record.get('product_name', record.get('product_type', register_data['product_name']))
            register_data['quantity'] = record.get('quantity', register_data['quantity'])
            register_data['unit'] = record.get('unit', register_data['unit'])
            register_data['delivery_date'] = record.get('delivery_date', register_data['delivery_date'])

        resp = requests.post(
            f'{dispatch_url}/api/dispatch-center/workorder/register',
            json=register_data,
            timeout=3
        )
        if resp.ok:
            logger.info(f'调度中心工单注册成功: {order_no}')

            # SSOT: dispatch_cache 从 process_records 读取状态，不再单独存储
            # 触发重新加载缓存（下次查询时会从 DB 获取最新状态）
            try:
                from dispatch_center._core import _dispatch_cache
                _dispatch_cache._cache = None  # 清空内存缓存
                _dispatch_cache._cache_time = 0  # 重置缓存时间
                logger.info(f'[confirm_schedule] 已清空 dispatch_cache 内存缓存: {order_no}')
            except Exception as e:
                logger.warning(f'[confirm_schedule] 重置 dispatch_cache TTL 失败: {e}')
        else:
            logger.warning(f'调度中心工单注册失败: {resp.status_code} {resp.text}')

        # 第二步：状态通过 8008 桥接同步，此处跳过（避免 405 错误）
    except Exception as e:
        logger.warning('同步到调度中心失败: %s', e)

    # 如有本地记录，更新本地存储
    if record:
        try:
            record['status'] = 'in_production'
            record['plan_start'] = plan_start
            record['plan_end'] = plan_end
            _content = record.get('content')
            if isinstance(_content, str):
                try:
                    _content = json.loads(_content)
                except (json.JSONDecodeError, TypeError):
                    _content = {}
            if not isinstance(_content, dict):
                _content = {}
            _content['plan_start'] = plan_start
            _content['plan_end'] = plan_end
            _content['schedule_days'] = schedule_days
            record['content'] = _content
            record['status'] = 'in_production'
            record['current_step'] = 2
            record['updated_at'] = datetime.now().isoformat()

            storage.save_process_record(record)
        except Exception as e:
            logger.warning('保存本地记录失败: %s', e)
    else:
        logger.info(f'本地无流程记录，已直接同步到调度中心: {order_no}')

    # 通过 sync_bridge 同步到所有下游系统
    try:
        sync_url = os.environ.get('SYNC_BRIDGE_URL', 'http://127.0.0.1:8008')
        requests.post(
            f'{sync_url}/api/sync/status-change',
            json={
                'order_no': order_no,
                'status_key': 'in_production',
                'plan_start': plan_start,
                'plan_end': plan_end,
                'schedule_days': schedule_days,
                'source': 'schedule_flow.confirm_schedule'
            },
            timeout=3
        )
    except Exception as e:
        logger.warning('通过 sync_bridge 同步状态失败: %s', e)

    # SSOT: 直接使用 storage 统一更新 process_records 表状态
    try:
        affected = 0
        if hasattr(storage, 'update_order_status'):
            record = storage.get_process_record_by_order(order_no)
            if record:
                record['status'] = 'in_production'
                record['plan_start'] = plan_start
                record['plan_end'] = plan_end
                storage.save_process_record(record)
                affected = 1
        if affected > 0:
            logger.info(f'[confirm_schedule] SSOT 状态更新成功: {order_no} status=in_production, plan={plan_start}~{plan_end}')
        else:
            logger.warning(f'[confirm_schedule] process_records 表无变化或订单不存在: {order_no}')
    except Exception as e:
        logger.warning(f'[confirm_schedule] process_records 表更新失败: {e}')

    return jsonify({
        'code': 0, 'success': True,
        'message': f'排产确认成功，工单已进入生产中: {order_no}',
        'data': {
            'order_no': order_no,
            'plan_start': plan_start,
            'plan_end': plan_end,
            'schedule_days': schedule_days,
            'status': 'in_production'
        }
    })

    # RE-004: 排产确认成功 → 推群 + @all App（已 /notify 模板变体）
    try:
        bot = get_wechat_bot()
        if bot:
            _msg = _render_template('tmpl_schedule_confirmed', {
                '订单号': order_no,
                '开始日期': plan_start or '待定',
                '结束日期': plan_end or '待定',
                '工期': f'{schedule_days} 天',
                '确认人': '系统',
                '时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            })
            bot.send_markdown(_msg)
    except Exception as e:
        logger.warning(f"[workorder_bp] /confirm_schedule 群消息失败: {e}")

    try:
        from cloud_poller import send_to_cloud, get_cloud_poller
        if get_cloud_poller() is not None:
            send_to_cloud(
                to_user='@all',
                content=_msg,
                msg_type='markdown',
                bot_type='app',
                route_tag='wechat_message',
            )
    except Exception as e:
        logger.warning(f"[workorder_bp] /confirm_schedule App 消息失败: {e}")


def _query_mysql_workorders(status=None):
    """从本地表 process_records_local 查询工单数据（兜底数据源）

    [优化 2026-06-12] 直接查 process_records.order_no，不跨库 JOIN production_orders
    [P0-1 修复 2026-06-13] 改读 container_center.process_records_local
    镜像表同步：通过 8008 sync_bridge 双写
    [修复 2026-06-15] 添加查询超时，防止慢查询阻塞
    """
    try:
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT
        conn = _get_mysql_connection()  # [T5 2026-06-14]
        try:
            c = conn.cursor()
            # [修复 2026-06-15] 设置查询超时为 5 秒（MySQL 8.0+）
            try:
                c.execute("SET SESSION MAX_EXECUTION_TIME=5000")
            except Exception:
                pass  # 旧版本 MySQL 不支持 MAX_EXECUTION_TIME
            # [优化] 字段裁剪，减少网络传输，使用 LIMIT 限制返回
            query = "SELECT id, order_no, product_name, quantity, unit, customer_name, status, created_at, updated_at FROM process_records_local WHERE order_no IS NOT NULL AND order_no != ''"
            params = []
            if status:
                query += " AND status = %s"
                params.append(status)
            query += " ORDER BY created_at DESC LIMIT 100"  # [修复 2026-06-15] 减少 LIMIT 从 200 到 100
            c.execute(query, params)
            rows = c.fetchall()
            return rows
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"[Schedule] 本地表查询工单数据失败（非致命）: {e}")
        return []

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


@schedule_bp.route('/backfill-flow-type', methods=['POST'])
def api_backfill_flow_type():
    """回填 process_records 表的 flow_type 字段"""
    import pymysql

    conn = None
    try:
        conn = _get_mysql_connection()  # [T5 2026-06-14]
        cur = conn.cursor()
        try:
            cur.execute("ALTER TABLE process_records ADD COLUMN flow_type VARCHAR(100) DEFAULT 'production'")
            conn.commit()
            logger.info('[回填] flow_type 列已添加')
        except Exception as e:
            if 'Duplicate' in str(e):
                logger.info('[回填] flow_type 列已存在')
            else:
                raise

        cur.execute("""
            UPDATE process_records
            SET flow_type = COALESCE(
                JSON_UNQUOTE(JSON_EXTRACT(content, '$.flow_type')),
                'production'
            )
            WHERE flow_type IS NULL OR flow_type = ''
        """)
        conn.commit()
        affected = cur.rowcount
        logger.info('[回填] 回填 %d 条', affected)

        cur.execute("SELECT COUNT(*) FROM process_records")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM process_records WHERE flow_type IS NOT NULL AND flow_type != ''")
        filled = cur.fetchone()[0]

        cur.close()
        conn.close()

        _clear_schedule_cache()
        return jsonify({
            'code': 0,
            'message': '回填完成',
            'data': {'total': total, 'filled': filled, 'affected': affected}
        })
    except Exception as e:
        logger.warning('[回填] 失败: %s', e)
        if conn:
            conn.close()
        return jsonify({'code': 500, 'message': str(e)}), 500


# ── 根路由（/api/schedule 和 /api/workorder）──
@schedule_bp.route('/', methods=['GET'])
def schedule_root():
    """排班模块根路由"""
    return jsonify({
        'code': 0,
        'module': 'schedule',
        'endpoints': [
            '/publish', '/notify', '/submit', '/confirm',
            '/status/<order_no>', '/list', '/pending',
            '/history/<order_no>', '/health', '/backfill-flow-type'
        ]
    })


@workorder_bp.route('/', methods=['GET'])
def workorder_root():
    """工单模块根路由"""
    return jsonify({
        'code': 0,
        'module': 'workorder',
        'endpoints': ['/confirm_schedule']
    })
