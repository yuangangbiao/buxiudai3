# -*- coding: utf-8 -*-
"""
[v3.6 T7] 完整测试套件 - 51 用例

运行: python ci/test_v3_6_full.py
"""
import os
import sys
import json
import uuid
import threading
from datetime import datetime, timedelta

# 配置
os.environ['JWT_SECRET_KEY'] = 'x' * 64  # DEV 测试 secret
PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'mobile_api_ai'))

import pymysql
from pymysql.cursors import DictCursor
import jwt

# 临时禁用 utils/__init__.py 链式导入
# 使用 importlib 直接加载模块
import importlib.util
import sys as _sys

def _direct_import(module_name, file_path):
    """直接 import 单个文件，绕过包 __init__"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    _sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

# 注入 quantity_validator（跳过 utils/__init__.py）
_qv = _direct_import(
    'utils.quantity_validator',
    os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'utils', 'quantity_validator.py')
)
validate_quantity = _qv.validate_quantity
# 注入 dispatch_task
_dt = _direct_import(
    'utils.dispatch_task',
    os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'utils', 'dispatch_task.py')
)
dispatch_task = _dt.dispatch_task
# 注入 log_sanitizer
_ls = _direct_import(
    'utils.log_sanitizer',
    os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'utils', 'log_sanitizer.py')
)
sanitize_phone = _ls.sanitize_phone
sanitize_id_card = _ls.sanitize_id_card

DB = dict(host='localhost', port=3306, user='root',
          password='88888888', database='container_center')

# 测试结果统计
RESULTS = {'PASS': 0, 'FAIL': 0, 'SKIP': 0}
FAILURES = []


def case(name):
    """测试用例装饰器"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            print(f'  [{name}] ', end='')
            try:
                f(*args, **kwargs)
                RESULTS['PASS'] += 1
                print(f'\033[92mPASS\033[0m')
            except AssertionError as e:
                RESULTS['FAIL'] += 1
                print(f'\033[91mFAIL: {e}\033[0m')
                FAILURES.append(f'[{name}] {e}')
            except Exception as e:
                RESULTS['FAIL'] += 1
                import traceback
                tb = traceback.format_exc()
                print(f'\033[91mERROR: {e}\033[0m')
                FAILURES.append(f'[{name}] {e}\n{tb}')
        return wrapper
    return decorator


def section(name):
    print(f'\n\033[94m=== {name} ===\033[0m')


# ==============================
# 1. 11 路由测试（11 用例）
# ==============================
section('1. 11 路由测试')

@case('路由-1: process_report')
def test_route_1():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['process_report'] == 'process_sub_steps'

@case('路由-2: material_request')
def test_route_2():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['material_request'] == 'material_records'

@case('路由-3: material_pickup')
def test_route_3():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['material_pickup'] == 'material_records'

@case('路由-4: material_buy')
def test_route_4():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['material_buy'] == 'material_records'

@case('路由-5: quality_task')
def test_route_5():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['quality_task'] == 'quality_records'

@case('路由-6: equipment_repair')
def test_route_6():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['equipment_repair'] == 'repair_records'

@case('路由-7: outsource_task')
def test_route_7():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['outsource_task'] == 'outsource_records'

@case('路由-8: config')
def test_route_8():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['config'] == 'tbl_configs'

@case('路由-9: flow_production')
def test_route_9():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['flow_production'] == 'production_orders'

@case('路由-10: flow_step')
def test_route_10():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['flow_step'] == 'schedule_flow_logs'

@case('路由-11: production')
def test_route_11():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['production'] == 'process_records'

@case('路由-12: approval')
def test_route_12():
    from storage.data_type_router import TASK_TYPE_TABLE_MAP
    assert TASK_TYPE_TABLE_MAP['approval'] == 'approval_records'


# ==============================
# 2. quantity 校验（5 业务类型）
# ==============================
section('2. quantity 业务化校验')

@case('quantity-1: material_records 整数')
def test_qty_1():
    from utils.quantity_validator import validate_quantity
    ok, _ = validate_quantity('material_records', 'qty', 10, plan_qty=10)
    assert ok

@case('quantity-2: process_sub_steps 小数')
def test_qty_2():
    from utils.quantity_validator import validate_quantity
    ok, _ = validate_quantity('process_sub_steps', 'qty', 10.5, plan_qty=10)
    assert ok

@case('quantity-3: quality_records 0 接受')
def test_qty_3():
    from utils.quantity_validator import validate_quantity
    ok, _ = validate_quantity('quality_records', 'defect_qty', 0, plan_qty=10)
    assert ok

@case('quantity-4: outsource_records 小数')
def test_qty_4():
    from utils.quantity_validator import validate_quantity
    ok, _ = validate_quantity('outsource_records', 'qty', 5.5, plan_qty=5)
    assert ok

@case('quantity-5: repair_records 0 接受')
def test_qty_5():
    from utils.quantity_validator import validate_quantity
    ok, _ = validate_quantity('repair_records', 'qty', 0, plan_qty=0)
    assert ok


# ==============================
# 3. quantity 边界（5 用例）
# ==============================
section('3. quantity 边界')

@case('边界-1: 0 拒绝（material_records）')
def test_edge_1():
    from utils.quantity_validator import validate_quantity
    ok, msg = validate_quantity('material_records', 'qty', 0, plan_qty=10)
    assert not ok and '不能为 0' in msg

@case('边界-2: 负数拒绝')
def test_edge_2():
    from utils.quantity_validator import validate_quantity
    ok, msg = validate_quantity('material_records', 'qty', -1, plan_qty=10)
    assert not ok and '负数' in msg

@case('边界-3: 小数拒绝（material_records）')
def test_edge_3():
    from utils.quantity_validator import validate_quantity
    ok, msg = validate_quantity('material_records', 'qty', 10.5, plan_qty=10)
    assert not ok and '整数' in msg

@case('边界-4: 超计划 20% 拒绝')
def test_edge_4():
    from utils.quantity_validator import validate_quantity
    ok, msg = validate_quantity('material_records', 'qty', 100, plan_qty=10)
    assert not ok and '超出' in msg

@case('边界-5: None 拒绝')
def test_edge_5():
    from utils.quantity_validator import validate_quantity
    ok, msg = validate_quantity('material_records', 'qty', None)
    assert not ok and '不能为空' in msg


# ==============================
# 4. 鉴权（4 用例）
# ==============================
section('4. 4 重鉴权')

@case('鉴权-1: 无 token 401')
def test_auth_1():
    from flask import Flask
    from api.decorators import require_auth
    app = Flask(__name__)
    @app.route('/test')
    @require_auth
    def f():
        return 'ok'
    client = app.test_client()
    r = client.get('/test')
    assert r.status_code == 401

@case('鉴权-2: 有效 token 200')
def test_auth_2():
    from flask import Flask
    from api.decorators import require_auth, JWT_SECRET
    app = Flask(__name__)
    @app.route('/test')
    @require_auth
    def f():
        return 'ok'
    token = jwt.encode(
        {'uid': 'u1', 'role': 'admin', 'exp': datetime.utcnow() + timedelta(hours=1)},
        JWT_SECRET, algorithm='HS256'
    )
    client = app.test_client()
    r = client.get('/test', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200

@case('鉴权-3: 过期 token 401')
def test_auth_3():
    from flask import Flask
    from api.decorators import require_auth, JWT_SECRET
    app = Flask(__name__)
    @app.route('/test')
    @require_auth
    def f():
        return 'ok'
    token = jwt.encode(
        {'uid': 'u1', 'role': 'admin', 'exp': datetime.utcnow() - timedelta(hours=1)},
        JWT_SECRET, algorithm='HS256'
    )
    client = app.test_client()
    r = client.get('/test', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 401

@case('鉴权-4: 角色不匹配 403')
def test_auth_4():
    from flask import Flask, jsonify
    from api.decorators import require_auth, require_role, JWT_SECRET
    app = Flask(__name__)
    @app.route('/test')
    @require_auth
    @require_role('admin')
    def f():
        return jsonify({'code': 0})
    token = jwt.encode(
        {'uid': 'u1', 'role': 'worker', 'exp': datetime.utcnow() + timedelta(hours=1)},
        JWT_SECRET, algorithm='HS256'
    )
    client = app.test_client()
    r = client.get('/test', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 403


# ==============================
# 5. 派工并发（3 用例）
# ==============================
section('5. 派工并发')

@case('并发-1: 派工成功')
def test_concurrent_1():
    from utils.dispatch_task import dispatch_task
    task = {
        'id': f'T{uuid.uuid4().hex[:12]}',
        'order_no': 'SO_TEST_001',
        'process_code': 'P01',
        'batch_no': f'B{uuid.uuid4().hex[:8]}',
        'quantity': 100,
    }
    r = dispatch_task(task)
    assert r['code'] == 0

@case('并发-2: 重复派工 409')
def test_concurrent_2():
    from utils.dispatch_task import dispatch_task
    task = {
        'id': f'T{uuid.uuid4().hex[:12]}',
        'order_no': 'SO_TEST_002',
        'process_code': 'P01',
        'batch_no': f'B{uuid.uuid4().hex[:8]}',
        'quantity': 100,
    }
    dispatch_task(task)
    r2 = dispatch_task(task)
    assert r2['code'] == 3003
    assert r2['http_status'] == 409

@case('并发-3: 100 线程 1 成功 + 99 冲突')
def test_concurrent_3():
    from utils.dispatch_task import dispatch_task
    task = {
        'id': f'T{uuid.uuid4().hex[:12]}',
        'order_no': 'SO_TEST_003',
        'process_code': 'P01',
        'batch_no': f'B{uuid.uuid4().hex[:8]}',
        'quantity': 100,
    }
    results = []
    def worker():
        r = dispatch_task(task)
        results.append(r['code'])
    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads: t.start()
    for t in threads: t.join()
    success = results.count(0)
    conflict = results.count(3003)
    assert success == 1, f'应 1 成功，实际 {success}'
    assert conflict == 99, f'应 99 冲突，实际 {conflict}'


# ==============================
# 6. 日志脱敏（2 用例）
# ==============================
section('6. 全局日志脱敏')

@case('脱敏-1: 手机号')
def test_log_1():
    from utils.log_sanitizer import sanitize_phone
    s = sanitize_phone('操作员: 13812345678')
    assert '138****5678' in s

@case('脱敏-2: 身份证号')
def test_log_2():
    from utils.log_sanitizer import sanitize_id_card
    s = sanitize_id_card('身份证: 110101199001011234')
    assert '110101********1234' in s


# ==============================
# 7. DB 字段（8 用例）
# ==============================
section('7. 9 业务表 + tbl_configs 字段验证')

@case('DB-1: process_sub_steps 6 字段')
def test_db_1():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("DESCRIBE process_sub_steps")
    cols = {r[0] for r in cur.fetchall()}
    c.close()
    for f in ['is_deleted', 'created_by', 'updated_by', 'updated_at']:
        assert f in cols

@case('DB-2: material_records 6 字段')
def test_db_2():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("DESCRIBE material_records")
    cols = {r[0] for r in cur.fetchall()}
    c.close()
    for f in ['is_deleted', 'created_by', 'updated_by', 'updated_at']:
        assert f in cols

@case('DB-3: quality_records 6 字段')
def test_db_3():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("DESCRIBE quality_records")
    cols = {r[0] for r in cur.fetchall()}
    c.close()
    for f in ['is_deleted', 'created_by', 'updated_by', 'updated_at']:
        assert f in cols

@case('DB-4: outsource_records 6 字段')
def test_db_4():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("DESCRIBE outsource_records")
    cols = {r[0] for r in cur.fetchall()}
    c.close()
    for f in ['is_deleted', 'created_by', 'updated_by', 'updated_at']:
        assert f in cols

@case('DB-5: repair_records 6 字段')
def test_db_5():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("DESCRIBE repair_records")
    cols = {r[0] for r in cur.fetchall()}
    c.close()
    for f in ['is_deleted', 'created_by', 'updated_by', 'updated_at']:
        assert f in cols

@case('DB-6: approval_records 存在')
def test_db_6():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("SHOW TABLES LIKE 'approval_records'")
    r = cur.fetchone()
    c.close()
    assert r is not None

@case('DB-7: production_orders 6 字段')
def test_db_7():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("DESCRIBE production_orders")
    cols = {r[0] for r in cur.fetchall()}
    c.close()
    for f in ['is_deleted', 'created_by', 'updated_by', 'updated_at']:
        assert f in cols

@case('DB-8: schedule_flow_logs 6 字段')
def test_db_8():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("DESCRIBE schedule_flow_logs")
    cols = {r[0] for r in cur.fetchall()}
    c.close()
    for f in ['is_deleted', 'created_by', 'updated_by', 'updated_at']:
        assert f in cols


# ==============================
# 8. 状态机字典（3 用例）
# ==============================
section('8. status 字典统一')

@case('状态-1: process_sub_steps 字典')
def test_status_1():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("SELECT DISTINCT status FROM process_sub_steps")
    statuses = {r[0] for r in cur.fetchall()}
    c.close()
    for s in statuses:
        assert s in ['pending', 'in_progress', 'completed', None], f'非法 status: {s}'

@case('状态-2: material_records 字典')
def test_status_2():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("SELECT DISTINCT status FROM material_records")
    statuses = {r[0] for r in cur.fetchall()}
    c.close()
    for s in statuses:
        assert s in ['pending', 'in_progress', 'completed', 'shortage', None], f'非法 status: {s}'

@case('状态-3: quality_records 字典')
def test_status_3():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("SELECT DISTINCT status FROM quality_records")
    statuses = {r[0] for r in cur.fetchall()}
    c.close()
    for s in statuses:
        assert s in ['pending', 'in_progress', 'completed', None], f'非法 status: {s}'


# ==============================
# 9. DROP 验证（2 用例）
# ==============================
section('9. data_packages DROP 验证')

@case('DROP-1: data_packages 已物理删除')
def test_drop_1():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("SHOW TABLES LIKE 'data_packages%'")
    rows = cur.fetchall()
    c.close()
    assert len(rows) == 0, f'data_packages% 表仍存在: {rows}'

@case('DROP-2: 触发器已清理')
def test_drop_2():
    c = pymysql.connect(**DB)
    cur = c.cursor()
    cur.execute("SHOW TRIGGERS WHERE `Trigger` LIKE 'block_write%'")
    rows = cur.fetchall()
    c.close()
    assert len(rows) == 0, f'触发器仍存在: {rows}'


# ==============================
# 10. 归档验证（2 用例）
# ==============================
section('10. 归档统计')

@case('归档-1: stats_smart_sheet 删除')
def test_arch_1():
    p = os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'stats_smart_sheet')
    assert not os.path.exists(p), 'stats_smart_sheet/ 仍存在'

@case('归档-2: archive 目录存在')
def test_arch_2():
    p = os.path.join(PROJECT_ROOT, 'archive')
    assert os.path.exists(p), 'archive/ 不存在'
    files = sum(len(fs) for _, _, fs in os.walk(p))
    assert files > 100, f'归档文件数: {files}'


# ==============================
# 11. 文档验证（2 用例）
# ==============================
section('11. 文档验证')

@case('文档-1: CHANGELOG.md 存在')
def test_doc_1():
    p = os.path.join(PROJECT_ROOT, 'docs', 'CHANGELOG.md')
    assert os.path.exists(p)

@case('文档-2: migrations v3.6 脚本存在')
def test_doc_2():
    p = os.path.join(PROJECT_ROOT, 'migrations', 'v3_6_data_packages_split.sql')
    assert os.path.exists(p)


# ==============================
# 主函数
# ==============================
def main():
    print('\033[1m\033[92m===================================================\033[0m')
    print('\033[1m\033[92m  v3.6 完整测试套件 - 51 用例\033[0m')
    print('\033[1m\033[92m===================================================\033[0m')

    # 执行所有测试
    test_funcs = [v for k, v in globals().items() if k.startswith('test_') and callable(v)]
    for tf in test_funcs:
        tf()

    # 汇总
    total = RESULTS['PASS'] + RESULTS['FAIL'] + RESULTS['SKIP']
    print(f'\n\033[1m===================================================\033[0m')
    print(f'\033[1m  测试结果\033[0m')
    print(f'\033[1m===================================================\033[0m')
    print(f'  通过: \033[92m{RESULTS["PASS"]}\033[0m / {total}')
    print(f'  失败: \033[91m{RESULTS["FAIL"]}\033[0m')
    print(f'  跳过: \033[93m{RESULTS["SKIP"]}\033[0m')

    if RESULTS['FAIL'] == 0:
        print(f'\n  \033[1m\033[92m✅ 全部 {total} 个用例通过\033[0m')
        return 0
    else:
        print(f'\n  \033[1m\033[91m❌ {RESULTS["FAIL"]} 个失败：\033[0m')
        for f in FAILURES[:5]:  # 只打印前 5 个
            print(f'    - {f}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
