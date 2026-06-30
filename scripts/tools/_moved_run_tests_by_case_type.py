# -*- coding: utf-8 -*-
"""
按功能分类运行测试脚本

功能：
- 按 case_type（单元/边界/并发/集成）运行测试
- 按 boundary_cat（空/单条/阈值/参数化）运行测试
- 支持按 module 目录运行测试
- 结果写入数据库

用法：
    python tests/run_tests_by_case_type.py list                      # 列出所有分类
    python tests/run_tests_by_case_type.py case-type 单元           # 运行单元测试
    python tests/run_tests_by_case_type.py case-type 边界          # 运行边界测试
    python tests/run_tests_by_case_type.py boundary 空              # 运行空值边界测试
    python tests/run_tests_by_case_type.py module models            # 运行 models 模块测试
    python tests/run_tests_by_case_type.py all                      # 运行所有测试
"""
import os
import sys
import sqlite3
import subprocess
import json
import argparse
from pathlib import Path
from datetime import datetime

# 项目根目录
ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / '.workbuddy' / 'regression' / 'regression.db'
CACHE_PATH = ROOT / '.workbuddy' / '.test_case_type_cache.json'


def get_db_connection():
    """获取数据库连接"""
    if not DB_PATH.exists():
        print(f"[FAIL] 数据库不存在: {DB_PATH}")
        print("请先运行: python .workbuddy/tools/regression_db.py import-tests")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def list_categories():
    """列出所有分类统计"""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n" + "=" * 50)
    print("测试用例分类统计")
    print("=" * 50)

    # case_type 分布
    print("\n【case_type 功能类型】")
    print("-" * 40)
    cursor.execute("SELECT case_type, COUNT(*) FROM test_cases GROUP BY case_type ORDER BY COUNT(*) DESC")
    total = 0
    for row in cursor.fetchall():
        case_type = row[0] or "(未分类)"
        count = row[1]
        total += count
        print(f"  {case_type}: {count} 个")
    print(f"  {'总计'}: {total} 个")

    # boundary_cat 分布
    print("\n【boundary_cat 边界分类】")
    print("-" * 40)
    cursor.execute("SELECT boundary_cat, COUNT(*) FROM test_cases GROUP BY boundary_cat ORDER BY COUNT(*) DESC")
    for row in cursor.fetchall():
        boundary = row[0] or "(无)"
        count = row[1]
        print(f"  {boundary}: {count} 个")

    # module 分布
    print("\n【module 模块分布】")
    print("-" * 40)
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
        print(f"  {layer}: {count} 个")

    conn.close()
    print("\n" + "=" * 50)


def get_test_paths_by_case_type(case_type: str) -> list:
    """根据 case_type 获取测试路径"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if case_type == "所有":
        cursor.execute("SELECT test_path FROM test_cases")
    else:
        cursor.execute(
            "SELECT test_path FROM test_cases WHERE case_type = ?",
            (case_type,)
        )
    
    paths = [row[0] for row in cursor.fetchall()]
    conn.close()
    return paths


def get_test_paths_by_boundary(boundary_cat: str) -> list:
    """根据 boundary_cat 获取测试路径"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if boundary_cat == "所有":
        cursor.execute("SELECT test_path FROM test_cases")
    else:
        cursor.execute(
            "SELECT test_path FROM test_cases WHERE boundary_cat = ?",
            (boundary_cat,)
        )
    
    paths = [row[0] for row in cursor.fetchall()]
    conn.close()
    return paths


def get_test_paths_by_module(module_keyword: str) -> list:
    """根据 module 关键词获取测试路径"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 映射常见模块名
    module_map = {
        "models": "unit.models",
        "model": "unit.models",
        "services": "unit.services",
        "service": "unit.services",
        "utils": "unit.utils",
        "util": "unit.utils",
        "core": "unit.core",
    }
    
    keyword = module_map.get(module_keyword.lower(), module_keyword.lower())
    
    cursor.execute(
        "SELECT test_path FROM test_cases WHERE module LIKE ?",
        (f"%{keyword}%",)
    )
    
    paths = [row[0] for row in cursor.fetchall()]
    conn.close()
    return paths


def group_paths_by_file(paths: list) -> dict:
    """将测试路径按文件分组"""
    files = {}
    for path in paths:
        # 提取文件路径（去掉 ::TestClass::test_name 部分）
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
    
    print(f"\n📁 共 {len(files)} 个测试文件, {len(test_paths)} 个测试用例")
    print("-" * 50)
    
    # 构建 pytest 命令
    cmd = [
        sys.executable, '-m', 'pytest',
        *test_paths,
        '-v', '--tb=short',
        '--no-cov',  # 禁用覆盖率（加速）
        '-p', 'no:cacheprovider',
    ]
    
    print(f"运行: {label}")
    print(f"命令: pytest {' '.join(test_paths[:3])}{' ...' if len(test_paths) > 3 else ''}")
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
    
    # 提取统计信息
    stats = {"status": "pass" if result.returncode == 0 else "fail"}
    stats["passed"] = output.count(" PASSED")
    stats["failed"] = output.count(" FAILED")
    stats["skipped"] = output.count(" SKIPPED")
    stats["error"] = 0  # pytest 不单独统计 error
    
    return stats


def update_test_status(test_paths: list, status: str):
    """更新数据库中的测试状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    for path in test_paths:
        if '::' in path:
            file_path = path.split('::')[0]
            if '[' in path:
                # parametrize: tests/x.py::Class::test[a-b]
                idx = path.index('[')
                params = path[idx+1:-1]
                base_path = path[:idx]
                cursor.execute(
                    "UPDATE test_cases SET last_run_at = ?, last_status = ? WHERE test_path = ? AND params = ?",
                    (now, status, base_path, params)
                )
            else:
                # 普通: tests/x.py::Class::test
                cursor.execute(
                    "UPDATE test_cases SET last_run_at = ?, last_status = ? WHERE test_path = ? AND params = ''",
                    (now, status, path)
                )
    
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="按功能分类运行测试")
    parser.add_argument("action", nargs="?", default="list",
                       help="操作: list/case-type/boundary/module/all")
    parser.add_argument("filter", nargs="?", default="",
                       help="过滤条件")
    
    args = parser.parse_args()
    
    if args.action == "list":
        list_categories()
        return
    
    if args.action == "case-type":
        if not args.filter:
            print("[FAIL] 请指定 case_type (单元/边界/并发/集成)")
            list_categories()
            return
        
        # 映射中文到英文
        case_type_map = {
            "单元": "单元",
            "边界": "边界",
            "并发": "并发",
            "集成": "集成",
            "所有": "所有",
        }
        case_type = case_type_map.get(args.filter, args.filter)
        
        print(f"\n🔍 按 case_type='{case_type}' 筛选测试")
        test_paths = get_test_paths_by_case_type(case_type)
        stats = run_tests(test_paths, f"case_type={case_type}")
        
        print(f"\n📊 结果: 通过={stats['passed']}, 失败={stats['failed']}, 跳过={stats['skipped']}")
        
        if stats["status"] == "pass":
            update_test_status(test_paths, "pass")
        else:
            update_test_status(test_paths, "fail")
        
        return
    
    if args.action == "boundary":
        if not args.filter:
            print("[FAIL] 请指定 boundary_cat (空/单条/阈值/参数化)")
            list_categories()
            return
        
        print(f"\n🔍 按 boundary_cat='{args.filter}' 筛选测试")
        test_paths = get_test_paths_by_boundary(args.filter)
        stats = run_tests(test_paths, f"boundary_cat={args.filter}")
        
        print(f"\n📊 结果: 通过={stats['passed']}, 失败={stats['failed']}, 跳过={stats['skipped']}")
        return
    
    if args.action == "module":
        if not args.filter:
            print("[FAIL] 请指定 module (models/services/utils/core)")
            list_categories()
            return
        
        print(f"\n🔍 按 module='{args.filter}' 筛选测试")
        test_paths = get_test_paths_by_module(args.filter)
        stats = run_tests(test_paths, f"module={args.filter}")
        
        print(f"\n📊 结果: 通过={stats['passed']}, 失败={stats['failed']}, 跳过={stats['skipped']}")
        return
    
    if args.action == "all":
        print("\n🔍 运行所有测试")
        test_paths = get_test_paths_by_case_type("所有")
        stats = run_tests(test_paths, "全部测试")
        
        print(f"\n📊 结果: 通过={stats['passed']}, 失败={stats['failed']}, 跳过={stats['skipped']}")
        return
    
    # 默认显示帮助
    print("\n用法:")
    print("  python tests/run_tests_by_case_type.py list                    # 列出分类统计")
    print("  python tests/run_tests_by_case_type.py case-type 单元         # 运行单元测试")
    print("  python tests/run_tests_by_case_type.py case-type 边界         # 运行边界测试")
    print("  python tests/run_tests_by_case_type.py boundary 参数化         # 运行参数化测试")
    print("  python tests/run_tests_by_case_type.py module models           # 运行 models 模块")
    print("  python tests/run_tests_by_case_type.py all                   # 运行所有测试")


if __name__ == '__main__':
    main()
