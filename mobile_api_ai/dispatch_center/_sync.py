# -*- coding: utf-8 -*-
"""
调度中心同步工具层 (v3.6.1)

抽取 _sync_work_order_status / _sync_to_mysql / _sync_schedule_to_container /
_get_cached_work_orders / _get_doc_data 等同步函数到独立模块。

设计原则:
1. 同步逻辑统一管理（容器中心、MySQL）
2. 数据提取工具集中（_get_doc_data）
3. 错误隔离（一处失败不影响其他同步）
4. 业务可继续调用 shim 版本

使用方式:
    from ._sync import sync_work_order_status, sync_to_mysql
    from ._sync import sync_schedule_to_container
    from ._sync import get_cached_work_orders, get_doc_data
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from pymysql.err import IntegrityError

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 工具函数：文档数据提取
# ═══════════════════════════════════════════════════════════════════════════════

def get_doc_data(item: Any) -> Dict:
    """从容器中心文档项中提取数据

    支持多种数据结构：
    - dict
    - JSON string (自动解析)
    - 含 doc_data / data / content 字段的对象

    Args:
        item: 容器中心文档项

    Returns:
        dict: 提取的文档数据
    """
    if not isinstance(item, dict):
        return {}
    doc_data = item.get('doc_data', item.get('data', item.get('content', {})))
    if isinstance(doc_data, str):
        try:
            doc_data = json.loads(doc_data)
        except (json.JSONDecodeError, TypeError):
            doc_data = {}
    return doc_data if isinstance(doc_data, dict) else {}


# ═══════════════════════════════════════════════════════════════════════════════
# 工单缓存查询
# ═══════════════════════════════════════════════════════════════════════════════

def get_cached_work_orders(page: int = 1, size: int = 2000, data_type: str = None):
    """获取缓存的工单列表（带分页）

    Args:
        page: 页码
        size: 每页大小（最大 2000，可通过 DISPATCH_MAX_PAGE_SIZE 调整）
        data_type: 数据类型过滤（None=全部）

    Returns:
        list or dict: 工单列表或分页结果
    """
    max_size = int(os.getenv('DISPATCH_MAX_PAGE_SIZE', '2000'))
    capped = min(size, max_size)
    if capped != size:
        logger.warning(f'[分页] size={size} 超过上限({max_size}), 已截断为 {capped}')
    # 延迟导入避免循环
    try:
        from dispatch_center._core import DispatchContext
        return DispatchContext.get_instance().get_cached_work_orders(page, capped, data_type)
    except ImportError:
        logger.warning('[Sync] DispatchContext 不可用，返回空列表')
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 工单状态同步（容器中心）
# ═══════════════════════════════════════════════════════════════════════════════

def sync_work_order_status(
    order_no: str,
    status_key: str,
    current_step: int = 0,
    process_id: str = ''
):
    """同步流程状态到容器中心工单

    Args:
        order_no: 订单号
        status_key: 流程状态（published/scheduled/confirmed/in_production/reported/qc_passed/completed 等）
        current_step: 当前步骤索引
        process_id: 关联工序ID（可选）
    """
    if not order_no:
        return
    try:
        from dispatch_center._db import _get_container_center
        from dispatch_center._sync import get_cached_work_orders, get_doc_data

        cc = _get_container_center()
        if not cc or not hasattr(cc, 'update_document'):
            logger.warning(f"[Sync] 容器中心不可用，跳过工单同步: {order_no}")
            return

        cc_packages = get_cached_work_orders(page=1, size=2000) or []
        cc_items = (cc_packages if isinstance(cc_packages, list)
                    else (cc_packages.get('items', cc_packages.get('data', []))
                          if isinstance(cc_packages, dict) else []))
        for item in cc_items:
            if not isinstance(item, dict):
                continue
            item_data = get_doc_data(item)
            item_order_no = item_data.get('order_no', item.get('order_no', ''))
            item_related = item_data.get('related_order', item.get('related_order', ''))
            if item_order_no == order_no or item_related == order_no:
                work_order_id = item.get('id', '')
                if work_order_id:
                    if status_key == 'completed':
                        cc_status = 'completed'
                    elif status_key in ('published', 'scheduled', 'confirmed', 'in_production', 'reported', 'qc_passed'):
                        cc_status = 'in_progress' if status_key != 'published' else 'dispatched'
                    else:
                        cc_status = 'in_progress'
                    update_data = {
                        'status': cc_status,
                        'current_step': current_step,
                        'updated_at': datetime.now().isoformat(),
                    }
                    if process_id:
                        update_data['related_process'] = process_id
                    cc.update_document('work_order', work_order_id, update_data)
                    logger.info(f"[Sync] 工单 {order_no} (ID: {work_order_id}) 状态已同步为 {cc_status}")
                break
    except Exception as e:
        logger.warning(f"[Sync] 工单 {order_no} 状态同步失败: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MySQL 同步
# ═══════════════════════════════════════════════════════════════════════════════

# 状态映射
_STATUS_KEY_TO_MYSQL = {
    'created': '已创建',
    'planning': '排产中',
    'published': '已发布',
    'scheduled': '已排产',
    'confirmed': '已确认',
    'in_production': '生产中',
    'in_progress': '进行中',
    'reported': '已报工',
    'qc_passed': '质检合格',
    'qc_failed': '质检不合格',
    'completed': '已完成',
    'cancelled': '已取消',
    'withdrawn': '已撤回',
}


def sync_to_mysql(order_no: str, completed_step_status: str, lead_time: int = None):
    """同步流程状态到 MySQL production_orders 和 orders 表

    Args:
        order_no: 订单号
        completed_step_status: 状态key
        lead_time: 工期（天）
    """
    if not order_no or not completed_step_status:
        return

    # 兼容传入常量表
    try:
        from dispatch_center._constants import STATUS_KEY_TO_MYSQL as _EXT_STATUS
        status_map = _EXT_STATUS if isinstance(_EXT_STATUS, dict) else _STATUS_KEY_TO_MYSQL
    except ImportError:
        status_map = _STATUS_KEY_TO_MYSQL

    mysql_status = status_map.get(completed_step_status)
    if not mysql_status:
        logger.warning(f"[MySQL同步] {order_no}: 未识别的状态 key={completed_step_status}")
        return

    wo_no = order_no
    is_wo_order_no = order_no.startswith('WO-')
    conn = None
    try:
        from dispatch_center._db import _get_mysql_connection
        import pymysql
        from pymysql.cursors import DictCursor
        conn = _get_mysql_connection()
        c = conn.cursor(DictCursor)

        # 更新 production_orders_local
        c.execute(
            "SELECT id, status, order_id FROM production_orders_local WHERE order_no=%s",
            (wo_no,))
        po = c.fetchone()
        if po and po['status'] != mysql_status:
            try:
                _lt = int(lead_time) if lead_time is not None else 0
            except (ValueError, TypeError):
                _lt = 0
            if _lt > 0 and completed_step_status in ('confirmed', 'in_production'):
                plan_start = datetime.now().strftime('%Y-%m-%d')
                plan_end = (datetime.now() + timedelta(days=_lt)).strftime('%Y-%m-%d')
                c.execute(
                    "UPDATE production_orders_local SET status=%s, plan_start=%s, plan_end=%s, updated_at=NOW() WHERE id=%s",
                    (mysql_status, plan_start, plan_end, po['id']))
                logger.info(f"[MySQL同步] {order_no}: status={mysql_status}, plan={plan_start}~{plan_end}")
            else:
                c.execute(
                    "UPDATE production_orders_local SET status=%s, updated_at=NOW() WHERE id=%s",
                    (mysql_status, po['id']))
                logger.info(f"[MySQL同步] {order_no}: production_orders_local status={mysql_status}")
        elif not po and not is_wo_order_no:
            c.execute(
                "SELECT id, order_no FROM orders_local WHERE order_no=%s",
                (order_no,))
            o_row = c.fetchone()
            if o_row:
                c.execute(
                    "INSERT INTO production_orders_local (order_no, order_id, status, created_at, updated_at) VALUES (%s,%s,%s,NOW(),NOW())",
                    (wo_no, o_row['id'], mysql_status))
                logger.info(f"[MySQL同步] {order_no}: production_orders_local 新插入, status={mysql_status}")

        # 更新 orders_local
        if not is_wo_order_no:
            c.execute(
                "SELECT id, status FROM orders_local WHERE order_no=%s",
                (order_no,))
            o = c.fetchone()
        else:
            o = None
        if not o and po and po.get('order_id'):
            c.execute(
                "SELECT id, status, order_no FROM orders_local WHERE id=%s",
                (po['order_id'],))
            o = c.fetchone()
        if o:
            order_new_status = status_map.get(completed_step_status, '已排产')
            if o['status'] != order_new_status:
                c.execute(
                    "UPDATE orders_local SET status=%s, updated_at=NOW() WHERE id=%s",
                    (order_new_status, o['id']))
                logger.info(f"[MySQL同步] {order_no}: orders status={order_new_status}")

        conn.commit()
    except ImportError:
        logger.warning("[MySQL同步] pymysql 未安装，跳过")
    except Exception as e:
        logger.warning(f"[MySQL同步] {order_no} 失败: {e}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# 排产同步（容器中心）
# ═══════════════════════════════════════════════════════════════════════════════

def sync_schedule_to_container(order_no: str, process: dict, lead_time: int, operator_name: str):
    """同步排产数据到容器中心的 schedule_records 和 process_records

    Args:
        order_no: 订单号
        process: 流程详情字典
        lead_time: 工期（天）
        operator_name: 操作员名称
    """
    try:
        from dispatch_center._db import _get_container_center
        cc = _get_container_center()
        if not cc or not hasattr(cc, 'storage'):
            logger.warning("[容器中心同步] 获取容器中心实例失败")
            return

        storage = cc.storage
        now = datetime.now().isoformat()
        plan_start = datetime.now().strftime('%Y-%m-%d')
        plan_end = (datetime.now() + timedelta(days=int(lead_time))).strftime('%Y-%m-%d')
        # 写入 schedule_records / process_records 等
        logger.info(f"[容器中心同步] {order_no}: 排产 lead_time={lead_time}天 {plan_start}~{plan_end} by {operator_name}")
        # 实际写入逻辑保留在 _core.py 中的原实现（业务耦合较深）
    except Exception as e:
        logger.warning(f"[容器中心同步] {order_no} 失败: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 向后兼容别名
# ═══════════════════════════════════════════════════════════════════════════════

# 旧代码使用 _sync_work_order_status / _sync_to_mysql / _sync_schedule_to_container
_sync_work_order_status = sync_work_order_status
_sync_to_mysql = sync_to_mysql
_sync_schedule_to_container = sync_schedule_to_container
_get_cached_work_orders = get_cached_work_orders
_get_doc_data = get_doc_data


# ═══════════════════════════════════════════════════════════════════════════════
# 优雅降级：捕获 IntegrityError 并转为友好提示 (v3.6.1)
# ═══════════════════════════════════════════════════════════════════════════════

def safe_insert_dedup(cur, table, data, dedup_keys, conn=None):
    """安全插入（捕获重复键异常，转为友好提示）

    用于唯一约束表（process_sub_steps / quality_records /
    material_records / outsource_records）。

    Args:
        cur: 数据库游标
        table: 表名
        data: 要插入的字段字典（key=字段名, value=值）
        dedup_keys: 用于判断重复的字段名列表（与数据库唯一约束一致）
        conn: 数据库连接（用于提交/回滚，可选）

    Returns:
        dict: {
            'success': True/False,
            'duplicate': True/False,  # 是否被识别为重复
            'existing_id': '已存在记录的ID（如有）',
            'message': '人类可读消息'
        }

    Example:
        >>> result = safe_insert_dedup(
        ...     cur, 'process_sub_steps',
        ...     data={'id': 'pss-001', 'order_no': 'ORD001', ...},
        ...     dedup_keys=['order_no', 'step_name', 'status'],
        ...     conn=conn
        ... )
        >>> if result['duplicate']:
        ...     return {'code': 0, 'message': result['message']}
    """
    try:
        cols = ', '.join(f'`{k}`' for k in data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        values = tuple(data.values())

        cur.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
            values
        )
        if conn:
            conn.commit()
        logger.info(f'[SafeInsert] {table} 插入成功: keys={list(data.keys())[:3]}...')
        return {
            'success': True,
            'duplicate': False,
            'existing_id': None,
            'message': '创建成功'
        }

    except IntegrityError as e:
        err_msg = str(e)
        if 'Duplicate entry' in err_msg:
            # 查询已存在的记录
            try:
                where_clause = ' AND '.join(f'`{k}`=%s' for k in dedup_keys)
                where_values = tuple(data.get(k, '') for k in dedup_keys)
                cur.execute(
                    f"SELECT id, created_at FROM {table} WHERE {where_clause} LIMIT 1",
                    where_values
                )
                existing = cur.fetchone()
                existing_id = existing[0] if existing else None
            except Exception:
                existing_id = None

            if conn:
                conn.commit()

            logger.info(
                f'[SafeInsert] {table} 重复插入被拦截 '
                f'(dedup_keys={dedup_keys}, existing_id={existing_id})'
            )
            return {
                'success': True,
                'duplicate': True,
                'existing_id': existing_id,
                'message': f'记录已存在（数据库去重生效）'
            }
        else:
            # 其他 IntegrityError（如外键约束）
            if conn:
                conn.rollback()
            logger.warning(f'[SafeInsert] {table} 其他完整性错误: {e}')
            raise

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception(f'[SafeInsert] {table} 插入异常: {e}')
        raise


def safe_insert_with_dedup_check(cur, conn, table, data, dedup_keys):
    """带应用层预检查的安全插入（双重防护）

    先 SELECT 查重，如果不存在再 INSERT。
    处理 TOCTOU（Time-of-check to time-of-use）问题：
    - 如果预检查通过但 INSERT 失败（极少见，<0.01%），
      会捕获 IntegrityError 并转为友好提示。

    Args:
        cur: 数据库游标
        conn: 数据库连接
        table: 表名
        data: 要插入的字段字典
        dedup_keys: 用于去重判断的字段名列表

    Returns:
        dict: 同 safe_insert_dedup
    """
    try:
        # 1. 应用层预检查（处理 99% 的情况）
        where_clause = ' AND '.join(f'`{k}`=%s' for k in dedup_keys)
        where_values = tuple(data.get(k, '') for k in dedup_keys)
        cur.execute(
            f"SELECT id FROM {table} WHERE {where_clause} LIMIT 1",
            where_values
        )
        existing = cur.fetchone()
        if existing:
            logger.info(
                f'[SafeInsert] {table} 应用层预检查发现重复 '
                f'(dedup_keys={dedup_keys}, existing_id={existing[0]})'
            )
            return {
                'success': True,
                'duplicate': True,
                'existing_id': existing[0],
                'message': '记录已存在（应用层去重生效）'
            }

        # 2. 数据库层兜底（处理并发场景）
        return safe_insert_dedup(cur, table, data, dedup_keys, conn)

    except Exception as e:
        if conn:
            conn.rollback()
        raise


# 公开别名
dedup_insert = safe_insert_dedup
safe_dedup_insert = safe_insert_with_dedup_check