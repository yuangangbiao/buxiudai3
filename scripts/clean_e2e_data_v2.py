"""
清理 E2E 测试残留数据（通用版）
从 process_sub_steps、material_records 中删除测试数据
"""
import pymysql

conn = pymysql.connect(host='localhost', user='root', password='88888888',
                       database='container_center', charset='utf8mb4')
c = conn.cursor()

# 1. 清理 process_sub_steps
c.execute("DELETE FROM process_sub_steps WHERE order_no='ORD-202604210002' AND operator LIKE 'shengchan%'")
print(f'process_sub_steps 已删除 {c.rowcount} 条')

# 2. 清理 material_records
c.execute("DELETE FROM material_records WHERE order_no='ORD-202604210002' AND material_name='不锈钢网带'")
print(f'material_records 已删除 {c.rowcount} 条')

# 同样清理 steel_belt 库
conn2 = pymysql.connect(host='localhost', user='root', password='88888888',
                        database='steel_belt', charset='utf8mb4')
c2 = conn2.cursor()
c2.execute("DELETE FROM process_sub_steps WHERE order_no='ORD-202604210002' AND operator LIKE 'shengchan%'")
print(f'steel_belt.process_sub_steps 已删除 {c2.rowcount} 条')

conn.commit()
conn2.commit()
conn.close()
conn2.close()
print('清理完成')
