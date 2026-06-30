# -*- coding: utf-8 -*-
"""
按模块功能分类运行测试脚本

功能：
- 按 models 模块运行测试（Order, Process, Production, Shipment等）
- 按 services 模块运行测试（OrderService, ProcessService等）
- 按 utils 模块运行测试（Validators, Helpers等）
- 按 core 模块运行测试

用法：
    python tests/run_tests_by_module.py list                      # 列出所有模块统计
    python tests/run_tests_by_module.py order                   # 运行 Order 模块测试
    python tests/run_tests_by_module.py production               # 运行 Production 模块测试
    python tests/run_tests_by_module.py all                     # 运行所有测试
"""
import os
import sys
import sqlite3
import subprocess
import argparse
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / '.workbuddy' / 'regression' / 'regression.db'


def get_db_connection():
    """获取数据库连接"""
    if not DB_PATH.exists():
        print(f"[FAIL] 数据库不存在: {DB_PATH}")
        print("请先运行: python .workbuddy/tools/regression_db.py import-tests")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def list_modules():
    """列出所有模块统计"""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("模块功能分类统计")
    print("=" * 60)

    # 1. 按 layer 分类（unit, integration, modular, e2e）
    print("\n【按测试层级分类】")
    print("-" * 50)
    cursor.execute("""
        SELECT 
            SUBSTR(module, 1, INSTR(module || '.', '.') - 1) as layer,
            COUNT(*) 
        FROM test_cases 
        GROUP BY layer 
        ORDER BY COUNT(*) DESC
    """)
    for row in cursor.fetchall():
        layer = row[0] or "(顶层)"
        count = row[1]
        print(f"  {layer}: {count} 个测试")

    # 2. 按子模块分类
    print("\n【按子模块分类】")
    print("-" * 50)
    cursor.execute("""
        SELECT 
            SUBSTR(module, INSTR(module, '.') + 1) as sub_module,
            COUNT(*) 
        FROM test_cases 
        WHERE module LIKE '%.%'
        GROUP BY sub_module 
        ORDER BY COUNT(*) DESC
        LIMIT 30
    """)
    for row in cursor.fetchall():
        sub = row[0] or "(无)"
        count = row[1]
        print(f"  {sub}: {count} 个测试")

    # 3. 按业务模块分类（models层）
    print("\n【models 层业务模块】")
    print("-" * 50)
    cursor.execute("""
        SELECT 
            SUBSTR(module, INSTR(module, '.') + 1) as business_module,
            COUNT(*) 
        FROM test_cases 
        WHERE module LIKE 'unit.models.%'
        GROUP BY business_module 
        ORDER BY COUNT(*) DESC
    """)
    for row in cursor.fetchall():
        module_name = row[0] or "(无)"
        count = row[1]
        print(f"  {module_name}: {count} 个测试")

    # 4. 按 services 层分类
    print("\n【services 层业务模块】")
    print("-" * 50)
    cursor.execute("""
        SELECT 
            SUBSTR(module, INSTR(module, '.') + 1) as service_module,
            COUNT(*) 
        FROM test_cases 
        WHERE module LIKE 'unit.services.%'
        GROUP BY service_module 
        ORDER BY COUNT(*) DESC
    """)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            module_name = row[0] or "(无)"
            count = row[1]
            print(f"  {module_name}: {count} 个测试")
    else:
        print("  (无 services 层测试)")

    # 5. 按 utils 层分类
    print("\n【utils 层业务模块】")
    print("-" * 50)
    cursor.execute("""
        SELECT 
            SUBSTR(module, INSTR(module, '.') + 1) as utils_module,
            COUNT(*) 
        FROM test_cases 
        WHERE module LIKE 'unit.utils.%'
        GROUP BY utils_module 
        ORDER BY COUNT(*) DESC
    """)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            module_name = row[0] or "(无)"
            count = row[1]
            print(f"  {module_name}: {count} 个测试")
    else:
        print("  (无 utils 层测试)")

    conn.close()
    print("\n" + "=" * 60)
    print("使用说明：")
    print("  python tests/run_tests_by_module.py order       # 运行 Order 模块")
    print("  python tests/run_tests_by_module.py production   # 运行 Production 模块")
    print("  python tests/run_tests_by_module.py process     # 运行 Process 模块")
    print("=" * 60)


def get_module_pattern(module_keyword: str) -> str:
    """根据关键词获取模块匹配模式"""
    # 业务模块映射
    module_map = {
        # models 层
        "order": "unit.models.test_order",
        "production": "unit.models.test_production",
        "process": "unit.models.test_process",
        "shipment": "unit.models.test_shipment",
        "quality": "unit.models.test_quality",
        "inventory": "unit.models.test_inventory",
        "operator": "unit.models.test_operator",
        "material": "unit.models.test_material",
        "bom": "unit.models.test_bom",
        "product": "unit.models.test_product",
        "alert": "unit.models.test_alert",
        "unit": "unit.models.test_unit",
        
        # services 层
        "order_service": "unit.services.test_order_service",
        "process_service": "unit.services.test_process_service",
        "audit_service": "unit.services.test_audit_service",
        "schedule": "unit.services.test_schedule",
        "inventory_service": "unit.services.test_inventory",
        "mysql_storage": "unit.services.test_mysql_storage",
        "wechat": "unit.services.test_wechat",
        "push": "unit.services.test_push",
        
        # utils 层
        "validators": "unit.utils.test_validator",
        "helpers": "unit.utils.test_helper",
        "pagination": "unit.utils.test_pagination",
        "excel": "unit.utils.test_excel",
        "material_calculator": "unit.utils.test_material_calculator",
        "logistics": "unit.utils.test_logistics",
        "i18n": "unit.utils.test_i18n",
        "log": "unit.utils.test_log",
        
        # core 层
        "db": "unit.core.test_db",
        "event": "unit.core.test_event",
        "process_code": "unit.core.test_process_code",
        "error": "unit.core.test_error",
        "circuit": "unit.core.test_circuit",
        "saga": "unit.core.test_saga",
        "push": "unit.core.test_push",
        
        # 层级
        "models": "unit.models",
        "services": "unit.services",
        "utils": "unit.utils",
        "core": "unit.core",
        "unit": "unit.%",
        "integration": "integration",
        "modular": "modular",
        "e2e": "e2e",
    }
    
    keyword = module_keyword.lower()
    return module_map.get(keyword, f"%{keyword}%")


def get_test_paths_by_module(module_pattern: str) -> list:
    """根据模块模式获取测试路径"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 使用 LIKE 匹配
    pattern = f"%{module_pattern}%"
    cursor.execute(
        "SELECT test_path FROM test_cases WHERE module LIKE ?",
        (pattern,)
    )
    
    paths = [row[0] for row in cursor.fetchall()]
    conn.close()
    return paths


def group_paths_by_file(paths: list) -> dict:
    """将测试路径按文件分组"""
    files = {}
    for path in paths:
        # 提取文件路径
        if '::' in path:
            file_path = path.split('::')[0]
        else:
            file_path = path
        files[file_path] = files.get(file_path, 0) + 1
    return files


def run_tests(test_paths: list, label: str) -> dict:
    """运行测试并返回结果"""
    if not test_paths:
        return {"status": "skip", "passed": 0, "failed": 0, "skipped": 0, "error": "无测试用例"}
    
    # 按文件分组
    files = group_paths_by_file(test_paths)
    
    print(f"\n📁 模块: {label}")
    print(f"   测试文件: {len(files)} 个")
    print(f"   测试用例: {len(test_paths)} 个")
    print("-" * 60)
    
    # 构建 pytest 命令
    cmd = [
        sys.executable, '-m', 'pytest',
        *test_paths,
        '-v', '--tb=short',
        '--no-cov',
        '-p', 'no:cacheprovider',
    ]
    
    print(f"运行命令: pytest {' '.join(list(files.keys())[:3])}{' ...' if len(files) > 3 else ''}")
    print()
    
    # 执行测试
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    
    # 解析结果
    output = result.stdout + result.stderr
    
    stats = {"status": "pass" if result.returncode == 0 else "fail"}
    stats["passed"] = output.count(" PASSED")
    stats["failed"] = output.count(" FAILED")
    stats["skipped"] = output.count(" SKIPPED")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="按模块功能运行测试")
    parser.add_argument("module", nargs="?", default="",
                       help="模块名: order/production/process/shipment/quality/inventory等")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有模块")
    
    args = parser.parse_args()
    
    if args.list or not args.module:
        list_modules()
        return
    
    # 获取模块模式
    module_pattern = get_module_pattern(args.module)
    print(f"\n🔍 搜索模块: {args.module}")
    print(f"   匹配模式: {module_pattern}")
    
    # 获取测试路径
    test_paths = get_test_paths_by_module(module_pattern)
    
    if not test_paths:
        print(f"[WARN] 未找到匹配的测试用例")
        print("\n可用模块:")
        list_modules()
        return
    
    # 运行测试
    stats = run_tests(test_paths, args.module)
    
    # 输出结果
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {args.module}")
    print("=" * 60)
    print(f"  通过: {stats['passed']}")
    print(f"  失败: {stats['failed']}")
    print(f"  跳过: {stats['skipped']}")
    print(f"  状态: {'✅ 通过' if stats['status'] == 'pass' else '❌ 失败'}")
    print("=" * 60)


if __name__ == '__main__':
    main()
