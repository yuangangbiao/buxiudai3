# -*- coding: utf-8 -*-
"""
[v3.6] CP-2 检查脚本 - 阶段 2 完成后

检查项:
- 11 路由白名单（T1）
- 4 重鉴权装饰器（T2b）
- quantity 业务化校验（T3）
- 派工并发 INSERT + IntegrityError（T4）
- T6 自动审计装饰器
- T6.5 日志脱敏
- T20 for remove 反模式扫描
- T23 统一日志路径
"""
import os
import sys
import subprocess
import pymysql

PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())
MOBILE_API = os.path.join(PROJECT_ROOT, 'mobile_api_ai')

class C:
    G = '\033[92m'
    R = '\033[91m'
    Y = '\033[93m'
    B = '\033[94m'
    E = '\033[0m'

DB = dict(host='localhost', port=3306, user='root',
          password='88888888', database='container_center')


def passed(name, details=''):
    print(f'{C.G}[PASS]{C.E} {name}')
    if details:
        print(f'       {details}')


def failed(name, details=''):
    print(f'{C.R}[FAIL]{C.E} {name}')
    if details:
        print(f'       {details}')


def check_t1_routing():
    """T1: 11 路由模块存在"""
    print(f'\n{C.B}[1/8] T1 11 路由模块{C.E}')
    path = os.path.join(MOBILE_API, 'storage', 'data_type_router.py')
    if not os.path.exists(path):
        failed('T1 路由模块', '文件不存在')
        return False
    passed('T1 路由模块', 'data_type_router.py 已创建')
    return True


def check_t2b_decorators():
    """T2b: 4 重鉴权装饰器"""
    print(f'\n{C.B}[2/8] T2b 鉴权装饰器{C.E}')
    path = os.path.join(MOBILE_API, 'api', 'decorators.py')
    if not os.path.exists(path):
        failed('T2b 装饰器', '文件不存在')
        return False
    with open(path) as f:
        content = f.read()
    for name in ['require_auth', 'require_role', 'require_owner_or_admin', 'audit_log']:
        if f'def {name}' not in content:
            failed('T2b 装饰器', f'缺少 {name}')
            return False
    passed('T2b 装饰器', '4 个装饰器全部定义')
    return True


def check_t3_quantity():
    """T3: quantity 业务化校验"""
    print(f'\n{C.B}[3/8] T3 quantity 校验{C.E}')
    path = os.path.join(MOBILE_API, 'utils', 'quantity_validator.py')
    if not os.path.exists(path):
        failed('T3 quantity 校验', '文件不存在')
        return False
    passed('T3 quantity 校验', 'utils/quantity_validator.py 已创建')
    return True


def check_t4_dispatch():
    """T4: 派工并发"""
    print(f'\n{C.B}[4/8] T4 派工并发模块{C.E}')
    path = os.path.join(MOBILE_API, 'utils', 'dispatch_task.py')
    if not os.path.exists(path):
        failed('T4 派工', '文件不存在')
        return False
    with open(path) as f:
        content = f.read()
    if 'IntegrityError' not in content or 'conn.rollback' not in content:
        failed('T4 派工', '缺少 IntegrityError 处理')
        return False
    passed('T4 派工', 'utils/dispatch_task.py 含并发防护')
    return True


def check_t6_5_log_sanitize():
    """T6.5: 日志脱敏"""
    print(f'\n{C.B}[5/8] T6.5 日志脱敏{C.E}')
    path = os.path.join(MOBILE_API, 'utils', 'log_sanitizer.py')
    if not os.path.exists(path):
        failed('T6.5 日志脱敏', '文件不存在')
        return False
    passed('T6.5 日志脱敏', 'utils/log_sanitizer.py 已创建')
    return True


def check_t20_for_remove():
    """T20: for remove 反模式扫描"""
    print(f'\n{C.B}[6/8] T20 for remove 反模式扫描{C.E}')
    try:
        r = subprocess.run(
            ['grep', '-rn', r'for .* in .*:\s*$', MOBILE_API,
             '--include=*.py', '-A', '3'],
            capture_output=True, text=True, timeout=20, shell=True
        )
        bad_patterns = []
        lines = r.stdout.split('\n')
        for i, line in enumerate(lines):
            if 'for ' in line and 'in ' in line:
                for j in range(i + 1, min(i + 5, len(lines))):
                    if '.remove(' in lines[j]:
                        bad_patterns.append(f'{line.strip()} -> {lines[j].strip()}')
        if bad_patterns:
            failed('T20 for remove', f'发现 {len(bad_patterns)} 处反模式')
            for p in bad_patterns[:3]:
                print(f'       {p}')
            return False
        passed('T20 for remove', '无反模式')
        return True
    except Exception as e:
        failed('T20 for remove', f'扫描失败: {e}')
        return False


def check_t23_log_path():
    """T23: 统一日志路径"""
    print(f'\n{C.B}[7/8] T23 统一日志路径{C.E}')
    try:
        r = subprocess.run(
            ['grep', '-rn', r"D:\\", MOBILE_API,
             '--include=*.py'],
            capture_output=True, text=True, timeout=20, shell=True
        )
        hardcoded = [l for l in r.stdout.split('\n') if 'open(' in l and 'D:' in l]
        if hardcoded:
            failed('T23 日志路径', f'发现 {len(hardcoded)} 处硬编码 D:\\')
            for h in hardcoded[:3]:
                print(f'       {h}')
            return False
        passed('T23 日志路径', '无硬编码路径')
        return True
    except Exception as e:
        failed('T23 日志路径', f'扫描失败: {e}')
        return False


def check_real_db_query():
    """真实 DB 查询：11 路由 + 软删除"""
    print(f'\n{C.B}[8/8] 真实 DB 查询（11 路由 + 软删除）{C.E}')
    try:
        sys.path.insert(0, MOBILE_API)
        from storage.data_type_router import validate_data_type, TASK_TYPE_TABLE_MAP
        c = pymysql.connect(**DB)
        cur = c.cursor()
        for dt, table in TASK_TYPE_TABLE_MAP.items():
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE is_deleted=0")
                count = cur.fetchone()[0]
                print(f'       {dt} -> {table}: {count} 行')
            except Exception as e:
                print(f'       {dt} -> {table}: ❌ {e}')
                return False
        c.close()
        passed('11 路由查询', '11 业务表全部可查询')
        return True
    except Exception as e:
        failed('11 路由查询', f'错误: {e}')
        return False


def main():
    print(f'{C.B}==================================================={C.E}')
    print(f'{C.B}  CP-2 检查：data_packages_split_v3 阶段 2{C.E}')
    print(f'{C.B}==================================================={C.E}')

    results = [
        ('T1 11 路由', check_t1_routing()),
        ('T2b 鉴权装饰器', check_t2b_decorators()),
        ('T3 quantity 校验', check_t3_quantity()),
        ('T4 派工并发', check_t4_dispatch()),
        ('T6.5 日志脱敏', check_t6_5_log_sanitize()),
        ('T20 for remove', check_t20_for_remove()),
        ('T23 日志路径', check_t23_log_path()),
        ('DB 11 路由查询', check_real_db_query()),
    ]

    print(f'\n{C.B}==================================================={C.E}')
    print(f'{C.B}  CP-2 检查结果汇总{C.E}')
    print(f'{C.B}==================================================={C.E}')

    passed_count = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f'\n通过: {passed_count}/{total}')

    if passed_count == total:
        print(f'{C.G}✅ CP-2 全部通过，可以进入阶段 3{C.E}')
        return 0
    else:
        print(f'{C.R}❌ CP-2 未通过{C.E}')
        for name, ok in results:
            status = f'{C.G}✅{C.E}' if ok else f'{C.R}❌{C.E}'
            print(f'   {status} {name}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
