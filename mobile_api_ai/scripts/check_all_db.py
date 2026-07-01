# -*- coding: utf-8 -*-
import sqlite3, os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mobile_api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 检查所有可能的 SQLite 数据库
# [F6 T4 清理] container_storage.db 已彻底移除,不再检查
db_names = ['wechat_container.db', 'container_center.db', 'container_api.db']

target = 'wo2026050009'

for db_name in db_names:
    db_path = os.path.join(mobile_api_dir, db_name)
    if not os.path.exists(db_path):
        print(f'{db_name}: 文件不存在')
        continue
    
    size = os.path.getsize(db_path)
    print(f'\n=== {db_name} (大小: {size} bytes) ===')
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 列出所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r['name'] for r in cursor.fetchall()]
        print(f'  表: {tables}')
        
        # 检查所有表中是否有目标订单号
        for table in tables:
            for col in ['order_no', 'order_no']:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM \"{table}\" WHERE \"{col}\" LIKE ?", (f'%{target}%',))
                    cnt = cursor.fetchone()[0]
                    if cnt > 0:
                        print(f'  表[{table}] 列[{col}]: 找到 {cnt} 条')
                        cursor.execute(f"SELECT * FROM \"{table}\" WHERE \"{col}\" LIKE ? LIMIT 3", (f'%{target}%',))
                        for r in cursor.fetchall():
                            print(f'    {dict(r)}')
                except:
                    pass
        
        conn.close()
    except Exception as e:
        print(f'  打开失败: {e}')

print('\n=== 检查完毕 ===')
