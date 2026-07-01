#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
云端部署更新脚本
将更新后的文件部署到云服务器124.223.57.82

使用方法:
  1. 先上传云端部署包/ 目录到云服务器
  2. 在云服务器上执行:
     bash cloud_deploy.sh
  3. 验证: curl http://localhost:5005/health

如果云服务器是Windows系统:
  1. 将云端部署包/ 目录复制到云服务器
  2. 双击 start.bat 启动服务
"""
import os
import sys
import shutil
import subprocess
from datetime import datetime

DEPLOY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '云端部署包')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deploy_output')

FILES_TO_DEPLOY = [
    'wechat_cloud.py',
    'wechat_app_bot.py',
    'cloud_backup.py',
    'config.py',
    'logging_setup.py',
    'requirements.txt',
    'start.bat',
    'cloud_deploy.sh',
    'cloud_deploy_mini.sh',
]


def prepare_deployment():
    print('=' * 60)
    print('  准备云端部署包')
    print('=' * 60)

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for fname in FILES_TO_DEPLOY:
        src = os.path.join(DEPLOY_DIR, fname)
        dst = os.path.join(OUTPUT_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f'  [OK] {fname}')
        else:
            print(f'  [SKIP] {fname} 不存在 (跳过)')

    print()
    print(f'部署包已生成: {OUTPUT_DIR}')
    print(f'文件列表:')
    for f in os.listdir(OUTPUT_DIR):
        fpath = os.path.join(OUTPUT_DIR, f)
        size = os.path.getsize(fpath)
        print(f'  {f} ({size} 字节)')


def create_deploy_script():
    """生成部署说明"""
    script = f'''#!/bin/bash
# 云端更新脚本 - {datetime.now().strftime('%Y-%m-%d %H:%M')}
# 在云服务器上执行此脚本

echo "开始更新云端服务..."

# 1. 停止旧服务
echo "[1/3] 停止旧服务..."
pkill -f "wechat_cloud.py" 2>/dev/null || true
sleep 2

# 2. 复制新文件
echo "[2/3] 复制新文件..."
DEPLOY_DIR=$(dirname "$0")
cp "$DEPLOY_DIR/wechat_app_bot.py" /path/to/project/
cp "$DEPLOY_DIR/wechat_cloud.py" /path/to/project/

# 3. 启动新服务
echo "[3/3] 启动新服务..."
cd /path/to/project
nohup python wechat_cloud.py > logs/cloud.log 2>&1 &
sleep 3

# 验证
if pgrep -f "wechat_cloud.py" > /dev/null; then
    echo "  ✅ 服务已重启成功!"
    echo "  检查日志: tail -f logs/cloud.log"
else
    echo "  ❌ 启动失败"
    cat logs/cloud.log
fi
'''
    update_script = os.path.join(OUTPUT_DIR, 'update_cloud.sh')
    with open(update_script, 'w', encoding='utf-8') as f:
        f.write(script)
    print(f'\n更新脚本已生成: {update_script}')


if __name__ == '__main__':
    prepare_deployment()
    create_deploy_script()

    print()
    print('=' * 60)
    print('  部署说明')
    print('=' * 60)
    print('''
需要您手动将 deploy_output/ 目录上传到云服务器。

方法1 - 通过云服务器提供商的控制台:
  1. 登录阿里云/腾讯云/华为云控制台
  2. 找到云服务器 ECS/CVM
  3. 使用 WebShell 或 VNC 连接
  4. 上传 deploy_output/ 到服务器

方法2 - 通过文件传输工具:
  WinSCP / FileZilla / Xftp
  主机: 124.223.57.82
  端口: (非22, 请使用云控制台提供的连接方式)

上传后执行:
  cd deploy_output
  bash update_cloud.sh    (Linux)
  或
  start.bat              (Windows)
''')
