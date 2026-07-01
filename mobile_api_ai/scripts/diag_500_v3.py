# -*- coding: utf-8 -*-
"""直接调视图函数抓 traceback"""
import os
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
import logging
logging.disable(logging.CRITICAL)
import inventory_api_server
app = inventory_api_server.app
app.config['PROPAGATE_EXCEPTIONS'] = True

lines = []
for path in ['/inventory/inbound', '/inventory/outbound', '/inventory/batch']:
    # 找视图函数
    view_func = None
    for rule in app.url_map.iter_rules():
        if rule.rule == path and 'GET' in rule.methods:
            view_func = app.view_functions[rule.endpoint]
            break
    if not view_func:
        lines.append(f'{path}: NO VIEW')
        continue
    with app.test_request_context(path):
        try:
            view_func()
            lines.append(f'{path}: OK')
        except Exception as e:
            lines.append(f'\n=== {path} -> {type(e).__name__}: {e} ===')
            lines.append(traceback.format_exc())

text = '\n'.join(lines)
Path(r'd:\yuan\diag_500_tb2.txt').write_text(text, encoding='utf-8')
print(text)
