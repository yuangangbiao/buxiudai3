import sqlite3, json

db = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

# 1) data_packages 中所有工单
print('=== data_packages 工单汇总 ===')
rows = conn.execute("""
    SELECT related_order, 
           COUNT(*) as pkg_cnt,
           GROUP_CONCAT(DISTINCT related_process) as processes,
           MIN(created_at) as first_seen,
           MAX(created_at) as last_seen
    FROM data_packages
    WHERE related_order IS NOT NULL AND related_order != ''
    GROUP BY related_order
    ORDER BY last_seen DESC
""").fetchall()
for r in rows:
    d = dict(r)
    print(f'  {d["related_order"]}')
    print(f'    数据包数: {d["pkg_cnt"]} | 工序: {d["processes"]}')
    print(f'    首次: {d["first_seen"]} | 最近: {d["last_seen"]}')

# 2) dispatch_commands 中所有工单
print('\n=== dispatch_commands 工单汇总 ===')
rows = conn.execute("""
    SELECT order_no, 
           COUNT(*) as cmd_cnt,
           GROUP_CONCAT(DISTINCT process_name) as processes,
           MIN(created_at) as first_seen,
           MAX(created_at) as last_seen
    FROM dispatch_commands
    WHERE order_no IS NOT NULL AND order_no != ''
    GROUP BY order_no
    ORDER BY last_seen DESC
""").fetchall()
for r in rows:
    d = dict(r)
    print(f'  {d["order_no"]}')
    print(f'    指令数: {d["cmd_cnt"]} | 工序: {d["processes"]}')
    print(f'    首次: {d["first_seen"]} | 最近: {d["last_seen"]}')

# 3) process_records 中所有工单
print('\n=== process_records 工单汇总 ===')
rows = conn.execute("""
    SELECT order_no, 
           COUNT(*) as rec_cnt,
           GROUP_CONCAT(DISTINCT process_name) as processes,
           MIN(record_date) as first_seen,
           MAX(record_date) as last_seen
    FROM process_records
    WHERE order_no IS NOT NULL AND order_no != ''
    GROUP BY order_no
    ORDER BY last_seen DESC
""").fetchall()
for r in rows:
    d = dict(r)
    print(f'  {d["order_no"]}')
    print(f'    记录数: {d["rec_cnt"]} | 工序: {d["processes"]}')
    print(f'    首次: {d["first_seen"]} | 最近: {d["last_seen"]}')

conn.close()
