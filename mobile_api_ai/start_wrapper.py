# -*- coding: utf-8 -*-
import sys
import os
import traceback

log_file = r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/server_startup.log'
with open(log_file, 'w', encoding='utf-8') as f:
    f.write(f"=== wechat_server.py starting at {__import__('datetime').datetime.now()} ===\n")
    f.write(f"sys.executable: {sys.executable}\n")
    f.write(f"cwd: {os.getcwd()}\n")
    f.flush()

try:
    import wechat_server as ws
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("wechat_server imported successfully\n")
        f.write(f"ws.app: {getattr(ws, 'app', 'NOT FOUND')}\n")
        f.flush()
except Exception as e:
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"IMPORT ERROR: {e}\n")
        f.write(traceback.format_exc())
    sys.exit(1)
