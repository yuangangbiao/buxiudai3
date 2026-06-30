import os
import pymysql
c = pymysql.connect(host='127.0.0.1', user='root', password=os.environ.get('MYSQL_PASSWORD', ''), database='container_center')
cur = c.cursor()
cur.execute("SELECT id, title FROM data_packages WHERE data_type='quality_task' AND (process_code IS NULL OR process_code='')")
rows = cur.fetchall()
print(f'删除前空 quality_task: {len(rows)} 条')
for r in rows:
    print(f'  {r}')

cur.execute("DELETE FROM data_packages WHERE data_type='quality_task' AND (process_code IS NULL OR process_code='')")
n = cur.rowcount
c.commit()
print(f'删除: {n} 行')

cur.execute('SELECT COUNT(*) FROM data_packages WHERE data_type=%s', ('quality_task',))
total = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM data_packages WHERE data_type=%s AND (process_code IS NULL OR process_code=%s)', ('quality_task', ''))
empty = cur.fetchone()[0]
print(f'quality_task 剩余: {total} 行 (空: {empty})')

cur.execute('SELECT id, title, process_code FROM data_packages WHERE data_type=%s', ('quality_task',))
for r in cur.fetchall():
    print(f'  {r}')
cur.close()
c.close()
print('完成')
