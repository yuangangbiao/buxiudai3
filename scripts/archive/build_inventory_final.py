# -*- coding: utf-8 -*-
"""
打包库存管理系统（完整版）v3
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

main_file = os.path.join(BASE_DIR, "inventory_manager_complete.py")
if not os.path.exists(main_file):
    logger.error(f"错误：未找到 {main_file}")
    exit(1)

logger.info("=" * 70)
logger.info("  库存管理系统 - EXE打包 (完整版)")
logger.info("=" * 70)

TEMP_DIR = os.path.join(BASE_DIR, "final_inventory_exe")
BUILD_DIR = os.path.join(BASE_DIR, "final_inventory_build")

logger.info("[STEP 1/4] 清理临时目录...")
if os.path.exists(TEMP_DIR):
    shutil.rmtree(TEMP_DIR)
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)
os.makedirs(TEMP_DIR)
logger.info("    [OK] 清理完成")

logger.info("[STEP 2/4] 开始打包...")
logger.info("    注意：打包过程需要2-5分钟，请耐心等待...")

cmd = [
    r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
    "--onefile",
    "--windowed",
    "--name=库存管理系统",
    f"--distpath={TEMP_DIR}",
    f"--workpath={BUILD_DIR}",
    "--clean",
    "--hidden-import=pymysql",
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.ttk",
    "--hidden-import=tkinter.messagebox",
    "--hidden-import=tkinter.filedialog",
    "--hidden-import=tkinter.colorchooser",
    "--hidden-import=tkinter.commondialog",
    "--hidden-import=tkinter.constants",
    "--hidden-import=tkinter.scrolledtext",
    "--hidden-import=openpyxl",
    "--hidden-import=inventory_db_complete",
    "--hidden-import=inventory_print",
    "--hidden-import=inventory_backup",
    "inventory_manager_complete.py"
]

result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk', cwd=BASE_DIR)

if result.returncode == 0:
    logger.info("[OK] 打包成功！")
    exe_path = os.path.join(TEMP_DIR, "库存管理系统.exe")

    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        logger.info(f"    文件: {exe_path}")
        logger.info(f"    大小: {size:.2f} MB")

        TARGET_DIR = r"F:\智能跟单系统\v3.0\库存管理系统"
        logger.info(f"[STEP 3/4] 复制到目标位置: {TARGET_DIR}")

        if not os.path.exists(TARGET_DIR):
            os.makedirs(TARGET_DIR)

        target_path = os.path.join(TARGET_DIR, "库存管理系统.exe")
        if os.path.exists(target_path):
            os.remove(target_path)

        shutil.copy2(exe_path, target_path)
        logger.info(f"    [OK] 已复制到: {target_path}")

        config_src = os.path.join(BASE_DIR, "inventory_config.json")
        if os.path.exists(config_src):
            shutil.copy2(config_src, TARGET_DIR)
            logger.info(f"    [OK] 配置文件已复制")

        logger.info("")
        logger.info("=" * 70)
        logger.info("[SUCCESS] 打包完成！")
        logger.info("=" * 70)
    else:
        logger.error("[FAIL] 未找到EXE文件")
else:
    logger.error("[FAIL] 打包失败")
    logger.error(result.stderr)