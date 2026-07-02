# -*- coding: utf-8 -*-
"""
CI 检查脚本 - 阶段 1 (CP-1)
"""
import os
import sys
import pymysql

PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())
MOBILE_API = os.path.join(PROJECT_ROOT, 'mobile_api_ai')

class C:
    G = '\033[92m'
    R = '\033[91m'
    Y = '\033[93m'
    B = '\033[94m'
    E = '\033[0m'

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 3306,
    'user': 'root',
    'password': '88888888',
    'database': 'container_center',
}

def get_conn():
    return pymysql.connect(**DB_CONFIG)

def passed(name, details=''):
    print(f'{C.G}[PASS]{C.E} {name}')
    if details:
        print(f'       {details}')

def failed(name, details=''):
    print(f'{C.R}[FAIL]{C.E} {name}')
    if details:
        print(f'       {details}')

def check_1_ddl_upgrade():
    print(f'\n{C.B}[1/8] 9 业务表 DDL 升级检查{C.E}')
    required = ['is_deleted', 'created_by', 'updated_by', 'updated_at']
    tables = [
        'process_sub_steps', 'material_records', 'quality_records',
        'outsource_records', 'repair_records', 'approval_records',
        'production_orders', 'schedule_flow_logs', 'process_records'
    ]
    try:
        c = get_conn()
        cur = c.cursor()
        missing = []
        for t in tables:
            cur.execute(f"SELECT COLUMN_NAME FROM information_schema.columns WHERE TABLE_SCHEMA='container_center' AND TABLE_NAME='{t}'")
            cols = [r[0] for r in cur.fetchall()]
            for f in required:
                if f not in cols:
                    missing.append(f'{t}.{f}')
        c.close()
        if missing:
            failed('DDL 升级', f'缺少字段: {missing}')
            return False
        passed('DDL 升级', '9 业务表全部有 is_deleted/created_by/updated_by/updated_at')
        return True
    except Exception as e:
        failed('DDL 升级', f'错误: {e}')
        return False

def check_2_approval_records():
    print(f'\n{C.B}[2/8] approval_records 表检查{C.E}')
    try:
        c = get_conn()
        cur = c.cursor()
        cur.execute("SHOW TABLES LIKE 'approval_records'")
        result = cur.fetchone()
        c.close()
        if result:
            passed('approval_records', '表已存在')
            return True
        failed('approval_records', '表不存在')
        return False
    except Exception as e:
        failed('approval_records', f'错误: {e}')
        return False

def check_3_data_migration():
    print(f'\n{C.B}[3/8] 数据迁移检查（status 字典）{C.E}')
    try:
        c = get_conn()
        cur = c.cursor()
        cur.execute("SELECT status, COUNT(*) FROM process_sub_steps GROUP BY status")
        ps = cur.fetchall()
        cur.execute("SELECT status, COUNT(*) FROM material_records GROUP BY status")
        mr = cur.fetchall()
        cur.execute("SELECT status, COUNT(*) FROM quality_records GROUP BY status")
        qr = cur.fetchall()
        c.close()

        print(f'       process_sub_steps: {ps}')
        print(f'       material_records: {mr}')
        print(f'       quality_records: {qr}')

        bad = ['待开始', '待备料', '缺料', 'quality_reported', 'quality_re_received']
        all_data = str(ps + mr + qr)
        for b in bad:
            if b in all_data:
                failed('数据迁移', f'仍有 {b}')
                return False
        passed('数据迁移', 'status 字典已统一')
        return True
    except Exception as e:
        failed('数据迁移', f'错误: {e}')
        return False

def check_4_exception_handler():
    print(f'\n{C.B}[4/8] 全局异常处理器检查{C.E}')
    path = os.path.join(MOBILE_API, 'utils', 'exception_handler.py')
    if os.path.exists(path):
        passed('异常处理器', 'utils/exception_handler.py 已创建')
        return True
    failed('异常处理器', f'文件不存在: {path}')
    return False

def check_5_no_hardcoded_password():
    print(f'\n{C.B}[5/8] 硬编码密码检查{C.E}')
    import subprocess
    try:
        r = subprocess.run(
            f'grep -rn "password.=.88888888" "{MOBILE_API}" "{os.path.join(PROJECT_ROOT, "scripts")}" --include=*.py',
            capture_output=True, text=True, timeout=20, shell=True
        )
        if '88888888' in r.stdout:
            failed('硬编码密码', f'仍存在: {r.stdout[:200]}')
            return False
        passed('硬编码密码', '已清除')
        return True
    except Exception as e:
        failed('硬编码密码', f'错误: {e}')
        return False

def check_6_global_var():
    print(f'\n{C.B}[6/8] global 变量摸底检查{C.E}')
    import subprocess
    try:
        r = subprocess.run(
            f'grep -rn "global [a-zA-Z_]" "{MOBILE_API}" --include=*.py',
            capture_output=True, text=True, timeout=20, shell=True
        )
        lines = [l for l in r.stdout.split('\n') if l.strip()]
        if not lines:
            passed('global 变量', '无违规')
            return True
        print(f'       发现 {len(lines)} 处（清单已记录到 T17 任务）:')
        for l in lines[:5]:
            print(f'       {l}')
        if len(lines) > 5:
            print(f'       ...还有 {len(lines) - 5} 处')
        passed('global 变量', f'摸底完成（{len(lines)} 处待清理）')
        return True
    except Exception as e:
        failed('global 变量', f'错误: {e}')
        return False

def check_7_data_packages_gone():
    print(f'\n{C.B}[7/8] data_packages DROP 检查{C.E}')
    try:
        c = get_conn()
        cur = c.cursor()
        cur.execute("SHOW TABLES LIKE 'data_packages'")
        if cur.fetchone():
            failed('data_packages', '表仍存在（需要 RENAME+触发器+DROP）')
            c.close()
            return False
        cur.execute("SHOW TABLES LIKE 'data_packages_deprecated'")
        deprecated = cur.fetchone()
        c.close()
        if deprecated:
            passed('data_packages', '已 RENAME 为 data_packages_deprecated（观察期）')
        else:
            passed('data_packages', '已 DROP')
        return True
    except Exception as e:
        failed('data_packages', f'错误: {e}')
        return False

def check_8_mysql_storage_clean():
    print(f'\n{C.B}[8/8] mysql_storage.py 清理检查{C.E}')
    path = os.path.join(MOBILE_API, 'storage', 'mysql_storage.py')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if "CREATE TABLE IF NOT EXISTS data_packages" in content:
        failed('mysql_storage.py', '仍包含 data_packages CREATE')
        return False
    if "CREATE TABLE IF NOT EXISTS enterprise_structure" in content:
        failed('mysql_storage.py', '仍包含 enterprise_structure CREATE')
        return False
    passed('mysql_storage.py', 'data_packages/enterprise_structure 已移除')
    return True

def main():
    print(f'{C.B}==================================================={C.E}')
    print(f'{C.B}  CP-1 检查：data_packages_split_v3 阶段 1{C.E}')
    print(f'{C.B}==================================================={C.E}')

    results = [
        ('9 业务表 DDL 升级', check_1_ddl_upgrade()),
        ('approval_records 表', check_2_approval_records()),
        ('数据迁移', check_3_data_migration()),
        ('异常处理器', check_4_exception_handler()),
        ('硬编码密码', check_5_no_hardcoded_password()),
        ('global 变量摸底', check_6_global_var()),
        ('data_packages DROP', check_7_data_packages_gone()),
        ('mysql_storage.py 清理', check_8_mysql_storage_clean()),
    ]

    print(f'\n{C.B}==================================================={C.E}')
    print(f'{C.B}  CP-1 检查结果汇总{C.E}')
    print(f'{C.B}==================================================={C.E}')

    passed_count = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f'\n通过: {passed_count}/{total}')

    if passed_count == total:
        print(f'{C.G}✅ CP-1 全部通过，可以进入阶段 2{C.E}')
        return 0
    else:
        print(f'{C.R}❌ CP-1 未通过{C.E}')
        for name, ok in results:
            status = f'{C.G}✅{C.E}' if ok else f'{C.R}❌{C.E}'
            print(f'   {status} {name}')
        return 1

if __name__ == '__main__':
    sys.exit(main())
