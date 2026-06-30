# -*- coding: utf-8 -*-
"""
business_flows conftest - 业务流程驱动测试专用 fixture

认证机制：
- 登录：POST /api/login {"operator_id": "YuanGangBiao"}
- 返回 JWT token，存储在 session header 中
- 后续请求用 Authorization: Bearer {token}
"""
import pytest
import os
import requests
from datetime import datetime

E2E_OPERATOR_ID = 'YuanGangBiao'
E2E_OPERATOR_NAME = '苑岗彪'
E2E_ORDER_PREFIX = 'E2E'

# JWT Secret（从 mobile_api_ai/.env 读取）
JWT_SECRET = '6ad79ab219915f0e3563dfaa7347d2233b8fbbf6fcadcc9a7bdd4efadb947f98'


def make_mobile_client(operator_id='YuanGangBiao'):
    """创建 5008 API 客户端（X-User-Id header 直连，5008 为本地服务）"""
    sess = requests.Session()
    sess.headers.update({
        'Content-Type': 'application/json',
        'X-User-Id': operator_id,
    })
    return sess


def login_mobile(operator_id='YuanGangBiao'):
    """登录 5008 mobile（直接用 X-User-Id header，5008 为本地服务不需要真实认证）"""
    sess = make_mobile_client(operator_id)
    return sess


# ============== DB Session ==============

@pytest.fixture(scope='session')
def db_session():
    import pymysql
    password = os.getenv('MYSQL_PASSWORD', '88888888')
    conn = pymysql.connect(
        host='localhost', port=3306, user='root',
        password=password, database='steel_belt',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )
    yield conn
    conn.close()


# ============== 登录 Fixture ==============

@pytest.fixture
def login_as():
    def _login(username='YuanGangBiao', role='worker'):
        return login_mobile(username)
    return _login


# ============== 服务就绪检查 ==============

@pytest.fixture(scope='session')
def wait_for_services():
    import time
    services = {
        '5008 移动端': 'http://localhost:5008/api/health',
        '8008 Sync Bridge': 'http://localhost:8008/api/health',
    }
    max_retries = 10
    for name, url in services.items():
        found = False
        for i in range(max_retries):
            try:
                r = requests.get(url, timeout=2)
                if r.status_code == 200:
                    found = True
                    print(f'[服务就绪] {name}')
                    break
            except Exception:
                pass
            time.sleep(2)
        if not found:
            pytest.skip(f'{name} 服务未启动，跳过 E2E 测试')
    yield


# ============== 业务流 Fixture ==============

def generate_e2e_order_no():
    date_str = datetime.now().strftime('%Y%m%d')
    seq = datetime.now().microsecond % 1000
    return f'{E2E_ORDER_PREFIX}-{date_str}-{seq:03d}'


@pytest.fixture
def mobile_session(login_as, wait_for_services):
    return login_as('YuanGangBiao', role='worker')


@pytest.fixture
def sync_session():
    sess = requests.Session()
    sess.headers['Content-Type'] = 'application/json'
    return sess


@pytest.fixture
def e2e_mobile_client():
    return make_mobile_client()


@pytest.fixture
def e2e_sync_client():
    sess = requests.Session()
    sess.headers['Content-Type'] = 'application/json'
    return sess


@pytest.fixture
def main_chain_session(mobile_session, db_session, wait_for_services):
    order_no = generate_e2e_order_no()
    context = {
        'order_no': order_no,
        'session': mobile_session,
        'db': db_session,
        'progress': {
            'published': False,
            'scheduled': False,
            'material_ready': False,
            'in_production': False,
            'qc_required': False,
            'warehoused': False,
            'completed': False,
            'shipped': False,
        },
    }
    yield context
    _cleanup_e2e_order(db_session, order_no)


# ============== Playwright Fixture ==============

@pytest.fixture(scope='session')
def mobile_browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip('Playwright 未安装，跳过 Playwright 测试')
    headless = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            yield browser
            browser.close()
    except Exception as e:
        pytest.skip(f'Playwright 启动失败: {e}')


@pytest.fixture
def mobile_page(mobile_browser):
    context = mobile_browser.new_context(
        viewport={'width': 375, 'height': 667},
        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
    )
    page = context.new_page()
    yield page
    context.close()


# ============== 清理工具 ==============

def _cleanup_e2e_order(db_session, order_no):
    try:
        with db_session.cursor() as cur:
            cur.execute("UPDATE orders SET is_deleted=1 WHERE order_no=%s", (order_no,))
            cur.execute("DELETE FROM process_steps WHERE order_no=%s", (order_no,))
            cur.execute("DELETE FROM material_records WHERE order_no=%s", (order_no,))
            cur.execute("DELETE FROM qc_records WHERE order_no=%s", (order_no,))
            cur.execute("DELETE FROM shipments WHERE order_no=%s", (order_no,))
        db_session.commit()
    except Exception as e:
        print(f'清理 E2E 订单失败: {order_no}, {e}')
