"""补同步 order_materials -> material_records + 修复 ETL 配置"""
import pymysql
CONN = dict(host='127.0.0.1', port=3306, user='root', password='88888888', connect_timeout=10, cursorclass=pymysql.cursors.DictCursor)

# 1. 字段映射同步
conn_s = pymysql.connect(database='steel_belt', **CONN)
conn_c = pymysql.connect(database='container_center', **CONN)
cur_s = conn_s.cursor()
cur_c = conn_c.cursor()

# 查 order_materials 数据
cur_s.execute("SELECT * FROM order_materials WHERE order_no IS NOT NULL AND order_no != '' ORDER BY id ASC")
rows = cur_s.fetchall()
print(f'order_materials 总数: {len(rows)}')

# 字段映射
sync_count = 0
for r in rows:
    rec = {
        'id': f"MAT-{r['id']}",
        'title': f"{r['material_name'] or ''} ({r['material_type'] or ''})",
        'content': '{}',  # json
        'source': r['flow_type'] or 'material_purchase',
        'status': r['status'] or 'pending',
        'material_name': r['material_name'] or '',
        'material_spec': r['spec'] or '',
        'unit': r['unit'] or '件',
        'warehouse': r['warehouse'] or '主仓库',
        'arrival_date': r['arrival_date'],
        'order_no': r['order_no'],
        'related_order': r['order_no'],
        'completed_qty': int(r.get('prepared_qty') or 0),
        'target_operator': r.get('target_operator'),
        'operator_id': r.get('target_operator'),
        'planned_qty': int(r.get('required_qty') or 0),
        'created_at': r['created_at'],
        'updated_at': r['updated_at'] or r['created_at'],
    }
    rec = {k: v for k, v in rec.items() if v is not None}
    cl = ', '.join(rec.keys())
    ph = ', '.join(['%s'] * len(rec))
    try:
        cur_c.execute(
            f"INSERT INTO material_records ({cl}) VALUES ({ph}) ON DUPLICATE KEY UPDATE material_name=VALUES(material_name), planned_qty=VALUES(planned_qty), updated_at=VALUES(updated_at)",
            tuple(rec.values())
        )
        sync_count += 1
    except Exception as e:
        print(f"  {r['order_no']} {r['material_name']}: {e}")

conn_c.commit()
print(f"补同步 material_records: {sync_count} 条")
cur_c.execute("SELECT COUNT(*) c FROM material_records")
print(f"container_center.material_records 总数: {cur_c.fetchone()['c']}")

# 2. 验证 API
import requests
r = requests.post('http://127.0.0.1:5008/api/login', json={'username':'测试','password':'123456'}, timeout=5)
tok = r.json().get('data', {}).get('token', '')
r = requests.get('http://127.0.0.1:5008/api/tasks?page_route=material', headers={'Authorization': f'Bearer {tok}'}, timeout=5)
d = r.json()
if isinstance(d, dict) and 'data' in d:
    tasks = d['data'].get('tasks', [])
    print(f"\n5008 /api/tasks?page_route=material 返回: {len(tasks)} 条")

conn_s.close()
conn_c.close()
