import pymysql
c = pymysql.connect(host='localhost',port=3306,user='root',password='88888888',database='container_center')
cur = c.cursor()
cur.execute('SHOW TRIGGERS')
print('=== 触发器列表 ===')
for r in cur.fetchall():
    print('  ', r)
cur.execute('SELECT COUNT(*) FROM data_packages_deprecated')
print('\n=== data_packages_deprecated 行数 ===', cur.fetchone()[0])
cur.execute("SHOW TABLES LIKE 'data_packages%'")
print('\n=== 匹配 data_packages% 的表 ===')
for r in cur.fetchall():
    print('  ', r)
cur.execute("SHOW TABLES LIKE 'process_packages'")
print('\n=== process_packages ===', cur.fetchall())
cur.execute("SHOW TABLES LIKE 'quality_packages'")
print('\n=== quality_packages ===', cur.fetchall())
c.close()
