# -*- coding: utf-8 -*-
"""生成 MySQL 数据库完整字典 — 一键同步到腾讯文档"""
import pymysql
from datetime import datetime

c = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='88888888')
cur = c.cursor()

cur.execute("""SELECT table_schema, table_name, table_comment, table_rows
FROM information_schema.TABLES
WHERE table_schema NOT IN ('information_schema','mysql','performance_schema','sys')
ORDER BY table_schema, table_name""")
tables = [(r[0], r[1], r[2] or '', r[3]) for r in cur.fetchall()]

cur.execute("""SELECT table_schema, table_name, ordinal_position, column_name,
  column_type, is_nullable, column_key, column_default, extra, column_comment
FROM information_schema.COLUMNS
WHERE table_schema NOT IN ('information_schema','mysql','performance_schema','sys')
ORDER BY table_schema, table_name, ordinal_position""")
cols = [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7] or '', r[8], r[9] or '') for r in cur.fetchall()]
c.close()

db_desc = {
    'container_center': '容器中心 + 调度中心 + 报工程序的流程管理、企业架构、任务池',
    'inventory_db': '库存管理系统 - 产品、库存、出入库流水、仓库、供应商',
    'steel_belt': '桌面端 SteelBelt 主库 - 订单、产品、客户、生产数据 GBK',
    'steel_belt_test': '桌面端测试库 - steel_belt 的测试副本',
}

today = datetime.now().strftime('%Y%m%d')
db_names = sorted(set(t[0] for t in tables))
lines = []
lines.append('# MySQL 数据库完整字典')
lines.append('> 生成时间: %s | %d 数据库 | %d 表 | %d 列' % (datetime.now().strftime('%Y-%m-%d'), len(db_names), len(tables), len(cols)))
lines.append('')
lines.append('---')
lines.append('')
lines.append('## 概览')
lines.append('')
lines.append('| 数据库 | 表数 | 用途 |')
lines.append('|--------|------|------|')
for db in db_names:
    tcount = sum(1 for t in tables if t[0] == db)
    lines.append('| `%s` | %d | %s |' % (db, tcount, db_desc.get(db, '')))
lines.append('')
lines.append('---')

for db in db_names:
    lines.append('')
    lines.append('## %s' % db)
    lines.append('> %s' % db_desc.get(db, ''))
    lines.append('')
    for tn, tc, tr in [(t[1], t[2], t[3]) for t in tables if t[0] == db]:
        lines.append('### `%s`' % tn)
        if tc:
            lines.append('> %s | %s 行' % (tc, tr))
        lines.append('')
        lines.append('| # | 列名 | 类型 | NULL | 键 | 默认值 | 额外 | 注释 |')
        lines.append('|----|------|------|------|-----|--------|------|------|')
        for cs, ctn, pos, cn, ctyp, nu, ck, cd, ex, cc in cols:
            if cs == db and ctn == tn:
                lines.append('| %s | `%s` | %s | %s | %s | %s | %s | %s |' % (pos, cn, ctyp, nu, ck or '', cd or '', ex or '', cc or ''))
        lines.append('')

output = '\n'.join(lines)
path = r'D:\yuan\不锈钢网带跟单3.0\代码审查报告\MySQL数据库完整字典_%s.md' % today
with open(path, 'w', encoding='utf-8') as f:
    f.write(output)
print('OK: %d lines -> %s' % (output.count('\n'), path))
