# -*- coding: utf-8 -*-
"""
清理测试数据：删除测试创建的自定义工序

测试创建的记录：
- id=491: P03-B 表面处理-精加工 (软删除)
- id=492: P03-C 表面处理-打磨
"""
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root', password='88888888',
    database='steel_belt', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
)
cursor = conn.cursor()

print("=" * 50)
print("清理测试数据")
print("=" * 50)

# 删除测试数据
test_ids = [491, 492]
for tid in test_ids:
    cursor.execute("DELETE FROM process_records WHERE id=%s", (tid,))
    print(f"删除 id={tid}, 影响行数: {cursor.rowcount}")

conn.commit()
cursor.close()
conn.close()

print()
print("✅ 清理完成！")
