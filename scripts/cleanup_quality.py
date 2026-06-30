import os
import pymysql
c = pymysql.connect(host='127.0.0.1', user='root', password=os.environ.get('MYSQL_PASSWORD', ''), database='container_center')
cur = c.cursor()
cur.execute('CREATE TABLE quality_records_bak_20260612 AS SELECT * FROM quality_records')
n = cur.rowcount
c.commit()
print(f'备份 quality_records {n} 行 -> quality_records_bak_20260612')

cur.execute("DELETE FROM quality_records WHERE id=51 AND order_no='1' AND process_name=''")
n_del = cur.rowcount
c.commit()
print(f'删除 id=51 (order_no=1): {n_del} 行')

cur.execute('SELECT COUNT(*) FROM quality_records WHERE process_name IS NULL OR process_name=%s', ('',))
rem = cur.fetchone()[0]
print(f'quality_records.process_name 仍为空: {rem} 行')
cur.close()
c.close()
print('完成')
