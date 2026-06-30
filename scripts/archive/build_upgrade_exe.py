# -*- coding: utf-8 -*-
"""
打包订单修复升级包
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
SOURCE_FILE = os.path.join(BASE_DIR, "升级包", "upgrade_v3_order_fix.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "dist_upgrade")
BUILD_DIR = os.path.join(BASE_DIR, "build_upgrade")

if not os.path.exists(SOURCE_FILE):
    logger.error(f"源文件不存在: {SOURCE_FILE}")
    exit(1)

logger.info("=" * 60)
logger.info("  订单修复升级包 - 打包")
logger.info("=" * 60)

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)
os.makedirs(OUTPUT_DIR)

logger.info("[STEP 1/3] 清理完成")

logger.info("[STEP 2/3] 开始打包...")
logger.info(f"    源文件: {SOURCE_FILE}")

cmd = [
    r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
    "--onefile",
    "--name=订单修复升级包v3",
    f"--distpath={OUTPUT_DIR}",
    f"--workpath={BUILD_DIR}",
    "--clean",
    "--hidden-import=pymysql",
    "--hidden-import=db_config",
    "--hidden-import=tkinter",
    "--hidden-import=logging",
    "升级包/upgrade_v3_order_fix.py"
]

result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk', cwd=BASE_DIR)

if result.returncode == 0:
    logger.info("[OK] 打包成功!")
    exe_path = os.path.join(OUTPUT_DIR, "订单修复升级包v3.exe")

    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        logger.info(f"    文件: {exe_path}")
        logger.info(f"    大小: {size:.2f} MB")

        TARGET_DIR = r"F:\智能跟单系统\v3.0\升级包"
        if not os.path.exists(TARGET_DIR):
            os.makedirs(TARGET_DIR)

        target_path = os.path.join(TARGET_DIR, "订单修复升级包v3.exe")
        if os.path.exists(target_path):
            os.remove(target_path)

        shutil.copy2(exe_path, target_path)
        logger.info(f"[OK] 已复制到: {target_path}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("[SUCCESS] 打包完成!")
        logger.info("=" * 60)
    else:
        logger.error("[FAIL] 未找到EXE文件")
else:
    logger.error("[FAIL] 打包失败")
    logger.error(result.stderr)