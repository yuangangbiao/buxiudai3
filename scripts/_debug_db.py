"""调试：检查数据库记录"""
import pymysql
conn = pymysql.connect(host='localhost', user='root', password='88888888',
                       database='container_center', charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()

print("=== data_packages 最近10条 ===")
c.execute('SELECT id, data_type, title, source, related_order, operator, status, created_at FROM data_packages ORDER BY created_at DESC LIMIT 10')
for r in c.fetchall():
    print(f'  id={r["id"]} type={r["data_type"]} source={r["source"]} order={r["related_order"]} operator={r["operator"]} status={r["status"]} created_at={r["created_at"]}')

print("\n=== material_records 最近5条 ===")
c.execute('SELECT id, order_no, material_name, status, created_at FROM material_records ORDER BY created_at DESC LIMIT 5')
for r in c.fetchall():
    print(f'  id={r["id"]} order={r["order_no"]} mat={r["material_name"]} status={r["status"]} created_at={r["created_at"]}')
conn.close()
