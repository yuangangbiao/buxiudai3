"""调试: 检查material_records"""
import pymysql
conn = pymysql.connect(host='localhost', user='root', password='88888888',
                       database='container_center', charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()

c.execute("SELECT id, order_no, material_name, material_spec, planned_qty, status, created_at FROM material_records WHERE id='A7C5BAB6'")
r = c.fetchone()
print(f"ID=A7C5BAB6: {r}")

c.execute('SELECT COUNT(*) as cnt FROM material_records')
print(f"Total material_records: {c.fetchone()['cnt']}")

c.execute("SELECT id, order_no, material_name, status, created_at FROM material_records ORDER BY created_at DESC LIMIT 10")
print("\n最近10条 material_records:")
for r in c.fetchall():
    print(f"  id={r['id']} order={r['order_no']} mat={r['material_name']} status={r['status']} time={r['created_at']}")
conn.close()
