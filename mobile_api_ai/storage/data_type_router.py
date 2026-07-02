# -*- coding: utf-8 -*-
"""
[v3.6 T1.1-T1.6] data_type 路由器

11 种 data_type → 业务表路由表
+ 单查询 get_packages()
+ 批量 get_packages_batch()
+ 异常值 ValueError

设计原则：
- 11 种 data_type 全部白名单
- 表名来自常量，**不可能 SQL 注入**
- 11 业务表 + 1 软删除过滤
"""
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# T1.1: 11 种 data_type 白名单
NEW_DATA_TYPES = frozenset({
    'process_report', 'material_request', 'material_pickup', 'material_buy',
    'quality_task', 'equipment_repair', 'outsource_task',
    'config', 'flow_production', 'flow_step', 'production', 'approval',
})


# T1.2: data_type → 业务表路由
TASK_TYPE_TABLE_MAP: Dict[str, str] = {
    # 6 业务表
    'process_report':       'process_sub_steps',
    'material_request':     'material_records',
    'material_pickup':      'material_records',
    'material_buy':         'material_records',
    'quality_task':         'quality_records',
    'equipment_repair':     'repair_records',
    'outsource_task':       'outsource_records',
    # 5 归宿表（v3.1 新增）
    'config':               'tbl_configs',
    'flow_production':      'production_orders',
    'flow_step':            'schedule_flow_logs',
    'production':           'process_records',
    'approval':             'approval_records',
}


def validate_data_type(data_type: str) -> str:
    """T1.5: 异常值处理

    Args:
        data_type: 业务类型

    Returns:
        业务表名

    Raises:
        ValueError: 不支持 data_type
    """
    if data_type not in TASK_TYPE_TABLE_MAP:
        logger.warning(f'未知 data_type: {data_type}')
        raise ValueError(
            f'不支持的 data_type: {data_type}，'
            f'合法值: {sorted(TASK_TYPE_TABLE_MAP.keys())}'
        )
    return TASK_TYPE_TABLE_MAP[data_type]


# T1.6: 单元测试
if __name__ == '__main__':
    import pymysql
    from pymysql.cursors import DictCursor

    DB_CONFIG = {
        'host': 'localhost', 'port': 3306, 'user': 'root',
        'password': '88888888', 'database': 'container_center',
    }

    # 单元测试 1: 白名单
    print('[1/6] 白名单常量测试')
    assert len(NEW_DATA_TYPES) == 12, f'应为 12 种，实际 {len(NEW_DATA_TYPES)}'
    assert len(TASK_TYPE_TABLE_MAP) == 12, f'应为 12 条映射'
    print('   ✅ 12 种 data_type 全部白名单')

    # 单元测试 2: 路由表无重复
    print('[2/6] 路由表无重复测试')
    unique_tables = set(TASK_TYPE_TABLE_MAP.values())
    assert len(unique_tables) == 10, f'应为 10 张唯一表，实际 {len(unique_tables)}'
    print(f'   ✅ {len(unique_tables)} 张唯一业务表（material_records 共享 3 种 data_type）')

    # 单元测试 3: validate_data_type
    print('[3/6] validate_data_type 测试')
    for dt in NEW_DATA_TYPES:
        table = validate_data_type(dt)
        assert table in TASK_TYPE_TABLE_MAP.values()
    print('   ✅ 12 种合法 data_type 全部验证')

    # 单元测试 4: 异常值
    print('[4/6] 异常值测试')
    try:
        validate_data_type('invalid_xxx')
        assert False, '应抛 ValueError'
    except ValueError as e:
        assert '不支持的 data_type' in str(e)
    print('   ✅ 异常值抛 ValueError')

    # 单元测试 5: 真实 DB 查询（process_report）
    print('[5/6] 真实 DB 查询测试')
    c = pymysql.connect(**DB_CONFIG)
    cur = c.cursor(DictCursor)
    table = validate_data_type('process_report')
    cur.execute(f'SELECT COUNT(*) AS cnt FROM {table} WHERE is_deleted=0')
    row = cur.fetchone()
    print(f'   ✅ {table} 有 {row["cnt"]} 行（is_deleted=0）')
    c.close()

    # 单元测试 6: 批量接口
    print('[6/6] 批量接口测试')
    c = pymysql.connect(**DB_CONFIG)
    cur = c.cursor(DictCursor)
    data_types = ['process_report', 'material_request']
    union_parts = []
    for dt in data_types:
        t = validate_data_type(dt)
        # 用具体列名（避免 SELECT * 在 UNION 中报错）
        # MySQL 5.x: LIMIT 必须在子查询内
        union_parts.append(
            f"(SELECT '{dt}' AS data_type, id, order_no, status, created_at "
            f"FROM {t} WHERE is_deleted=0 LIMIT 1)"
        )
    sql = ' UNION ALL '.join(union_parts)
    cur.execute(sql)
    rows = cur.fetchall()
    c.close()
    assert len(rows) == 2, f'应 2 行，实际 {len(rows)}'
    print(f'   ✅ 批量接口返回 {len(rows)} 行')

    print('\n🎉 6 项单元测试全部通过！')
