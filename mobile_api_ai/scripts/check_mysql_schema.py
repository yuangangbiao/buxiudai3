import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('MYSQL_HOST', 'localhost')
os.environ.setdefault('MYSQL_PORT', '3306')
os.environ.setdefault('MYSQL_USER', 'root')
os.environ.setdefault('MYSQL_PASSWORD', '')
os.environ.setdefault('MYSQL_DATABASE', 'steel_belt')

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    print('pymysql not installed')
    sys.exit(0)

cfg = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
}

try:
    conn = pymysql.connect(**cfg, cursorclass=DictCursor, connect_timeout=3)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) AS cnt FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME='production_process_records'", (cfg['database'],))
    r = c.fetchone()
    print(f'production_process_records 是否存在: {r["cnt"] > 0}')

    if r['cnt'] > 0:
        c.execute('DESCRIBE production_process_records')
        for col in c.fetchall():
            print(f'  {col["Field"]:20s} {col["Type"]:30s} Null={col["Null"]:5s} Key={col["Key"]:5s} Extra={col.get("Extra","")}')
    else:
        c.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s', (cfg['database'],))
        tables = [t['TABLE_NAME'] for t in c.fetchall()]
        related = [t for t in tables if 'process' in t.lower() or 'record' in t.lower()]
        print(f'相关表(process/record): {related}')
        print(f'全部表: {tables}')

    conn.close()
except Exception as e:
    print(f'连接失败: {e}')

input('\n按回车键退出...')
