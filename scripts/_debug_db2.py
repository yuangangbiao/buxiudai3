"""调试: 检查所有最近记录"""
import pymysql
conn = pymysql.connect(host='localhost', user='root', password='88888888',
                       database='container_center', charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()

print("=== 全部 data_packages ===")
c.execute('SELECT id, data_type, title, source, related_order, status, created_at FROM data_packages ORDER BY created_at DESC LIMIT 20')
for r in c.fetchall():
    print(f'  id={r["id"]} type={r["data_type"]} src={r["source"]} order={r["related_order"][:20] if r["related_order"] else ""} status={r["status"]} time={r["created_at"]}')

print("\n=== 全部 material_records ===")
c.execute('SELECT id, order_no, material_name, planned_qty, status, created_at FROM material_records ORDER BY created_at DESC LIMIT 10')
for r in c.fetchall():
    print(f'  id={r["id"]} order={r["order_no"]} mat={r["material_name"]} qty={r["planned_qty"]} status={r["status"]} time={r["created_at"]}')

print("\n=== process_sub_steps 最近 ===")
c.execute('SELECT id, order_no, step_name, operator, status, created_at FROM process_sub_steps ORDER BY created_at DESC LIMIT 5')
for r in c.fetchall():
    print(f'  id={r["id"]} order={r["order_no"]} step={r["step_name"]} op={r["operator"]} status={r["status"]} time={r["created_at"]}')

print("\n=== quality_records 最近 ===")
c.execute('SELECT id, order_no, inspection_type, inspector, status, record_date FROM quality_records ORDER BY id DESC LIMIT 5')
for r in c.fetchall():
    print(f'  id={r["id"]} order={r["order_no"]} type={r["inspection_type"]} inspector={r["inspector"]} status={r["status"]} time={r["record_date"]}')

conn.close()
