# -*- coding: utf-8 -*-
"""
可视化大屏独立软件 - 主入口
工厂大屏显示模块，提供图形界面管理服务器
"""
import os
import sys

if getattr(sys, 'frozen', False):
    APP_DIR = sys._MEIPASS
    sys.path.insert(0, APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, APP_DIR)

if __name__ == "__main__":
    print("[MAIN] Preloading dashboard server module...")
    try:
        from desktop.views.dashboard import dashboard_server
        print("[MAIN] Dashboard server module loaded successfully")
    except Exception as e:
        print(f"[MAIN] Failed to load dashboard server: {e}")
        import traceback
        traceback.print_exc()
    from visualization_app.launcher_ui import DashboardLauncherUI
    ui = DashboardLauncherUI()
    ui.run()