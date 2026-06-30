# -*- coding: utf-8 -*-
"""测试 server.py 是否能正常导入"""
import sys, os
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')
os.chdir(r'd:\yuan\不锈钢网带跟单3.0')
try:
    import desktop_web.server as srv
    print("OK server.py import")
    print(f"routes: {len(srv.app.url_map._rules)}")
except Exception as e:
    print(f"FAIL: {e}")
    import traceback; traceback.print_exc()
