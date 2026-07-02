# -*- coding: utf-8 -*-
import pymysql
from pymysql.cursors import DictCursor
c = pymysql.connect(host='localhost',port=3306,user='root',password='88888888',database='container_center')
cur = c.cursor(DictCursor)
sql = "SELECT 'process_report' AS data_type, id, order_no, status, created_at FROM process_sub_steps WHERE is_deleted=0 LIMIT 1"
print('SQL 1:', sql)
cur.execute(sql)
print('rows:', cur.fetchall())
c.close()
