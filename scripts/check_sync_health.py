# -*- coding: utf-8 -*-
"""同步健康检查脚本"""
import pymysql
import os

def _env(key, default=''):
    env_path = 'd:/yuan/不锈钢网带跟单3.0/.env'
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    if k.strip() == key:
                        return v.strip()
    return default

def check_sync_health():
    print('='*60)
    print('同步健康检查')
    print('='*60)

    # 连接 steel_belt
    try:
        conn = pymysql.connect(
            host=_env('STEEL_BELT_MYSQL_HOST', '127.0.0.1'),
            port=int(_env('STEEL_BELT_MYSQL_PORT', '3306')),
            user=_env('STEEL_BELT_MYSQL_USER', 'root'),
            password=_env('STEEL_BELT_MYSQL_PASSWORD', '88888888'),
            database='steel_belt',
            charset='utf8mb4'
        )
        cur = conn.cursor()
    except Exception as e:
        print(f'连接 steel_belt 失败: {e}')
        return

    # 1. 检查 sync_outbox 表
    print()
    print('【1】sync_outbox 表状态')
    print('-'*40)
    try:
        cur.execute('SELECT COUNT(*) FROM sync_outbox')
        total = cur.fetchone()[0]
        print(f'总记录数: {total}')

        cur.execute("SELECT COUNT(*) FROM sync_outbox WHERE status='pending'")
        pending = cur.fetchone()[0]
        print(f'待处理: {pending}')

        cur.execute("SELECT COUNT(*) FROM sync_outbox WHERE status='sent'")
        sent = cur.fetchone()[0]
        print(f'已发送: {sent}')

        cur.execute("SELECT COUNT(*) FROM sync_outbox WHERE status='failed'")
        failed = cur.fetchone()[0]
        print(f'失败: {failed}')

        if pending > 0:
            print()
            print('待处理记录（前3条）:')
            cur.execute("SELECT id, operation, table_name, created_at FROM sync_outbox WHERE status='pending' ORDER BY created_at LIMIT 3")
            for row in cur.fetchall():
                print(f'  ID:{row[0]} | 操作:{row[1]} | 表:{row[2]} | 时间:{row[3]}')
    except Exception as e:
        print(f'查询 sync_outbox 失败: {e}')

    # 2. 检查关键业务表
    print()
    print('【2】steel_belt 关键表记录数')
    print('-'*40)
    tables = ['orders', 'order_materials', 'production_orders', 'process_sub_steps', 'quality_records']
    for tbl in tables:
        try:
            cur.execute(f'SELECT COUNT(*) FROM {tbl}')
            count = cur.fetchone()[0]
            print(f'{tbl}: {count} 条')
        except Exception as e:
            print(f'{tbl}: 查询失败 - {e}')

    conn.close()

    # 连接 container_center
    print()
    print('【3】container_center 关键表记录数')
    print('-'*40)
    try:
        conn2 = pymysql.connect(
            host=_env('CONTAINER_MYSQL_HOST', '127.0.0.1'),
            port=int(_env('CONTAINER_MYSQL_PORT', '3306')),
            user=_env('CONTAINER_MYSQL_USER', 'root'),
            password=_env('CONTAINER_MYSQL_PASSWORD', '88888888'),
            database='container_center',
            charset='utf8mb4'
        )
        cur2 = conn2.cursor()

        tables2 = ['orders', 'process_sub_steps', 'quality_records', 'process_records', 'workers']
        for tbl in tables2:
            try:
                cur2.execute(f'SELECT COUNT(*) FROM {tbl}')
                count = cur2.fetchone()[0]
                print(f'{tbl}: {count} 条')
            except Exception as e:
                print(f'{tbl}: 查询失败 - {e}')

        conn2.close()
    except Exception as e:
        print(f'连接 container_center 失败: {e}')

    print()
    print('='*60)
    print('检查完成')
    print('='*60)

if __name__ == '__main__':
    check_sync_health()
