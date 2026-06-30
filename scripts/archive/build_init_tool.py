# -*- coding: utf-8 -*-
import subprocess
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

base_dir = r"d:\yuan\不锈钢网带跟单3.0"
init_tool = os.path.join(base_dir, "数据库初始化工具v3.py")

pyinstaller = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe"

cmd = [pyinstaller, "--onefile", "--windowed", "--name=数据库初始化工具v3",
       "--distpath", os.path.join(base_dir, "dist"),
       "--workpath", os.path.join(base_dir, "build_init"),
       "--clean",
       init_tool]

logger.info(f"Running: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=base_dir, encoding="gbk")

logger.info(f"Return code: {result.returncode}")
if result.returncode == 0:
    logger.info("[OK] 打包成功！")
else:
    logger.error("[FAIL] 打包失败")
    logger.error(result.stderr[:500] if result.stderr else "")