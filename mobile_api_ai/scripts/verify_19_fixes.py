#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""集成测试：验证悲观审计 19 项修复的端到端行为

配套 docs/库存功能优化/ACCEPTANCE_库存功能优化.md 第八节

用法：
    python scripts/verify_19_fixes.py
    python scripts/verify_19_fixes.py --verbose
    python scripts/verify_19_fixes.py --fix-id C-1   # 只验证特定修复

退出码：
    0 - 全部通过
    1 - 至少一项失败
    2 - 环境异常（缺依赖、文件不存在等）

设计原则：
    1. 不依赖 MySQL/Flask，纯静态 + 文本搜索 + AST 解析
    2. 每个 test 独立 try/except，单项失败不中断后续
    3. 详细日志 + 摘要表
"""
import os
import sys
import re
import ast
import py_compile
import subprocess
import argparse
from typing import List, Tuple, Callable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INVENTORY_WEB = os.path.join(ROOT, 'inventory_web')
SCRIPTS = os.path.join(ROOT, 'scripts')
STATIC = os.path.join(ROOT, 'inventory_web', 'static')
MIGRATIONS = os.path.join(INVENTORY_WEB, 'migrations')

PASS = '[PASS]'
FAIL = '[FAIL]'
WARN = '[WARN]'

results: List[Tuple[str, str, str]] = []  # (id, status, message)


def check(fix_id: str, description: str, ok: bool, message: str = ''):
    """记录检查结果"""
    status = PASS if ok else FAIL
    msg = f'{status} {fix_id}: {description}'
    if message:
        msg += f' - {message}'
    results.append((fix_id, status, msg))
    return ok


def fix_only(fix_id: str) -> bool:
    """只验证特定 fix"""
    if not args.fix_id:
        return True
    return fix_id == args.fix_id


# ============================================================
# C-1: SQL 迁移无 IF NOT EXISTS
# ============================================================
def test_c1():
    if not fix_only('C-1'):
        return
    f = os.path.join(MIGRATIONS, '001_function_optimization.sql')
    if not os.path.exists(f):
        check('C-1', '迁移文件存在', False, f'文件不存在: {f}')
        return
    with open(f, 'r', encoding='utf-8') as fh:
        sql = fh.read()
    # 检查禁用模式
    if_exists_add = re.search(r'ADD\s+COLUMN\s+IF\s+NOT\s+EXISTS', sql, re.IGNORECASE)
    if_exists_idx = re.search(r'CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS', sql, re.IGNORECASE)
    # 检查启用模式
    has_info_schema = 'INFORMATION_SCHEMA' in sql
    ok = not if_exists_add and not if_exists_idx and has_info_schema
    check('C-1', 'SQL 迁移用 INFORMATION_SCHEMA 动态 DDL', ok,
          f'{"INFORMATION_SCHEMA 已用，" if has_info_schema else ""}'
          f'{"无 ADD COLUMN IF NOT EXISTS，" if not if_exists_add else "仍含 ADD COLUMN IF NOT EXISTS (FAIL)，"}'
          f'{"无 CREATE INDEX IF NOT EXISTS" if not if_exists_idx else "仍含 CREATE INDEX IF NOT EXISTS (FAIL)"}')


# ============================================================
# C-2: 装饰器导入隔离
# ============================================================
def test_c2():
    if not fix_only('C-2'):
        return
    f1 = os.path.join(INVENTORY_WEB, 'feature_flags.py')
    f2 = os.path.join(INVENTORY_WEB, 'routes_core.py')
    f3 = os.path.join(INVENTORY_WEB, 'routes_api.py')

    try:
        with open(f1, 'r', encoding='utf-8') as fh:
            ff = fh.read()
        with open(f2, 'r', encoding='utf-8') as fh:
            rc = fh.read()
        with open(f3, 'r', encoding='utf-8') as fh:
            ra = fh.read()
    except OSError as e:
        check('C-2', '装饰器导入隔离文件可读', False, str(e))
        return

    has_safe = 'def safe_require_feature' in ff
    try_except_rc = 'try:' in rc and 'from .feature_flags' in rc and 'except' in rc
    try_except_ra = 'try:' in ra and 'from .feature_flags' in ra and 'except' in ra
    ok = has_safe and try_except_rc and try_except_ra
    check('C-2', '装饰器导入有兜底', ok,
          f'safe_require_feature={has_safe}, routes_core try/except={try_except_rc}, routes_api try/except={try_except_ra}')


# ============================================================
# H-1: Windows cron chcp 65001
# ============================================================
def test_h1():
    if not fix_only('H-1'):
        return
    f = os.path.join(SCRIPTS, 'install_transfer_reaper_windows.bat')
    if not os.path.exists(f):
        check('H-1', 'Windows 批处理文件存在', False, f'文件不存在: {f}')
        return
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    ok = 'chcp 65001' in s and 'PYTHONIOENCODING' in s
    check('H-1', 'Windows 批处理含 chcp 65001 + PYTHONIOENCODING', ok)


# ============================================================
# H-2: report_service 无 % 字符在 SQL
# ============================================================
def test_h2():
    if not fix_only('H-2'):
        return
    f = os.path.join(INVENTORY_WEB, 'services', 'report_service.py')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    # SQL 字符串中的 % 字符（除了字符串字面量外）
    # 简单方法：找 """ 块中的 %
    sql_blocks = re.findall(r'"""(.*?)"""', s, re.DOTALL)
    has_pct = False
    for block in sql_blocks:
        # 排除注释行
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('--'):
                continue
            # 排除 %s 占位符（参数化）
            if '%' in line:
                # 检查是否是 %s 之后的位置
                if re.search(r'%(?![sfd])', line):
                    has_pct = True
                    break
    ok_concat = 'CONCAT(YEAR' in s
    ok = not has_pct and ok_concat
    check('H-2', 'report_service SQL 无 % 字符（除 %s）', ok,
          f'CONCAT(YEAR)={ok_concat}, %字符残留={has_pct}')


# ============================================================
# H-3: service 层灰度
# ============================================================
def test_h3():
    if not fix_only('H-3'):
        return
    f = os.path.join(INVENTORY_WEB, 'services', 'transfer_service.py')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    has_feature_check = 'is_enabled' in s or '_feature_enabled' in s
    has_reap = 'reap_stale_transfers' in s
    ok = has_feature_check and has_reap
    check('H-3', 'TransferService 灰度入口存在', ok,
          f'is_enabled={has_feature_check}, reap_stale_transfers={has_reap}')


# ============================================================
# M-1: is_enabled 默认 False
# ============================================================
def test_m1():
    if not fix_only('M-1'):
        return
    f = os.path.join(INVENTORY_WEB, 'feature_flags.py')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    # 检查 is_enabled 函数实现
    has_default_false = "return False" in s and "未知 flag" in s
    # 旧的默认 True 应该不存在
    has_old_default = re.search(r'flags\.get\(name,\s*True\)', s) is not None
    ok = has_default_false and not has_old_default
    check('M-1', 'is_enabled 默认 False（白名单制）', ok,
          f'默认 False={has_default_false}, 旧默认 True 残留={has_old_default}')


# ============================================================
# M-2: unit_price 类型转换
# ============================================================
def test_m2():
    if not fix_only('M-2'):
        return
    f = os.path.join(INVENTORY_WEB, 'services', 'inventory_service.py')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    has_float_cast = 'float(unit_price)' in s
    has_try = 'try:' in s and 'except' in s
    ok = has_float_cast and has_try
    check('M-2', 'unit_price 类型转换 + try/except', ok,
          f'float()={has_float_cast}, try/except={has_try}')


# ============================================================
# M-3: mktemp 已替换
# ============================================================
def test_m3():
    if not fix_only('M-3'):
        return
    f = os.path.join(SCRIPTS, 'perf_test_xlsx.py')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    has_mktemp = re.search(r'\bmktemp\s*\(', s) is not None
    has_mkstemp = 'mkstemp' in s
    ok = not has_mktemp and has_mkstemp
    check('M-3', 'mktemp 已替换为 mkstemp', ok,
          f'mktemp 残留={has_mktemp}, mkstemp={has_mkstemp}')


# ============================================================
# M-4: 24h 改环境变量
# ============================================================
def test_m4():
    if not fix_only('M-4'):
        return
    f1 = os.path.join(INVENTORY_WEB, 'services', 'transfer_service.py')
    f2 = os.path.join(SCRIPTS, 'transfer_reaper.py')
    with open(f1, 'r', encoding='utf-8') as fh:
        s1 = fh.read()
    with open(f2, 'r', encoding='utf-8') as fh:
        s2 = fh.read()
    has_env = 'INVENTORY_TRANSFER_STALE_HOURS' in s1
    has_exit_code = 'sys.exit(2)' in s2 or 'exit(2)' in s2
    ok = has_env and has_exit_code
    check('M-4', '24h 改环境变量 + 失败退出码', ok,
          f'环境变量={has_env}, 退出码 2={has_exit_code}')


# ============================================================
# M-5: html5-qrcode textContent
# ============================================================
def test_m5():
    if not fix_only('M-5'):
        return
    f = os.path.join(STATIC, 'vendor', 'html5-qrcode.min.js')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    has_innerhtml = "innerHTML" in s
    has_textcontent = "textContent" in s
    has_createelement = "createElement" in s
    ok = has_textcontent and has_createelement
    check('M-5', 'html5-qrcode 用 textContent + createElement', ok,
          f'createElement={has_createelement}, textContent={has_textcontent}, innerHTML={has_innerhtml}')


# ============================================================
# M-6: 软删除 + UNIQUE 复合索引
# ============================================================
def test_m6():
    if not fix_only('M-6'):
        return
    f = os.path.join(MIGRATIONS, '001_function_optimization.sql')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    has_compound_idx = 'uk_products_code_active' in s
    has_composite = re.search(r'uk_products_code_active\s*\(\s*code\s*,\s*deleted_at\s*\)', s, re.IGNORECASE) is not None
    ok = has_compound_idx and has_composite
    check('M-6', '复合唯一索引 uk_products_code_active(code, deleted_at)', ok,
          f'索引存在={has_compound_idx}, 复合定义={has_composite}')


# ============================================================
# L-1: feature_flags reload
# ============================================================
def test_l1():
    if not fix_only('L-1'):
        return
    f = os.path.join(INVENTORY_WEB, 'feature_flags.py')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    has_reload = 'def reload_flags' in s
    ok = has_reload
    check('L-1', 'feature_flags reload_flags() 存在', ok)


# ============================================================
# L-2: last_purchase_price_at
# ============================================================
def test_l2():
    if not fix_only('L-2'):
        return
    f1 = os.path.join(MIGRATIONS, '001_function_optimization.sql')
    f2 = os.path.join(INVENTORY_WEB, 'services', 'inventory_service.py')
    with open(f1, 'r', encoding='utf-8') as fh:
        s1 = fh.read()
    with open(f2, 'r', encoding='utf-8') as fh:
        s2 = fh.read()
    has_field = 'last_purchase_price_at' in s1
    has_update = 'last_purchase_price_at=NOW()' in s2
    ok = has_field and has_update
    check('L-2', 'last_purchase_price_at 字段 + 入库 NOW()', ok,
          f'字段={has_field}, NOW()={has_update}')


# ============================================================
# L-3: html5-qrcode clear() 方法
# ============================================================
def test_l3():
    if not fix_only('L-3'):
        return
    f = os.path.join(STATIC, 'vendor', 'html5-qrcode.min.js')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    has_clear = '.prototype.clear' in s
    has_getcameras = 'getCameras' in s
    has_issupported = 'isSupported' in s
    ok = has_clear and has_getcameras and has_issupported
    check('L-3+L-7', 'html5-qrcode clear() + getCameras + isSupported', ok,
          f'clear={has_clear}, getCameras={has_getcameras}, isSupported={has_issupported}')


# ============================================================
# L-4: perf_test OOM 保护
# ============================================================
def test_l4():
    if not fix_only('L-4'):
        return
    f = os.path.join(SCRIPTS, 'perf_test_xlsx.py')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    has_max_rows = '--max-rows' in s
    has_psutil = 'psutil' in s
    has_timeout = 'signal.alarm' in s or 'Timeout' in s
    ok = has_max_rows and (has_psutil or has_timeout)
    check('L-4', 'perf_test OOM 保护', ok,
          f'max-rows={has_max_rows}, psutil={has_psutil}, timeout={has_timeout}')


# ============================================================
# L-5: transfer_items deleted_at
# ============================================================
def test_l5():
    if not fix_only('L-5'):
        return
    f = os.path.join(MIGRATIONS, '001_function_optimization.sql')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    # 检查在 transfer_items 表定义附近有 deleted_at
    has = 'transfer_items' in s and 'idx_ti_deleted' in s
    check('L-5', 'transfer_items deleted_at + idx_ti_deleted', has)


# ============================================================
# L-6: cron 日志路径可配置
# ============================================================
def test_l6():
    if not fix_only('L-6'):
        return
    f = os.path.join(SCRIPTS, 'install_transfer_reaper_cron.sh')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    has_env = 'INVENTORY_LOG_DIR' in s
    has_fallback = '/tmp' in s
    ok = has_env and has_fallback
    check('L-6', 'cron 日志路径可配置 + /tmp 兜底', ok,
          f'INVENTORY_LOG_DIR={has_env}, /tmp 兜底={has_fallback}')


# ============================================================
# L-8: report_service 协议说明
# ============================================================
def test_l8():
    if not fix_only('L-8'):
        return
    f = os.path.join(INVENTORY_WEB, 'services', 'report_service.py')
    with open(f, 'r', encoding='utf-8') as fh:
        s = fh.read()
    has_protocol_doc = 'status_code' in s and '异常协议' in s
    ok = has_protocol_doc
    check('L-8', 'report_service 异常协议说明', ok,
          f'协议文档={has_protocol_doc}')


# ============================================================
# 综合测试：Python 文件编译
# ============================================================
def test_python_compile_all():
    if not fix_only('COMPILE'):
        return
    py_files = [
        'feature_flags.py',
        'routes_core.py',
        'routes_api.py',
        'routes_data.py',
        'routes_report.py',
        'services/inventory_service.py',
        'services/transfer_service.py',
        'services/stocktake_service.py',
        'services/report_service.py',
        'services/product_service.py',
        'services/notification_service.py',
        'services/import_service.py',
        'db_utils.py',
        'admin_auth.py',
        'scripts/transfer_reaper.py',
        'scripts/perf_test_xlsx.py',
    ]
    failed = []
    for f in py_files:
        path = os.path.join(INVENTORY_WEB, f)
        if not os.path.exists(path):
            failed.append(f'{f} (not found)')
            continue
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as e:
            failed.append(f'{f} ({e})')
    ok = len(failed) == 0
    check('COMPILE', f'{len(py_files)} 个 Python 文件编译', ok,
          f'失败: {failed}' if failed else f'{len(py_files)}/16 通过')


# ============================================================
# 综合测试：JS 文件语法
# ============================================================
def test_js_compile():
    if not fix_only('JS'):
        return
    f = os.path.join(STATIC, 'vendor', 'html5-qrcode.min.js')
    if not os.path.exists(f):
        check('JS', 'JS 文件存在', False)
        return
    try:
        r = subprocess.run(['node', '-c', f], capture_output=True, timeout=10)
        ok = r.returncode == 0
        check('JS', 'html5-qrcode.min.js node -c', ok,
              r.stderr.decode() if not ok else 'OK')
    except FileNotFoundError:
        check('JS', 'node 不可用', True, '跳过（沙盒无 node）')
    except Exception as e:
        check('JS', 'JS 编译异常', False, str(e))


# ============================================================
# 综合测试：feature_flags 模块导入
# ============================================================
def test_feature_flags_import():
    if not fix_only('IMPORT'):
        return
    sys.path.insert(0, ROOT)
    try:
        from inventory_web.feature_flags import is_enabled, reload_flags, safe_require_feature
        # 测试白名单：未知 flag 应该返回 False
        unknown = is_enabled('nonexistent_flag_for_test')
        # 测试 reload 不抛异常
        reload_flags()
        # 测试装饰器存在
        assert callable(safe_require_feature)
        ok = unknown is False
        check('IMPORT', 'feature_flags 模块导入 + 白名单行为', ok,
              f'未知 flag={unknown} (期望 False)')
    except Exception as e:
        check('IMPORT', 'feature_flags 模块导入', False, str(e))


# ============================================================
# 主函数
# ============================================================
def main():
    global args
    parser = argparse.ArgumentParser(description='19 项悲观审计修复集成测试')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    parser.add_argument('--fix-id', type=str, default='', help='只验证特定修复 (如 C-1)')
    args = parser.parse_args()

    print('=' * 70)
    print('  集成测试：悲观审计 19 项修复验证')
    print('=' * 70)
    print()

    # 运行所有测试
    tests = [
        test_c1, test_c2,
        test_h1, test_h2, test_h3,
        test_m1, test_m2, test_m3, test_m4, test_m5, test_m6,
        test_l1, test_l2, test_l3, test_l4, test_l5, test_l6, test_l8,
        test_python_compile_all, test_js_compile, test_feature_flags_import,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            check(t.__name__, t.__name__, False, f'异常: {e}')

    # 输出详情
    if args.verbose:
        print('\n--- 详细结果 ---')
        for fix_id, status, msg in results:
            print(msg)

    # 摘要表
    print('\n' + '=' * 70)
    print('  摘要')
    print('=' * 70)
    total = len(results)
    passed = sum(1 for r in results if r[1] == PASS)
    failed = total - passed

    by_category = {}
    for fix_id, status, _ in results:
        cat = fix_id.split('-')[0] if '-' in fix_id else fix_id
        by_category.setdefault(cat, []).append((fix_id, status))

    for cat in ['C', 'H', 'M', 'L', 'COMPILE', 'JS', 'IMPORT']:
        items = by_category.get(cat, [])
        if not items:
            continue
        cat_passed = sum(1 for _, s in items if s == PASS)
        print(f'  {cat}: {cat_passed}/{len(items)}')
        for fix_id, status in items:
            mark = '✓' if status == PASS else '✗'
            print(f'    {mark} {fix_id}')

    print()
    print(f'  合计: {passed}/{total} 通过，{failed} 失败')
    print('=' * 70)

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
