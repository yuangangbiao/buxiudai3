# -*- coding: utf-8 -*-
"""对比 inventory_db 实际表字段 vs 代码 SQL 引用字段"""
import os
import re
import pymysql
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)

# 1) 实际表字段
conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST'), port=int(os.getenv('MYSQL_PORT')),
    user=os.getenv('MYSQL_USER'), password=os.getenv('MYSQL_PASSWORD'),
    database='inventory_db', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)
actual = defaultdict(set)
with conn.cursor() as cur:
    cur.execute("SHOW TABLES")
    for r in cur.fetchall():
        tbl = list(r.values())[0]
        cur.execute(f"DESCRIBE `{tbl}`")
        for c in cur.fetchall():
            actual[tbl].add(c['Field'])
conn.close()

# 2) 代码 SQL 引用的字段
code_refs = defaultdict(set)  # {table: {field, ...}}
ROOT = Path(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
sql_pattern = re.compile(r'(?:FROM|UPDATE|INTO)\s+`?(\w+)`?\s.*?(?:WHERE|SET|VALUES|\(|$)', re.IGNORECASE | re.DOTALL)
field_pattern = re.compile(r'\b([a-z_][a-z0-9_]+)\b\s*[=<>!]', re.IGNORECASE)

# 收集所有 sql 字符串字面量
for f in (ROOT / 'inventory_web').rglob('*.py'):
    text = f.read_text(encoding='utf-8', errors='replace')
    # 匹配 "FROM table" "UPDATE table" "INTO table"
    for m in re.finditer(r'(?:FROM|UPDATE|INTO|JOIN)\s+`?(\w+)`?', text, re.IGNORECASE):
        tbl = m.group(1).lower()
        if tbl in {'select', 'where', 'set', 'values', 'and', 'or', 'on', 'as', 'left', 'right', 'inner', 'outer', 'cross', 'join'}:
            continue
        if tbl in actual or tbl in {'products', 'inventory', 'inventory_transactions', 'warehouses', 'suppliers', 'categories', 'inbound_records', 'outbound_records', 'stock_records', 'stocktake', 'bom', 'product_bom', 'inventory_alerts', 'operation_logs', 'process_calc_rules', 'quality_rules', 'quality_rule_items', 'customers', 'users', 'notifications', 'messages', 'message_templates'}:
            # 找附近 200 字符内的字段引用
            ctx = text[max(0, m.start()-50):m.end()+500]
            for fm in re.finditer(r'\b([a-z_][a-z0-9_]{2,})\b', ctx, re.IGNORECASE):
                field = fm.group(1).lower()
                if field in {'from', 'update', 'into', 'join', 'where', 'set', 'values', 'and', 'or', 'on', 'as', 'select', 'is', 'null', 'true', 'false', 'not', 'in', 'like', 'between', 'exists', 'case', 'when', 'then', 'else', 'end', 'coalesce', 'ifnull', 'sum', 'count', 'avg', 'min', 'max', 'distinct', 'group', 'order', 'by', 'limit', 'offset', 'asc', 'desc', 'having', 'union', 'all', 'any', 'some'}:
                    continue
                code_refs[tbl].add(field)

# 3) 对比
lines = []
for tbl in sorted(actual.keys() | code_refs.keys()):
    actual_fields = actual.get(tbl, set())
    code_fields = code_refs.get(tbl, set())
    missing_in_db = code_fields - actual_fields - {tbl, 'id', 'created_at', 'updated_at'}
    unused_in_code = actual_fields - code_fields
    if missing_in_db:
        lines.append(f'\n[{tbl}]')
        lines.append(f'  代码引用: {sorted(code_fields)}')
        lines.append(f'  实际字段: {sorted(actual_fields)}')
        lines.append(f'  ⚠️ 代码用但表没有: {sorted(missing_in_db)}')

text = '\n'.join(lines)
Path(r'd:\yuan\field_diff.txt').write_text(text, encoding='utf-8')
print(text)
