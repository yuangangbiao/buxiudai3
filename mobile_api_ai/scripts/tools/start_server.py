# -*- coding: utf-8 -*-
"""启动 wechat_server.py 并保持前台运行"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('REDIS_HOST', 'localhost')
os.environ.setdefault('REDIS_PORT', '6379')
os.environ.setdefault('SOCKET_CONNECT_TIMEOUT', '3')

from wechat_server import app, init_services, init_wechat_services

init_services()
init_wechat_services()

from dispatch_center import start_background_scheduler
try:
    start_background_scheduler()
except Exception:
    pass

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--host', default='0.0.0.0')
parser.add_argument('--port', type=int, default=5003)
args = parser.parse_args()

print(f"[StartServer] Starting on {args.host}:{args.port}")
app.run(host=args.host, port=args.port, threaded=True)
