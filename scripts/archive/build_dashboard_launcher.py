#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包可视化大屏独立启动器 - 文件夹方式
"""
import os
import shutil
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE = os.path.join(BASE_DIR, "visualization_app", "main.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "dist_dashboard_new")
BUILD_DIR = os.path.join(BASE_DIR, "build_dashboard_launcher")

if not os.path.exists(SOURCE_FILE):
    logger.error(f"源文件不存在: {SOURCE_FILE}")
    exit(1)

logger.info("=" * 60)
logger.info("  可视化大屏独立启动器 - 文件夹打包")
logger.info("=" * 60)

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)

logger.info("[STEP 1/3] 清理完成")
logger.info("[STEP 2/3] 开始打包...")

cmd = [
    r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
    "--onefile",
    "--name=大屏独立启动器",
    f"--distpath={OUTPUT_DIR}",
    f"--workpath={BUILD_DIR}",
    "--clean",
    "--add-data=views/dashboard/templates;views/dashboard/templates",
    "--add-data=views;views",
    "--add-data=visualization_app;visualization_app",
    "--add-data=constants.py;.",
    "--add-data=config.py;.",
    "--add-data=db_config.py;.",
    "--add-data=i18n.py;.",
    "--hidden-import=views.dashboard.dashboard_server",
    "--hidden-import=flask",
    "--hidden-import=flask.app",
    "--hidden-import=flask.blueprints",
    "--hidden-import=flask.globals",
    "--hidden-import=flask.helpers",
    "--hidden-import=flask.json",
    "--hidden-import=flask.templating",
    "--hidden-import=flask.wrappers",
    "--hidden-import=flask_cors",
    "--hidden-import=werkzeug",
    "--hidden-import=werkzeug.routing",
    "--hidden-import=werkzeug.wrappers",
    "--hidden-import=werkzeug.utils",
    "--hidden-import=jinja2",
    "--hidden-import=jinja2.runtime",
    "--hidden-import=jinja2.loaders",
    "--hidden-import=pymysql",
    "--hidden-import=pymysql.cursors",
    "--hidden-import=socket",
    "--hidden-import=threading",
    "--hidden-import=webbrowser",
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.ttk",
    "--hidden-import=tkinter.messagebox",
    "--hidden-import=tkinter.scrolledtext",
    "--hidden-import=tkinter.colorchooser",
    "--hidden-import=tkinter.filedialog",
    "--hidden-import=constants",
    "--hidden-import=config",
    "--hidden-import=db_config",
    "--hidden-import=views",
    "--hidden-import=views.dashboard",
    "--hidden-import=views.dashboard.dashboard_server",
    "--hidden-import=views.orders",
    "--hidden-import=pathlib",
    "--hidden-import=pathlib.Path",
    "--additional-hooks-dir=",
    "visualization_app/main.py"
]

result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk', cwd=BASE_DIR)

if result.returncode == 0:
    logger.info("[OK] 打包成功！")
    exe_dir = os.path.join(OUTPUT_DIR, "大屏独立启动器")

    if os.path.exists(exe_dir):
        # 复制到部署包
        deploy_dir = os.path.join(BASE_DIR, "dist", "部署包", "大屏启动器")
        if os.path.exists(deploy_dir):
            shutil.rmtree(deploy_dir)
        
        shutil.copytree(exe_dir, deploy_dir)
        logger.info(f"[OK] 已复制到部署包: {deploy_dir}")

        # 创建使用说明
        with open(os.path.join(deploy_dir, "使用说明.txt"), "w", encoding="utf-8") as f:
            f.write("""可视化大屏独立启动器 - 使用说明
=================================

使用步骤：
1. 双击运行 大屏独立启动器.exe
2. 点击"启动服务器"
3. 点击"打开大屏"

注意事项：
- 需要和主程序在同一网络环境中
- 确保数据库配置正确

""")

        logger.info("")
        logger.info("=" * 60)
        logger.info("[SUCCESS] 打包完成！")
        logger.info("=" * 60)
        logger.info(f"部署包位置: {deploy_dir}")
    else:
        logger.error("[FAIL] 未找到输出目录")
else:
    logger.error("[FAIL] 打包失败")
    logger.error(result.stderr)
