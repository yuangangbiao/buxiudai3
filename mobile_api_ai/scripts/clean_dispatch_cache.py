import json, sqlite3

KEEP = ['ORD-202604290001', 'WO-202605005', 'ORD-202604210003', 'WO-202605006', '202605006']
KEEP_WO = ['WO-202605005', 'WO-202605006', 'WO-202605009', 'WO-202605008', 'WO-202605007']
KEEP_ORDER = ['ORD-202604210003', 'ORD-202604290001']

# 1. 清理本地缓存文件
cache_file = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center_data.json'
with open(cache_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

before = len(data.get('processes', []))
data['processes'] = [p for p in data['processes'] 
    if p.get('order_no') in KEEP or p.get('order_no') in KEEP]

after = len(data['processes'])
print(f'缓存processes: {before} -> {after}')

with open(cache_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('缓存已更新')

# 2. 清理数据库 process_records
db_path = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'
db = sqlite3.connect(db_path)
cur = db.cursor()

# 查看现有
wo_before = [r[0] for r in cur.execute('SELECT order_no FROM process_records')]
print(f'\n数据库process_records清理前: {wo_before}')

cur.execute('DELETE FROM process_records WHERE order_no NOT IN (?,?)', KEEP_WO[:2])
db.commit()

wo_after = [r[0] for r in cur.execute('SELECT order_no FROM process_records')]
print(f'数据库process_records清理后: {wo_after}')

# 3. 清理 dispatch_commands
cmd_before = [r[0] for r in cur.execute('SELECT DISTINCT order_no FROM dispatch_commands')]
print(f'\ndispatch_commands清理前order_no: {cmd_before}')

cur.execute('DELETE FROM dispatch_commands WHERE order_no NOT IN (?,?)', KEEP_ORDER)
db.commit()

cmd_after = [r[0] for r in cur.execute('SELECT DISTINCT order_no FROM dispatch_commands')]
cmd_count = [r[0] for r in cur.execute('SELECT COUNT(*) FROM dispatch_commands')]
print(f'dispatch_commands清理后order_no: {cmd_after}, 总数: {cmd_count[0]}')

# 4. 清理 schedule_records
# [F16 T16.2 修复] F6 P9 2026-06-10 已 DROP schedule_records (跨库历史表清理, 详见 MEMORY.md L20)
#     该表原 MySQL 容器中心表 + SQLite wechat_container.db 表均被清理
#     排产数据已迁移到 process_records + dispatch_cache, 跳过 schedule_records 清理
print('\n[F6 P9 兼容] schedule_records 表已 DROP, 跳过清理 (排产数据已迁移到 process_records)')

# 5. 清理 data_flow_logs
fl_before = [r[0] for r in cur.execute('SELECT DISTINCT order_no FROM data_flow_logs')]
print(f'\ndata_flow_logs清理前order_no数: {len(fl_before)}')

cur.execute("DELETE FROM data_flow_logs WHERE order_no NOT IN (?,?,?,?,?)", 
    KEEP_ORDER + KEEP_WO)
db.commit()

fl_after = [r[0] for r in cur.execute('SELECT DISTINCT order_no FROM data_flow_logs')]
print(f'data_flow_logs清理后order_no数: {len(fl_after)}')

db.close()
print('\n清理完成！请重启调度中心')
