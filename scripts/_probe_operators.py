"""查真实 operators 表账号"""
import pymysql

# 试 5003 用的 container_center
for db_name in ['container_center', 'steel_belt']:
    print(f'\n=== {db_name} ===')
    try:
        conn = pymysql.connect(
            host='127.0.0.1', port=3306,
            user='root', password='88888888',
            database=db_name, charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
        )
        with conn.cursor() as cur:
            # 找用户表
            cur.execute("SHOW TABLES LIKE '%operator%'")
            op_tables = cur.fetchall()
            print(f'  operator* tables: {[list(t.values())[0] for t in op_tables]}')
            cur.execute("SHOW TABLES LIKE '%user%'")
            user_tables = cur.fetchall()
            print(f'  user* tables: {[list(t.values())[0] for t in user_tables]}')
            cur.execute("SHOW TABLES LIKE '%worker%'")
            w_tables = cur.fetchall()
            print(f'  worker* tables: {[list(t.values())[0] for t in w_tables]}')

            # 试 operators
            try:
                cur.execute("SELECT * FROM operators LIMIT 5")
                rows = cur.fetchall()
                for r in rows:
                    print(f'  operators: {r}')
            except Exception as e:
                print(f'  operators err: {e}')

            # 试 workers
            try:
                cur.execute("SELECT * FROM workers LIMIT 5")
                rows = cur.fetchall()
                for r in rows:
                    print(f'  workers: {r}')
            except Exception as e:
                print(f'  workers err: {e}')

            # 试 users
            try:
                cur.execute("SELECT * FROM users LIMIT 5")
                rows = cur.fetchall()
                for r in rows:
                    print(f'  users: {r}')
            except Exception as e:
                print(f'  users err: {e}')

        conn.close()
    except Exception as e:
        print(f'  connect err: {e}')
