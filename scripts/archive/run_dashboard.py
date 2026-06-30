# -*- coding: utf-8 -*-
"""启动大屏服务器"""
import os
import sys
from pathlib import Path

project_dir = Path(__file__).parent
env_file = project_dir / ".env"

if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

sys.path.insert(0, str(project_dir))
from desktop.views.dashboard.dashboard_server import app

if __name__ == "__main__":
    print("=" * 50)
    print("大屏服务器启动中...")
    print("访问地址: http://localhost:5000")
    print("局域网访问: http://192.168.0.129:5000")
    print("=" * 50)
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host="0.0.0.0", port=5000, debug=debug_mode, use_reloader=False, threaded=True)
