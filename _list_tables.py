import pymysql

conn = pymysql.connect(
    host='127.0.0.1', port=3306,
    user='root', password='88888888',
    database='steel_belt', charset='utf8mb4'
)
cursor = conn.cursor()
cursor.execute('SHOW TABLES')
tables = cursor.fetchall()

print(f'数据库 steel_belt 共 {len(tables)} 张表:')
print('=' * 65)

for i, (tname,) in enumerate(tables, 1):
    try:
        cursor.execute("SELECT COUNT(*) FROM `" + tname + "`")
        cnt = cursor.fetchone()[0]
        print(f'  {i:2d}. {tname:45s} {cnt:>8,} 行')
    except Exception as e:
        print(f'  {i:2d}. {tname:45s} ERR: {e}')

cursor.close()
conn.close()
