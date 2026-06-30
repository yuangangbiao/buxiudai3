# -*- coding: utf-8 -*-
"""
打包可视化大屏服务器独立EXE
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
SOURCE_FILE = os.path.join(BASE_DIR, "views", "dashboard", "dashboard_server.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "dist_dashboard_server")
BUILD_DIR = os.path.join(BASE_DIR, "build_dashboard_server")

if not os.path.exists(SOURCE_FILE):
    logger.error(f"源文件不存在: {SOURCE_FILE}")
    exit(1)

logger.info("=" * 60)
logger.info("  可视化大屏服务器 - 独立EXE打包")
logger.info("=" * 60)

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)
os.makedirs(OUTPUT_DIR)

logger.info("[STEP 1/3] 清理完成")

templates_src = os.path.join(BASE_DIR, "views", "dashboard", "templates")
templates_dst = os.path.join(OUTPUT_DIR, "templates")

if os.path.exists(templates_src):
    shutil.copytree(templates_src, templates_dst)
    logger.info(f"[STEP 2/3] 已复制 templates 目录")

logger.info("[STEP 3/3] 开始打包...")

cmd = [
    r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
    "--onefile",
    "--console",
    "--name=大屏数据服务器",
    f"--distpath={OUTPUT_DIR}",
    f"--workpath={BUILD_DIR}",
    "--clean",
    "--hidden-import=flask",
    "--hidden-import=flask.app",
    "--hidden-import=flask.blueprints",
    "--hidden-import=flask.globals",
    "--hidden-import=flask.helpers",
    "--hidden-import=flask.json",
    "--hidden-import=flask.templating",
    "--hidden-import=flask.wrappers",
    "--hidden-import=werkzeug",
    "--hidden-import=werkzeug.routing",
    "--hidden-import=werkzeug.wrappers",
    "--hidden-import=werkzeug.utils",
    "--hidden-import=jinja2",
    "--hidden-import=jinja2.runtime",
    "--hidden-import=jinja2.loaders",
    "--hidden-import=pymysql",
    "--hidden-import=socket",
    "--additional-hooks-dir=",
    "views/dashboard/dashboard_server.py"
]

result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk', cwd=BASE_DIR)

if result.returncode == 0:
    logger.info("[OK] 打包成功！")
    exe_path = os.path.join(OUTPUT_DIR, "大屏数据服务器.exe")

    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        logger.info(f"    文件: {exe_path}")
        logger.info(f"    大小: {size:.2f} MB")

        TARGET_DIR = r"F:\智能跟单系统\v3.0\大屏服务器"
        if not os.path.exists(TARGET_DIR):
            os.makedirs(TARGET_DIR)

        target_path = os.path.join(TARGET_DIR, "大屏数据服务器.exe")
        if os.path.exists(target_path):
            os.remove(target_path)

        shutil.copy2(exe_path, target_path)
        logger.info(f"[OK] 已复制到: {target_path}")

        shutil.copytree(templates_dst, os.path.join(TARGET_DIR, "templates"), dirs_exist_ok=True)
        logger.info(f"[OK] 已复制 templates")

        logger.info("")
        logger.info("=" * 60)
        logger.info("[SUCCESS] 打包完成！")
        logger.info("=" * 60)
    else:
        logger.error("[FAIL] 未找到EXE文件")
else:
    logger.error("[FAIL] 打包失败")
    logger.error(result.stderr)