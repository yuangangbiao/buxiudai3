# -*- coding: utf-8 -*-
"""同步功能测试脚本"""
import requests
import time

BASE_URL = 'http://localhost:5008'
URL_5003 = 'http://localhost:5003'
URL_5002 = 'http://localhost:5002'

def test_health():
    print('='*60)
    print('1. 服务健康检查')
    print('='*60)
    for name, url in [('5008报工系统', BASE_URL), ('5003调度中心', URL_5003), ('5002容器中心', URL_5002)]:
        try:
            r = requests.get(f'{url}/api/health', timeout=3)
            print(f'{name}: ✅ {r.status_code}')
        except Exception as e:
            print(f'{name}: ❌ {e}')

def test_login():
    print()
    print('='*60)
    print('2. 白名单登录测试')
    print('='*60)
    r = requests.post(f'{BASE_URL}/api/login', json={'username': '苑岗彪'}, timeout=5)
    print(f'状态码: {r.status_code}')
    print(f'响应: {r.text[:200]}')
    if r.status_code == 200:
        data = r.json()
        if data.get('success'):
            print('✅ 登录成功')
            return data.get('data', {}).get('username', '')
        else:
            print(f'❌ 登录失败: {data.get("message")}')
    return None

def test_report(username):
    print()
    print('='*60)
    print('3. 报工接口测试')
    print('='*60)
    # 获取一个待报工的订单
    r = requests.get(f'{BASE_URL}/api/process/list?status=pending', timeout=5)
    print(f'获取待报工任务: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        items = data.get('data', {}).get('items', [])
        print(f'待报工任务数: {len(items)}')
        if items:
            task = items[0]
            print(f'测试任务: {task.get("order_no")} - {task.get("step_name")}')
            return True
    return False

def test_sync_queue():
    print()
    print('='*60)
    print('4. 同步队列检查')
    print('='*60)
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

    conn = pymysql.connect(
        host=_env('STEEL_BELT_MYSQL_HOST', '127.0.0.1'),
        port=int(_env('STEEL_BELT_MYSQL_PORT', '3306')),
        user=_env('STEEL_BELT_MYSQL_USER', 'root'),
        password=_env('STEEL_BELT_MYSQL_PASSWORD', '88888888'),
        database='steel_belt',
        charset='utf8mb4'
    )
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM sync_outbox')
    count = cur.fetchone()[0]
    print(f'sync_outbox 记录数: {count}')
    if count == 0:
        print('✅ 同步队列为空，无积压')
    else:
        print('⚠️ 有待处理的同步任务')
        cur.execute('SELECT id, operation, table_name, status, created_at FROM sync_outbox WHERE status="pending" LIMIT 5')
        for row in cur.fetchall():
            print(f'  ID:{row[0]} | 操作:{row[1]} | 表:{row[2]} | 状态:{row[3]} | 时间:{row[4]}')
    conn.close()

def test_5003_5002():
    print()
    print('='*60)
    print('5. 5003-5002 通信测试')
    print('='*60)
    # 5003 调用 5002 的 operators 接口
    r = requests.get(f'{URL_5003}/api/operators', timeout=5)
    print(f'5003 → 5002 /api/operators: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print(f'操作员数量: {len(data.get("data", []))}')
        print('✅ 5003-5002 通信正常')
    else:
        print(f'⚠️ 5003-5002 通信问题: {r.text[:200]}')
        # 尝试直接测试 5002 的 operators
        r2 = requests.get(f'{URL_5002}/api/operators', timeout=5)
        print(f'直接测试 5002 /api/operators: {r2.status_code}')
        if r2.status_code == 200:
            print('✅ 5002 API 正常，可能是 5003 配置问题')

if __name__ == '__main__':
    test_health()
    username = test_login()
    test_report(username)
    test_sync_queue()
    test_5003_5002()
    print()
    print('='*60)
    print('测试完成')
    print('='*60)
