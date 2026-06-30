"""检查 material_records 和 data_packages 表结构"""
import pymysql

conn = pymysql.connect(host='localhost', user='root', password='88888888',
                       database='container_center', charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()

print('=== material_records ===')
c.execute('DESCRIBE material_records')
for r in c.fetchall():
    print(f"  {r['Field']:25s} {r['Type']:30s} Null={r['Null']} Key={r['Key']} Default={str(r['Default']):15s} Extra={r.get('Extra','')}")

print('\n=== data_packages ===')
c.execute('DESCRIBE data_packages')
for r in c.fetchall():
    print(f"  {r['Field']:25s} {r['Type']:30s} Null={r['Null']} Key={r['Key']} Default={str(r['Default']):15s} Extra={r.get('Extra','')}")

print('\n=== quality_records ===')
c.execute('DESCRIBE quality_records')
for r in c.fetchall():
    print(f"  {r['Field']:25s} {r['Type']:30s} Null={r['Null']} Key={r['Key']} Default={str(r['Default']):15s} Extra={r.get('Extra','')}")

conn.close()
