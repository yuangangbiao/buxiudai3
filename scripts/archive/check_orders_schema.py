# -*- coding: utf-8 -*-
from models.database import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute('DESCRIBE orders')
cols = cursor.fetchall()
print('orders 表结构:')
for c in cols:
    print(f'  {c["Field"]} - {c["Type"]}')
cursor.close()
conn.close()