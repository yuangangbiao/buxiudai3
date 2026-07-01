# -*- coding: utf-8 -*-
"""最终验证 - 8 个 TASK 全部完成情况
不依赖 Flask app context（不启动 routes）"""
import sys, os
sys.path.insert(0, 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai')

# 模拟环境变量
os.environ.setdefault('INVENTORY_ADMIN_PASSWORD_HASH', '0' * 32 + '$' + '0' * 128)
os.environ.setdefault('FLASK_SECRET_KEY', 'X' * 20 + 'y' * 10 + '7' * 5 + '!' * 5)
os.environ.setdefault('MYSQL_USER', 'test')
os.environ.setdefault('MYSQL_PASSWORD', 'test')
os.environ.setdefault('INVENTORY_DB_NAME', 'test')
os.environ.setdefault('INVENTORY_MAX_STOCK', '10000')

print('=' * 60)
print('库存功能优化 - 8 TASK 完成情况验证')
print('=' * 60)

# T1: 迁移脚本
import os
mig_path = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/inventory_web/migrations/001_function_optimization.sql'
exists = os.path.exists(mig_path)
size = os.path.getsize(mig_path) if exists else 0
print(f'[T1] DB 迁移脚本: {"OK" if exists and size > 1000 else "FAIL"} ({size} bytes)')

# T2: service 层
from inventory_web.services import (
    ProductService, InventoryService, StocktakeService,
    TransferService, ReportService, NotificationService
)
services = [ProductService, InventoryService, StocktakeService,
            TransferService, ReportService, NotificationService]
for s in services:
    methods = [m for m in dir(s) if not m.startswith('_')]
    print(f'[T2] {s.__name__}: OK ({len(methods)} methods)')

# T3: CRUD 端点
with open('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/inventory_web/routes_data.py', encoding='utf-8') as f:
    rd = f.read()
crud_endpoints = sum(rd.count(f'/inventory/api/{e}/<int:') for e in ['product', 'supplier', 'category', 'base', 'warehouse'])
print(f'[T3] CRUD update+delete 端点: {crud_endpoints} 个')
print(f'[T3] 软删除: {"_soft_delete" in rd}')
print(f'[T3] 仓库 add: {"/inventory/api/warehouse/add" in rd}')

# T4: 高级查询
print(f'[T4] 高级查询: {"ProductService.list" in rd}')
print(f'[T4] 回收站 list: {"/inventory/api/recycle-bin/list" in rd}')
print(f'[T4] 回收站 restore: {"/recycle-bin/<entity>/<int:eid>/restore" in rd}')

# T5: 抽盘
with open('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/inventory_web/routes_core.py', encoding='utf-8') as f:
    rc = f.read()
print(f'[T5] 抽盘 create: {"/inventory/api/stocktake/create" in rc}')
print(f'[T5] 抽盘 submit: {"/stocktake/<int:sid>/submit" in rc}')
print(f'[T5] 抽盘 adjust: {"/stocktake/<int:sid>/adjust" in rc}')

# T6: 调拨
print(f'[T6] 调拨 create: {"/inventory/api/transfer/create" in rc}')
print(f'[T6] 调拨 complete: {"/transfer/<int:tid>/complete" in rc}')
print(f'[T6] 调拨 cancel: {"/transfer/<int:tid>/cancel" in rc}')
reaper = os.path.exists('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/scripts/transfer_reaper.py')
print(f'[T6] 死信清理脚本: {"OK" if reaper else "FAIL"}')

# T7: 报表
with open('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/inventory_web/routes_api.py', encoding='utf-8') as f:
    ra = f.read()
for ep in ['stock-trend', 'io-flow', 'top-low-stock', 'category-distribution']:
    print(f'[T7] 报表 {ep}: {ep in ra}')

# T8: 导入/通知/扫码
print(f'[T8] 导入 template: {"import/template" in ra}')
print(f'[T8] 导入 dry-run: {"import/dry-run" in ra}')
print(f'[T8] 导入 commit: {"import/commit" in ra}')
print(f'[T8] 通知 list: {"notification/list" in ra}')
print(f'[T8] 通知 unread: {"notification/unread-count" in ra}')
print(f'[T8] 扫码页面: {"scanner_page" in ra}')

# 前端模板
templates = ['stocktake.html', 'transfer.html', 'reports.html', 'notifications.html', 'scanner.html', 'recycle_bin.html']
tpl_dir = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/inventory_web/templates/inventory'
for t in templates:
    p = os.path.join(tpl_dir, t)
    print(f'[T模板] {t}: {"OK" if os.path.exists(p) else "FAIL"}')

# base.html 升级
with open(f'{tpl_dir}/base.html', encoding='utf-8') as f:
    base = f.read()
print(f'[T8] base.html 通知铃铛: {"notifBadge" in base}')
print(f'[T8] base.html 新导航: {"/inventory/stocktake" in base and "/inventory/transfer" in base}')

print('=' * 60)
print('全部 8 TASK 验证完成')
print('=' * 60)
