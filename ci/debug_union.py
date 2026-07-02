# -*- coding: utf-8 -*-
import pymysql
c = pymysql.connect(host='localhost',port=3306,user='root',password='88888888',database='container_center')
cur = c.cursor()
cur.execute("SHOW COLUMNS FROM process_sub_steps")
print('process_sub_steps:', [r[0] for r in cur.fetchall()])
cur.execute("SHOW COLUMNS FROM material_records")
print('material_records:', [r[0] for r in cur.fetchall()])
c.close()
