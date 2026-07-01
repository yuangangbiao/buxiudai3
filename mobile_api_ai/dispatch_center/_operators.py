# -*- coding: utf-8 -*-
"""
调度中心操作员工具层 (v3.6.1)

抽取 _get_operators / _get_department_members / _get_customer_group_for_order
等操作员相关函数到独立模块，集中缓存策略和管理逻辑。

设计原则:
1. 操作员数据统一管理
2. TTL 缓存避免频繁远程调用
3. 多级 fallback（5002 → v4 client → dispatch_cache）
4. 部门成员查询聚合

使用方式:
    from ._operators import get_operators
    from ._operators import get_department_members
    from ._operators import get_customer_group_for_order
"""
import os
import json
import time
import logging
import threading
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 缓存
# ═══════════════════════════════════════════════════════════════════════════════

_OPERATORS_CACHE = {'data': None, 'time': 0}
_OPERATORS_LOCK = threading.RLock()
OPERATORS_CACHE_TTL = 300  # 秒（5 分钟）

CUSTOMER_GROUP_CACHE_TTL = 300  # 秒
_customer_group_cache: Dict[str, Dict] = {}
_customer_group_lock = threading.RLock()


# ═══════════════════════════════════════════════════════════════════════════════
# 操作员查询
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_operators_from_5002() -> Dict[str, Dict]:
    """从容器中心 5002 /api/operators 获取操作员

    Returns:
        dict: {operator_id: {name, role, department}}
    """
    import requests
    operators_map = {}
    try:
        cc_api_key = (
            os.environ.get('CONTAINER_CENTER_API_KEY')
            or os.environ.get('API_KEY')
            or os.environ.get('WECHAT_CLOUD_API_KEY')
            or ''
        )
        cc_base = os.environ.get('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')
        headers = {'X-API-Key': cc_api_key} if cc_api_key else {}
        resp = requests.get(f'{cc_base}/api/operators', headers=headers, timeout=3)
        if resp.ok:
            data = resp.json()
            operators = data.get('data', []) if isinstance(data, dict) else data
            if isinstance(operators, list) and operators:
                for op in operators:
                    op_id = op.get('id') or op.get('operator_id', '')
                    if op_id:
                        operators_map[op_id] = {
                            'name': op.get('name', ''),
                            'role': op.get('role', ''),
                            'department': op.get('department', '') or op.get('team_name', ''),
                        }
                logger.debug(f'[Operators] 5002 直连返 {len(operators_map)} 个')
    except Exception as e:
        logger.warning(f'[Operators] 直接调 5002 /api/operators 失败: {e}')
    return operators_map


def _fetch_operators_from_v4_client() -> Dict[str, Dict]:
    """从 v4 client 获取操作员（fallback）

    Returns:
        dict: {operator_id: {name, role, department}}
    """
    operators_map = {}
    try:
        # 延迟导入避免循环
        from cloud_relay.v4_client import get_v4_client  # noqa
        client = get_v4_client()
        operators = client.get_operators() if client else []
        for op in operators:
            op_id = op.get('id') or op.get('operator_id', '')
            if op_id:
                operators_map[op_id] = {
                    'name': op.get('name', ''),
                    'role': op.get('role', ''),
                    'department': op.get('department', '') or op.get('team_name', ''),
                }
        if operators_map:
            logger.debug(f'[Operators] v4 client fallback 返 {len(operators_map)} 个')
    except Exception as e:
        logger.warning(f'[Operators] v4 client fallback 失败: {e}')
    return operators_map


def _fetch_operators_from_dispatch_cache() -> Dict[str, Dict]:
    """从 dispatch_cache 聚合操作员（最后 fallback）

    Returns:
        dict: {operator_id: {name, role, department}}
    """
    operators_map = {}
    try:
        from dispatch_center._db import get_dispatch_cache
        result = get_dispatch_cache().get_data()
        processes = result.get('processes', []) if isinstance(result, dict) else []
        for proc in processes:
            op_id = proc.get('target_operator') or proc.get('operator', '')
            if op_id and op_id not in operators_map:
                operators_map[op_id] = {
                    'name': proc.get('operator_name', op_id),
                    'role': proc.get('operator_role', '操作员'),
                    'department': proc.get('department', ''),
                }
    except Exception as e:
        logger.warning(f'[Operators] dispatch_cache fallback 失败: {e}')
    return operators_map


def get_operators() -> Dict[str, Dict]:
    """获取操作员列表（带内存缓存，TTL=300s）

    优先级:
        1. 直接调 5002 /api/operators（含 department 字段）
        2. v4 client.get_operators()（fallback）
        3. dispatch_cache process_tasks 聚合（最后 fallback）

    Returns:
        dict: {operator_id: {name, role, department}}
    """
    with _OPERATORS_LOCK:
        now = time.time()
        if (_OPERATORS_CACHE['data'] is not None
                and (now - _OPERATORS_CACHE['time']) < OPERATORS_CACHE_TTL):
            return _OPERATORS_CACHE['data']

        # 1. 5002 直连
        operators_map = _fetch_operators_from_5002()
        # 2. v4 client fallback
        if not operators_map:
            operators_map = _fetch_operators_from_v4_client()
        # 3. dispatch_cache fallback
        if not operators_map:
            operators_map = _fetch_operators_from_dispatch_cache()

        _OPERATORS_CACHE['data'] = operators_map
        _OPERATORS_CACHE['time'] = now
        return operators_map


def get_operator_info(operator_id: str) -> Optional[Dict]:
    """获取单个操作员信息

    Args:
        operator_id: 操作员ID

    Returns:
        dict or None: {name, role, department}
    """
    if not operator_id:
        return None
    operators = get_operators()
    return operators.get(operator_id)


def get_operators_by_department(department_name: str) -> List[str]:
    """获取某部门的所有操作员ID

    Args:
        department_name: 部门名称

    Returns:
        list: 操作员ID列表
    """
    operators = get_operators()
    return [
        op_id for op_id, op_info in operators.items()
        if op_info.get('department') == department_name
    ]


def clear_operators_cache():
    """清空操作员缓存（强制下次重新拉取）"""
    with _OPERATORS_LOCK:
        _OPERATORS_CACHE['data'] = None
        _OPERATORS_CACHE['time'] = 0


# ═══════════════════════════════════════════════════════════════════════════════
# 部门成员
# ═══════════════════════════════════════════════════════════════════════════════

def get_department_members(department_name: str) -> List[str]:
    """获取部门成员

    数据源优先级:
        1. enterprise_structure.json (departments + users)
        2. operators 缓存的 department 字段 fallback

    Args:
        department_name: 部门名称

    Returns:
        list: 成员 userid 列表
    """
    members = _get_department_members_from_json(department_name)
    if members:
        return members

    # fallback: 从 operators 缓存聚合
    return get_operators_by_department(department_name)


def _get_department_members_from_json(department_name: str) -> List[str]:
    """从 enterprise_structure.json 读取部门成员"""
    try:
        # 延迟导入 DB_PATHS
        try:
            from core.config import DB_PATHS
            structure_file = DB_PATHS.get('enterprise_structure', '')
        except ImportError:
            structure_file = ''

        if not structure_file or not os.path.exists(structure_file):
            return []

        with open(structure_file, 'r', encoding='utf-8') as f:
            structure = json.load(f)
        departments = structure.get('departments', [])
        users = structure.get('users', [])

        dept_id = None
        for dept in departments:
            if dept.get('name') == department_name:
                dept_id = dept.get('id')
                break

        if dept_id:
            members = []
            for user in users:
                if dept_id in user.get('department', []):
                    members.append(user.get('userid', ''))
            return [m for m in members if m]
    except Exception as e:
        logger.warning(f'[Department] 获取部门成员失败(JSON): {e}')
    return []


def list_departments() -> List[Dict]:
    """列出所有部门

    Returns:
        list: [{id, name, member_count}, ...]
    """
    try:
        from core.config import DB_PATHS
        structure_file = DB_PATHS.get('enterprise_structure', '')
        if not structure_file or not os.path.exists(structure_file):
            return []
        with open(structure_file, 'r', encoding='utf-8') as f:
            structure = json.load(f)
        departments = structure.get('departments', [])
        users = structure.get('users', [])
        result = []
        for dept in departments:
            dept_id = dept.get('id')
            member_count = sum(
                1 for user in users
                if dept_id in user.get('department', [])
            )
            result.append({
                'id': dept_id,
                'name': dept.get('name', ''),
                'member_count': member_count,
            })
        return result
    except Exception as e:
        logger.warning(f'[Department] 列出部门失败: {e}')
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 客户组查询
# ═══════════════════════════════════════════════════════════════════════════════

def get_customer_group_for_order(order_no: str) -> str:
    """从本地表 orders_local 查询客户群(customer_group), 进程内缓存 5 分钟

    [P0-1 修复 2026-06-13] 原从 steel_belt.orders 跨库直查 → 改读 container_center.orders_local
    镜像表同步：通过 8008 sync_bridge 双写
    返回空字符串表示无数据/查询失败

    Args:
        order_no: 订单号

    Returns:
        str: 客户组名称
    """
    if not order_no:
        return ''

    # 检查缓存
    with _customer_group_lock:
        cached = _customer_group_cache.get(order_no)
        if cached is not None:
            if time.time() - cached['time'] < CUSTOMER_GROUP_CACHE_TTL:
                return cached['value']
            _customer_group_cache.pop(order_no, None)

    # 查询数据库
    try:
        from dispatch_center._db import _get_mysql_connection
        import pymysql
        conn = _get_mysql_connection()
        try:
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute(
                "SELECT customer_group FROM orders_local WHERE order_no = %s LIMIT 1",
                (order_no,))
            row = cur.fetchone()
            value = (row.get('customer_group') if row else '') or ''
            # 缓存结果
            with _customer_group_lock:
                _customer_group_cache[order_no] = {'value': value, 'time': time.time()}
            return value
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f'[CustomerGroup] 查询 {order_no} 失败: {e}')
        return ''


def clear_customer_group_cache(order_no: str = None):
    """清空客户组缓存

    Args:
        order_no: 指定订单号（None=清空全部）
    """
    with _customer_group_lock:
        if order_no:
            _customer_group_cache.pop(order_no, None)
        else:
            _customer_group_cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 向后兼容别名
# ═══════════════════════════════════════════════════════════════════════════════

# 旧代码使用 _get_operators / _get_department_members / _get_customer_group_for_order
_get_operators = get_operators
_get_department_members = get_department_members
_get_customer_group_for_order = get_customer_group_for_order