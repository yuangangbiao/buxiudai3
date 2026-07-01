#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云端服务诊断版本
专门用于排查EXE启动问题
"""
import os
import sys

print("=" * 60)
print("云端微信服务 - 诊断版本")
print("=" * 60)

# Step 1: 检查Python环境
print(f"\n[1] Python版本: {sys.version}")
print(f"    可执行文件: {sys.executable}")
print(f"    程序路径: {sys.argv[0]}")
print(f"    工作目录: {os.getcwd()}")

# Step 2: 检查目录
exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
print(f"\n[2] EXE所在目录: {exe_dir}")
print(f"    目录存在: {os.path.exists(exe_dir)}")

# Step 3: 检查.env文件
env_path = os.path.join(exe_dir, '.env')
print(f"\n[3] .env文件检查:")
print(f"    路径: {env_path}")
print(f"    存在: {os.path.exists(env_path)}")

# Step 4: 尝试加载环境变量
if os.path.exists(env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        print("    .env加载: 成功")
    except Exception as e:
        print(f"    .env加载: 失败 - {e}")
else:
    print("    .env加载: 文件不存在，跳过")

# Step 5: 加载配置
print(f"\n[4] 配置加载:")
try:
    from core.config import LOG_DIR, BASE_DIR
    print(f"    LOG_DIR: {LOG_DIR}")
    print(f"    BASE_DIR: {BASE_DIR}")
    print(f"    配置模块: 成功")
except Exception as e:
    print(f"    配置模块: 失败 - {e}")

# Step 6: 设置日志
print(f"\n[5] 日志系统:")
try:
    from logging_setup import setup_daily_logger, cleanup_old_logs
    print("    logging_setup导入: 成功")
    cleanup_old_logs()
    logger = setup_daily_logger('wechat_cloud')
    print("    日志初始化: 成功")
except Exception as e:
    print(f"    日志初始化: 失败 - {e}")
    import traceback
    traceback.print_exc()

# Step 7: 初始化数据库
print(f"\n[6] 数据库初始化:")
try:
    from cloud_backup import init_db
    result = init_db()
    print(f"    数据库初始化: {'成功' if result else '失败'}")
except Exception as e:
    print(f"    数据库初始化: 失败 - {e}")
    import traceback
    traceback.print_exc()

# Step 8: 创建Flask应用
print(f"\n[7] Flask应用创建:")
try:
    from flask import Flask
    app = Flask(__name__)
    print("    Flask应用: 成功")
except Exception as e:
    print(f"    Flask应用: 失败 - {e}")
    import traceback
    traceback.print_exc()

print("\n[8] 启动完成，按Ctrl+C退出")
print("=" * 60)

# 等待用户按键
input("\n按Enter键继续启动服务...")

# 继续正常启动
import logging
logger = logging.getLogger(__name__)
logger.info("诊断完成，开始正常启动服务...")

# 导入主程序
import wechat_cloud
