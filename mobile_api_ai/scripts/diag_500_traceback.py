# -*- coding: utf-8 -*-
"""直接调 inventory_api_server 的 Flask app，跑 3 个 500 路由抓 traceback"""
import os
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')

# 关闭 setup_daily_logger 的 file handler 避免干扰
import logging
logging.disable(logging.CRITICAL)

# 拦截 sys.excepthook 抓 traceback
captured = []

old_excepthook = sys.excepthook
def my_hook(et, ev, tb):
    captured.append(''.join(traceback.format_exception(et, ev, tb)))
sys.excepthook = my_hook

# 设置测试环境标志
os.environ['FLASK_ENV'] = 'test'
import inventory_api_server
app = inventory_api_server.app

# 登录
client = app.test_client()
r = client.post('/login', data={'password': 'Admin@2026'}, follow_redirects=False)
print(f'POST /login -> {r.status_code}, location={r.headers.get("Location", "(none)")}')

# 测试 3 个 500 路由
for path in ['/inventory/inbound', '/inventory/outbound', '/inventory/batch']:
    captured.clear()
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['TESTING'] = True
    try:
        with app.test_client() as c2:
            # 复用 session
            for k, v in client.cookie_jar._cookies.items() if hasattr(client.cookie_jar, '_cookies') else []:
                pass
            # 直接构造
            c2.set_cookie('session', client.cookie_jar._cookies.get('127.0.0.1', {}).get('/', {}).get('session', None).value if False else '')
            r = c2.get(path)
            print(f'\n=== {path} -> {r.status_code} ===')
            if r.status_code >= 500:
                # 重新执行抓 traceback
                with app.test_request_context(path):
                    view = app.view_functions.get(path.strip('/').replace('/', '.'))
                # 直接 call view
                with app.test_request_context(path, headers={'Cookie': 'session=' + 'x'}):
                    # 模拟 admin
                    from flask import session
                    session['logged_in'] = True
                    session['is_admin'] = True
                    view_func = None
                    for rule in app.url_map.iter_rules():
                        if rule.rule == path and 'GET' in rule.methods:
                            view_func = app.view_functions[rule.endpoint]
                            break
                    if view_func:
                        try:
                            view_func()
                        except Exception as e:
                            print('TRACEBACK:')
                            traceback.print_exc()
    except Exception as e:
        print(f'\n{path} EXC: {e}')
        traceback.print_exc()
