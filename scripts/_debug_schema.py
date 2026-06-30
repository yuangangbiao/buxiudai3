"""调试: 检查表结构"""
import pymysql
conn = pymysql.connect(host='localhost', user='root', password='88888888',
                       database='container_center', charset='utf8mb4')
c = conn.cursor()

print("=== material_records ===")
c.execute('DESCRIBE material_records')
for r in c.fetchall():
    print(f'  {r}')

print("\n=== data_packages ===")
c.execute('DESCRIBE data_packages')
for r in c.fetchall():
    print(f'  {r}')

print("\n=== quality_records ===")
c.execute('DESCRIBE quality_records')
for r in c.fetchall():
    print(f'  {r}')

print("\n=== process_sub_steps ===")
c.execute('DESCRIBE process_sub_steps')
for r in c.fetchall():
    print(f'  {r}')
conn.close()
