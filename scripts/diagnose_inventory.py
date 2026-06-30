#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
库存管理 500 错误诊断脚本
TASK-005 配套工具

用法:
    python scripts/diagnose_inventory.py
    python scripts/diagnose_inventory.py --route /inventory/dashboard

捕获 Flask 路由的 traceback，定位真正的异常源头。
不修改 inventory_api_server.py（归档保护）。
"""
import os
import sys
import traceback
import argparse
import logging
from unittest.mock import MagicMock

# 设置工作目录
os.chdir(os.path.join(os.path.dirname(__file__), '..', 'mobile_api_ai'))
sys.path.insert(0, os.getcwd())

# 准备环境变量（用 .env 中的值，或给占位符）
os.environ.setdefault('FLASK_SECRET_KEY', 'a' * 48 + 'A1!')  # 占位满足长度
os.environ.setdefault('INVENTORY_ADMIN_PASSWORD_HASH',
                      '0' * 32 + '$' + '0' * 128)  # 占位
os.environ.setdefault('MYSQL_USER', 'root')
os.environ.setdefault('INVENTORY_DB_NAME', 'steel_belt')
os.environ.setdefault('MYSQL_PASSWORD', '')

# 启用详细日志
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')


def diagnose_route(url_path: str, method: str = 'GET'):
    """直接调用 Flask 路由，捕获所有异常"""
    print('=' * 70)
    print(f'  诊断路由: {method} {url_path}')
    print('=' * 70)

    try:
        from inventory_api_server import app
    except Exception as e:
        print(f'[FATAL] 导入 inventory_api_server 失败: {e}')
        traceback.print_exc()
        return 1

    # 模拟登录态（如果路由需要）
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['is_admin'] = True
            sess['username'] = 'admin'

        # 调用路由
        try:
            resp = client.open(url_path, method=method)
            print(f'[响应] status={resp.status_code}')
            print(f'[响应] content-type={resp.content_type}')
            if resp.status_code == 500:
                # 500 错误一定有 traceback 写到 logger
                print('[响应] ⚠️ 500 错误 - 请检查 logger 输出')
            else:
                # 输出 body 摘要
                body = resp.data[:500].decode('utf-8', errors='replace')
                print(f'[响应] body 摘要: {body}')
        except Exception as e:
            print(f'[异常] 路由调用失败: {e}')
            traceback.print_exc()
            return 1

    return 0


def diagnose_all_routes():
    """诊断所有页面路由"""
    routes = [
        '/',
        '/inventory',
        '/inventory/dashboard',
        '/inventory/stock',
        '/inventory/inbound',
        '/inventory/products',
        '/inventory/stocktake',
        '/inventory/transfer',
        '/inventory/reports',
        '/inventory/notifications',
        '/inventory/backup',
    ]
    for r in routes:
        diagnose_route(r)
        print()


def diagnose_env():
    """检查环境变量"""
    print('=' * 70)
    print('  环境变量检查')
    print('=' * 70)
    required = [
        'FLASK_SECRET_KEY',
        'INVENTORY_ADMIN_PASSWORD_HASH',
        'MYSQL_USER',
        'INVENTORY_DB_NAME',
        'MYSQL_HOST',
        'MYSQL_PORT',
    ]
    for k in required:
        v = os.environ.get(k, '')
        status = '✓' if v else '✗'
        masked = (v[:20] + '...') if len(v) > 20 else v
        print(f'  [{status}] {k} = {masked}')
    print()


def diagnose_imports():
    """检查关键 import"""
    print('=' * 70)
    print('  Import 检查')
    print('=' * 70)
    modules = [
        'inventory_web',
        'inventory_web.routes',
        'inventory_web.routes_core',
        'inventory_web.routes_data',
        'inventory_web.routes_system',
        'inventory_web.routes_api',
        'inventory_web.db_utils',
        'inventory_web.admin_auth',
        'inventory_web.feature_flags',
        'inventory_web.services.inventory_service',
    ]
    for m in modules:
        try:
            __import__(m)
            print(f'  [✓] {m}')
        except Exception as e:
            print(f'  [✗] {m}: {e}')
    print()


def main():
    parser = argparse.ArgumentParser(description='库存 500 错误诊断')
    parser.add_argument('--route', type=str, default='', help='指定单个路由')
    parser.add_argument('--env', action='store_true', help='只检查环境变量')
    parser.add_argument('--imports', action='store_true', help='只检查 import')
    args = parser.parse_args()

    if args.env:
        diagnose_env()
        return 0
    if args.imports:
        diagnose_imports()
        return 0

    # 完整诊断
    diagnose_env()
    diagnose_imports()
    if args.route:
        return diagnose_route(args.route)
    diagnose_all_routes()
    return 0


if __name__ == '__main__':
    sys.exit(main())
