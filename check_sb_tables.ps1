$pythonCode = @'
import pymysql

conn = pymysql.connect(
    host='127.0.0.1', port=3306, user='root', password='88888888',
    database='steel_belt', charset='utf8mb4'
)
cur = conn.cursor()

print('=== steel_belt 核心表 ===')
cur.execute("SHOW TABLES")
tables = [row[0] for row in cur.fetchall()]
for t in tables:
    print('  ' + t)

print('')
print('=== 核心表行数 ===')
core_tables = ['orders', 'production_orders', 'products', 'customers', 'operators']
for t in core_tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f'  {t}: {cnt} 行')
    except Exception as e:
        print(f'  {t}: 错误 - {e}')

cur.close()
conn.close()
'@

$tempFile = "$env:TEMP\check_sb_tables.py"
Set-Content -Path $tempFile -Value $pythonCode -Encoding UTF8

& "C:\Users\lenovo\AppData\Local\Python\bin\python.exe" $tempFile

Remove-Item $tempFile -Force
