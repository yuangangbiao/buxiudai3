"""调试: 模拟 material_records 插入"""
import os, sys, json, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mobile_api_ai'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from storage.mysql_storage import MySQLStorage

storage = MySQLStorage(db_config={
    'host': 'localhost',
    'user': 'root',
    'password': '88888888',
    'database': 'container_center',
})

content = {
    'order_no': 'ORD-202604210002',
    'material': '不锈钢网带',
    'spec': '50目*1.0mm',
    'quantity': 50,
    'unit': '米',
    'warehouse': '主仓库',
    'remark': '生产用料',
}

material_id = uuid.uuid4().hex[:8].upper()
material_data = {
    'id': material_id,
    'title': '测试物料插入',
    'content': content,
    'source': 'desktop_publish_test',
    'priority': 'normal',
    'status': 'pending',
    'order_no': 'ORD-202604210002',
    'related_order': 'ORD-202604210002',
    'material_name': content.get('material', content.get('material_name', '')),
    'material_spec': content.get('spec', content.get('material_spec', '')),
    'unit': content.get('unit', ''),
    'warehouse': content.get('warehouse', ''),
    'planned_qty': content.get('quantity', 0),
    'completed_qty': 0,
    'target_operator': 'wuliaotest01',
    'operator_id': 'wuliaotest01',
    'flow_type': 'material',
}

print(f'尝试插入 material_records, id={material_id}')
print(f'content 类型: {type(content)}')
print(f'content 值: {content}')

try:
    result = storage.insert('material_records', material_data)
    print(f'insert 返回: {result}')
except Exception as e:
    print(f'插入失败: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()

# 验证
import pymysql
conn = pymysql.connect(host='localhost', user='root', password='88888888',
                       database='container_center', charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()
c.execute(f"SELECT id, order_no, material_name, created_at FROM material_records WHERE id='{material_id}'")
r = c.fetchone()
print(f'验证查询: {r}')
conn.close()
