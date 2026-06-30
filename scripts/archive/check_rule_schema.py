# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("DESCRIBE process_calc_rules")
cols = cursor.fetchall()
print("process_calc_rules 表结构:")
for c in cols:
    print(f"  {c['Field']} - {c['Type']} - {c['Null']} - {c['Key']}")

cursor.close()
conn.close()