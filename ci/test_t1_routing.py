# -*- coding: utf-8 -*-
"""T1 单元测试：11 路由白名单"""
import sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')

from storage.data_type_router import (
    NEW_DATA_TYPES, TASK_TYPE_TABLE_MAP, validate_data_type
)
import pymysql
from pymysql.cursors import DictCursor

DB = dict(host='localhost', port=3306, user='root',
          password='88888888', database='container_center')

print('[1/5] 白名单常量')
assert len(NEW_DATA_TYPES) == 12
assert len(TASK_TYPE_TABLE_MAP) == 12
print('   PASS: 12 种 data_type')

print('[2/5] 唯一表')
assert len(set(TASK_TYPE_TABLE_MAP.values())) == 10
print('   PASS: 10 张唯一表')

print('[3/5] validate_data_type')
for dt in NEW_DATA_TYPES:
    assert validate_data_type(dt) in TASK_TYPE_TABLE_MAP.values()
print('   PASS: 12 种合法 data_type')

print('[4/5] 异常值')
try:
    validate_data_type('invalid_xxx')
    assert False
except ValueError:
    pass
print('   PASS: 异常值抛 ValueError')

print('[5/5] 批量接口真实 DB 查询')
c = pymysql.connect(**DB)
cur = c.cursor(DictCursor)
sql = (
    "(SELECT 'process_report' AS data_type, id, order_no, status, created_at "
    "FROM process_sub_steps WHERE is_deleted=0 LIMIT 1) "
    "UNION ALL "
    "(SELECT 'material_request' AS data_type, id, order_no, status, created_at "
    "FROM material_records WHERE is_deleted=0 LIMIT 1)"
)
cur.execute(sql)
rows = cur.fetchall()
c.close()
assert len(rows) == 2
print(f'   PASS: 批量返回 {len(rows)} 行')

print('\n5/5 全部通过')
