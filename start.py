# -*- coding: utf-8 -*-
"""统一启动入口 — 管理所有子服务"""
import sys
import subprocess
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

SERVICES = {
    "container": ["python", "mobile_api_ai/container_center_api.py"],
    "dispatch": ["python", "mobile_api_ai/dispatch_center.py"],
    "dashboard": ["python", "desktop/views/dashboard/dashboard_server.py"],
    "mobile": ["python", "mobile_api_ai/app.py"],
    "sync": ["python", "mobile_api_ai/sync_bridge_server.py"],
    "all": None,
}


def start(service: str) -> None:
    """启动指定服务或全部服务"""
    if service == "all":
        for s in SERVICES:
            if s != "all":
                subprocess.Popen(SERVICES[s], cwd=ROOT)
    else:
        subprocess.run(SERVICES[service], cwd=ROOT)


if __name__ == "__main__":
    s = sys.argv[1] if len(sys.argv) > 1 else "all"
    start(s)
