import pymysql

c = pymysql.connect(host='localhost',port=3306,user='root',password='88888888',database='steel_belt',charset='utf8mb4')
cur = c.cursor()

# 1. All unique process_names in MySQL process_records
cur.execute("SELECT DISTINCT process_name FROM process_records ORDER BY process_name")
print('=== MySQL process_records 所有工序名 ===')
names = [r[0] for r in cur.fetchall()]
for n in names:
    cur.execute("SELECT COUNT(*) FROM process_records WHERE process_name=%s", (n,))
    cnt = cur.fetchone()[0]
    in_dict = '✅' if n in {
        "原材料准备","焊接眼镜网","激光切板","链板冲压孔","链板冲压成型",
        "编制左旋","编制右旋","穿曲轴","输送带组装穿杆","安装链条",
        "安装裙边","整形校直","焊接输送带","表面处理","质量检验","包装入库"
    } else '⚠️'
    print('  %s %-20s %s条' % (in_dict, n, cnt))

# 2. Check for duplicate process_names in same order
cur.execute("""
    SELECT order_id, process_name, COUNT(*) as cnt 
    FROM process_records 
    GROUP BY order_id, process_name 
    HAVING cnt > 1
    ORDER BY order_id
""")
dups = cur.fetchall()
print('\n=== 同一工单中重复工序名 ===')
for d in dups:
    print('  order_id=%s, process_name=%s, %s行' % (d[0], d[1], d[2]))

# 3. process_seq range
cur.execute("SELECT MIN(process_seq), MAX(process_seq) FROM process_records")
mn, mx = cur.fetchone()
print('\n=== process_seq 范围 ===')
print('  最小: %s, 最大: %s' % (mn, mx))

# 4. orphan records (no matching production_orders)
cur.execute("""
    SELECT pr.id, pr.process_name, pr.order_id 
    FROM process_records pr 
    LEFT JOIN production_orders po ON pr.production_id = po.id 
    WHERE po.id IS NULL
    LIMIT 10
""")
orphans = cur.fetchall()
print('\n=== 孤儿 process_records (无 production_orders) ===')
for o in orphans:
    print('  id=%s %s order_id=%s' % (o[0], o[1], o[2]))

c.close()
