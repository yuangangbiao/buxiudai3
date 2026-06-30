# Execute backfill script
$script = @"
import sys
sys.path.insert(0, r'D:\\yuan\\不锈钢网带跟单3.0')
from core.db import get_direct_connection
import os
conn = get_direct_connection(host='127.0.0.1', port=3306, user='root', password=os.environ.get('MYSQL_PASSWORD', ''), database='container_center', charset='utf8mb4')
cur = conn.cursor()
try:
    cur.execute('ALTER TABLE process_records ADD COLUMN flow_type VARCHAR(100) DEFAULT \\'production\\'')
    conn.commit()
    print('[OK] flow_type 列已添加')
except Exception as e:
    if 'Duplicate column' in str(e) or 'already exists' in str(e).lower():
        print('[SKIP] flow_type 列已存在')
    else:
        print(f'[ERROR] 添加列失败: {e}')
try:
    cur.execute('''UPDATE process_records SET flow_type = COALESCE(JSON_UNQUOTE(JSON_EXTRACT(content, '\$.flow_type')), 'production') WHERE flow_type IS NULL OR flow_type = ' ' ''')
    conn.commit()
    print(f'[OK] 回填 {cur.rowcount} 条记录')
except Exception as e:
    print(f'[ERROR] 回填失败: {e}')
cur.execute('SELECT COUNT(*) AS total, SUM(CASE WHEN flow_type IS NOT NULL AND flow_type != \\'\\' THEN 1 ELSE 0 END) AS filled FROM process_records')
row = cur.fetchone()
print(f'[统计] 总记录: {row[0]}, 已填充: {row[1]}')
cur.close()
conn.close()
print('[完成]')
"@
$tempFile = "$env:TEMP\backfill_$(Get-Random).py"
Set-Content -Path $tempFile -Value $script -Encoding UTF8
python $tempFile
Remove-Item $tempFile -Force
