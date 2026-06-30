import pymysql

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='88888888', charset='utf8mb4')
c = conn.cursor()

# 两个库都有的业务表
common_tables = [
    'process_records', 'order_items', 'schedule_records',
    'product_flow_map', 'enterprise_structure', 'operation_logs',
    'customer_contacts', 'customer_groups', 'data_packages',
    'attendance', 'process_sub_steps', 'sub_step_audit_log'
]

print('steel_belt vs container_center 同名表结构对比:')
print('=' * 80)

for t in common_tables:
    c.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='steel_belt' AND TABLE_NAME='" + t + "'")
    sb_cols = set(r[0] for r in c.fetchall())

    c.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='container_center' AND TABLE_NAME='" + t + "'")
    cc_cols = set(r[0] for r in c.fetchall())

    if not sb_cols and not cc_cols:
        continue

    common = sb_cols & cc_cols
    only_sb = sb_cols - cc_cols
    only_cc = cc_cols - sb_cols

    sb_has = '有' if sb_cols else '无'
    cc_has = '有' if cc_cols else '无'

    print('\n  [%s]  steel_belt=%s(%d列)  container_center=%s(%d列)' % (t, sb_has, len(sb_cols), cc_has, len(cc_cols)))
    if common:
        same_pct = len(common) / max(len(sb_cols or [1]), len(cc_cols or [1])) * 100
        match = '完全一致' if same_pct >= 100 else '重合' + str(int(same_pct)) + '%'
        print('         共用列(%d): %s' % (len(common), ', '.join(sorted(common)[:8])))
        print('         匹配度: ' + match)
    if only_sb:
        print('         仅 steel_belt: ' + ', '.join(sorted(only_sb)[:5]))
    if only_cc:
        print('         仅 container_center: ' + ', '.join(sorted(only_cc)[:5]))

# 行数对比
print('\n' + '=' * 80)
print('同名表行数对比:')
print('=' * 80)
for t in common_tables:
    c.execute("SELECT COUNT(*) FROM steel_belt." + t)
    sb_cnt = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM container_center." + t)
    cc_cnt = c.fetchone()[0]
    status = '数据相同' if sb_cnt == cc_cnt else '不同!'
    print('  %-25s  steel_belt=%-5d  container_center=%-5d  %s' % (t, sb_cnt, cc_cnt, status))

# inventory_db vs inventory_management_db
print('\n' + '=' * 80)
print('inventory_db vs inventory_management_db 同名表:')
print('=' * 80)
inv_common = ['categories', 'products', 'inventory', 'inventory_transactions', 'suppliers', 'warehouses']
for t in inv_common:
    c.execute("SELECT COUNT(*) FROM inventory_db." + t)
    a = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM inventory_management_db." + t)
    b = c.fetchone()[0]
    status = '数据相同' if a == b else '不同!'
    print('  %-25s  inventory_db=%-5d  inv_mgmt_db=%-5d  %s' % (t, a, b, status))

c.close()
conn.close()
