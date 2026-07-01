import sqlite3, json

db_path = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'
db = sqlite3.connect(db_path)
cur = db.cursor()

# 检查 process_records 完整数据
print('=== process_records 全部记录 ===')
cur.execute('SELECT * FROM process_records')
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    row = dict(zip(cols, r))
    print(f'  id={row["id"]}, order_no={row["order_no"]}, order_no={row["order_no"]}')
    print(f'  product_name={row["product_name"]}, status={row["status"]}, flow_type={row["flow_type"]}')
    steps = row.get('steps')
    if isinstance(steps, str):
        try:
            s = json.loads(steps)
            print(f'  steps: {len(s)}个')
        except Exception as e:
            print(f'  steps: {steps[:100]} (JSON解析失败: {e})')
    print()

# 检查 data_packages 查看是否有 WO-202605005 数据
print('=== data_packages related_order 分布 ===')
cur.execute('SELECT DISTINCT related_order FROM data_packages')
for r in cur.fetchall():
    print(f'  {r[0]}')

print()
print('=== 从data_packages查看WO-202605005的content ===')
cur.execute('SELECT content FROM data_packages WHERE related_order LIKE ? LIMIT 1', ('%WO-202605005%',))
row = cur.fetchone()
if row:
    try:
        content = json.loads(row[0])
        print(f'  content keys: {list(content.keys())}')
        print(f'  order_no: {content.get("order_no", "N/A")}')
        print(f'  order_no: {content.get("order_no", "N/A")}')
    except Exception as e:
        print(f'  content: {row[0][:200]} (JSON解析失败: {e})')
else:
    print('  未找到WO-202605005的数据')

# 检查 dispatch_commands 中的 order_no 和 order_no 对应关系
print()
print('=== dispatch_commands order_no 分布 ===')
cur.execute('SELECT DISTINCT order_no, process_name FROM dispatch_commands ORDER BY order_no, process_name')
for r in cur.fetchall():
    print(f'  order_no={r[0]}, process={r[1]}')

db.close()
