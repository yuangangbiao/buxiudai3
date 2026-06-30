"""检查 MySQL 连接和 sub_steps 表状态"""
import pymysql
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path)

cfg = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
    'charset': os.environ.get('MYSQL_CHARSET', 'utf8mb4'),
}

try:
    conn = pymysql.connect(**cfg)
    cur = conn.cursor()

    # 检查 sub_steps 表
    cur.execute("SHOW TABLES LIKE 'sub_steps'")
    if cur.fetchone():
        cur.execute("DESCRIBE sub_steps")
        cols = cur.fetchall()
        print('=== sub_steps 表结构 ===')
        has_overtime_minutes = False
        has_overtime_hours = False
        for c in cols:
            name = c[0]
            flag = ' <<<< overtime字段' if 'overtime' in name else ''
            print(f'  {name}: {c[1]}  null={c[2]}  default={c[4]}{flag}')
            if name == 'overtime_minutes':
                has_overtime_minutes = True
            elif name == 'overtime_hours':
                has_overtime_hours = True

        cur.execute('SELECT COUNT(*) FROM sub_steps')
        count = cur.fetchone()[0]
        print(f'\n=== 总记录数: {count}')

        if count > 0 and has_overtime_minutes:
            cur.execute('SELECT overtime_hours, overtime_minutes FROM sub_steps WHERE overtime_minutes > 0 LIMIT 5')
            rows = cur.fetchall()
            print('=== 有 overtime_minutes 值的记录(前5条) ===')
            for r in rows:
                print(f'  overtime_hours={r[0]}, overtime_minutes={r[1]}')
    else:
        print('[INFO] sub_steps 表不存在')

    # 检查 dispatch_operators 表（TASK-07 调度业务专用表）
    cur.execute("SHOW TABLES LIKE 'dispatch_operators'")
    if cur.fetchone():
        cur.execute("DESCRIBE dispatch_operators")
        cols = cur.fetchall()
        print('\n=== dispatch_operators 表结构 ===')
        for c in cols:
            print(f'  {c[0]}: {c[1]}  null={c[2]}  default={c[4]}')
    else:
        print('\n[INFO] dispatch_operators 表不存在（将在首次启动时自动创建）')

    conn.close()
    print('\n[OK] MySQL 连接成功！')
except Exception as e:
    print(f'[FAIL] MySQL 连接失败: {e}')
