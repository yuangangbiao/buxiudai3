#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用 trae_ro 账号列出所有数据库 + 各库表数量"""
import pymysql

conn = pymysql.connect(
    host='127.0.0.1',
    port=3306,
    user='trae_ro',
    password='Trae_RO_2026!ReadOnly',
    charset='utf8mb4',
)
cur = conn.cursor()

cur.execute('SHOW DATABASES')
print('=' * 60)
print('  所有数据库列表')
print('=' * 60)
dbs = [r[0] for r in cur.fetchall()]
for i, db in enumerate(dbs, 1):
    if db in ('information_schema', 'performance_schema', 'mysql', 'sys'):
        marker = ' [系统库]'
    else:
        marker = ' [业务库]'
    print(f'  {i}. {db}{marker}')

print('\n' + '=' * 60)
print('  业务库表数量统计')
print('=' * 60)
business_dbs = [db for db in dbs if db not in ('information_schema', 'performance_schema', 'mysql', 'sys')]
for db in business_dbs:
    cur.execute(f"SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = '{db}'")
    count = cur.fetchone()[0]
    print(f'  - {db:25s}  {count:>4} 张表')

conn.close()
print('\n' + '=' * 60)
print('  ✓ 查询完成（用的是 trae_ro 只读账号，等价于 MCP）')
print('=' * 60)
