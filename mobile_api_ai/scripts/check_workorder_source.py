import sqlite3, json

db_path = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'
db = sqlite3.connect(db_path)
cur = db.cursor()

# 检查 data_packages 的 related_order 分布
print('=== data_packages related_order 全部 ===')
cur.execute('SELECT DISTINCT related_order FROM data_packages')
for r in cur.fetchall():
    print(f'  {r[0]}')

print()
print('=== data_packages 总数 ===')
cur.execute('SELECT COUNT(*) FROM data_packages')
print(f'  总数: {cur.fetchone()[0]}')

# 检查 container center 的数据 API 返回
print()
print('=== 检查 _get_cached_work_orders 会返回什么 ===')
# 这个函数查询的是 data_packages 表，看看有哪些状态
cur.execute('SELECT DISTINCT status FROM data_packages')
statuses = [r[0] for r in cur.fetchall()]
print(f'  状态分布: {statuses}')

# 看 WO-SCAN 记录
cur.execute('SELECT id, related_order, related_process, status FROM data_packages WHERE related_order LIKE ?', ('WO-SCAN%',))
print(f'\n=== data_packages 中的 WO-SCAN 记录 ===')
scan_records = cur.fetchall()
for r in scan_records:
    print(f'  id={r[0]}, order={r[1]}, process={r[2]}, status={r[3]}')
if not scan_records:
    print('  无WO-SCAN记录')

# 再看其他测试数据
cur.execute("SELECT DISTINCT related_order FROM data_packages WHERE related_order LIKE '%TEST%' OR related_order LIKE '%test%'")
test_records = [r[0] for r in cur.fetchall()]
print(f'\n=== data_packages 中的 TEST 记录 ===')
for r in test_records:
    print(f'  {r}')
if not test_records:
    print('  无TEST记录')

# 检查 process_records 中 WO-202605005 是否存在
cur.execute('SELECT order_no, order_no FROM process_records')
print(f'\n=== process_records 当前数据 ===')
for r in cur.fetchall():
    print(f'  order_no={r[0]}, order_no={r[1]}')

db.close()
