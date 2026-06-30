# -*- coding: utf-8 -*-
"""
死测试文件清理脚本 v2 - 分类处理剩余 36 个文件

A1: 删除 2 个真正死测试 (无 def test_* + 无实际用途)
A2: 移动 5 个工具/调试脚本到 scripts/tools/
A3: 移动 24 个散落 scripts/test_*.py 到 scripts/manual_acceptance/
"""
import os
import shutil
import re

PROJECT_ROOT = r"d:\yuan\不锈钢网带跟单3.0"

SCRIPTS_TOOLS = os.path.join(PROJECT_ROOT, "scripts", "tools")
SCRIPTS_MANUAL = os.path.join(PROJECT_ROOT, "scripts", "manual_acceptance")

os.makedirs(SCRIPTS_TOOLS, exist_ok=True)
os.makedirs(SCRIPTS_MANUAL, exist_ok=True)

A1_DELETE = [
    "tests/_analyze_imports.py",
    "tests/generate_report.py",
]

A2_MOVE_TOOLS = [
    "tests/unit/models/_run_native_coverage.py",
    "tests/unit/models/_run_operator_full_cov.py",
    "tests/unit/utils/_debug_fixture.py",
    "mobile_api_ai/tests/unit/_syspath_runner.py",
    "mobile_api_ai/tests/unit/e2e_get_packages_process_report.py",
    "mobile_api_ai/tests/unit/http_client.py",
]

A3_MOVE_MANUAL = [
    "scripts/test_5003.py",
    "scripts/test_5008_b3_b4_fixed.py",
    "scripts/test_8008_5008_full.py",
    "scripts/test_consistency_xiaosheng.py",
    "scripts/test_data_source_direct_0620.py",
    "scripts/test_finished_goods.py",
    "scripts/test_full_ux.py",
    "scripts/test_functional_xiaoh.py",
    "scripts/test_independent_tables_sync_0620.py",
    "scripts/test_login.py",
    "scripts/test_main_software_sync_0620.py",
    "scripts/test_metrics_integration.py",
    "scripts/test_mobile_desktop_sync_0620.py",
    "scripts/test_order_detail.py",
    "scripts/test_orders_list.py",
    "scripts/test_process_api.py",
    "scripts/test_process_detail.py",
    "scripts/test_production_list.py",
    "scripts/test_regression_api_0620.py",
    "scripts/test_schedule_list.py",
    "scripts/test_security_xiaoyu.py",
    "scripts/test_shipment_api.py",
    "scripts/test_shipment_full.py",
    "scripts/test_ux_xiaoxi.py",
]


def human_size(n):
    for unit in ("B", "KB", "MB"):
        if n < 1024.0:
            return f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} GB"


def get_size(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def safe_move(src, dst_dir, rename_prefix="_moved_"):
    """移动文件到目标目录，自动重命名避免冲突"""
    os.makedirs(dst_dir, exist_ok=True)
    fname = os.path.basename(src)
    dst_name = rename_prefix + fname
    dst = os.path.join(dst_dir, dst_name)
    counter = 1
    while os.path.exists(dst):
        dst_name = f"{rename_prefix}{os.path.splitext(fname)[0]}_{counter}{os.path.splitext(fname)[1]}"
        dst = os.path.join(dst_dir, dst_name)
        counter += 1
    size = os.path.getsize(src)
    shutil.move(src, dst)
    return dst, dst_name, size


def safe_delete(path):
    """安全删除文件"""
    size = os.path.getsize(path)
    os.remove(path)
    return size


def main():
    results = {"delete": [], "move_tools": [], "move_manual": [], "skip": []}

    # A1: 删除 2 个真正死测试
    print("\n" + "=" * 70)
    print("【A1】删除 2 个真正死测试")
    print("=" * 70)
    for rel in A1_DELETE:
        path = os.path.join(PROJECT_ROOT, rel)
        if not os.path.exists(path):
            print(f"  ⊘ 跳过 (不存在): {rel}")
            results["skip"].append(rel)
            continue
        try:
            size = safe_delete(path)
            print(f"  ✓ 删除: {rel} ({human_size(size)})")
            results["delete"].append((rel, size))
        except Exception as e:
            print(f"  ✗ 失败: {rel} - {e}")

    # A2: 移动 5 个工具/调试脚本
    print("\n" + "=" * 70)
    print("【A2】移动 6 个工具/调试脚本到 scripts/tools/")
    print("=" * 70)
    for rel in A2_MOVE_TOOLS:
        path = os.path.join(PROJECT_ROOT, rel)
        if not os.path.exists(path):
            print(f"  ⊘ 跳过 (不存在): {rel}")
            results["skip"].append(rel)
            continue
        try:
            dst, dst_name, size = safe_move(path, SCRIPTS_TOOLS, rename_prefix="_moved_")
            print(f"  ✓ 移动: {rel} → scripts/tools/{dst_name} ({human_size(size)})")
            results["move_tools"].append((rel, dst_name, size))
        except Exception as e:
            print(f"  ✗ 失败: {rel} - {e}")

    # A3: 移动 24 个散落验收脚本
    print("\n" + "=" * 70)
    print("【A3】移动 24 个散落 scripts/test_*.py 到 scripts/manual_acceptance/")
    print("=" * 70)
    for rel in A3_MOVE_MANUAL:
        path = os.path.join(PROJECT_ROOT, rel)
        if not os.path.exists(path):
            print(f"  ⊘ 跳过 (不存在): {rel}")
            results["skip"].append(rel)
            continue
        try:
            dst, dst_name, size = safe_move(path, SCRIPTS_MANUAL, rename_prefix="_moved_")
            print(f"  ✓ 移动: {rel} → scripts/manual_acceptance/{dst_name} ({human_size(size)})")
            results["move_manual"].append((rel, dst_name, size))
        except Exception as e:
            print(f"  ✗ 失败: {rel} - {e}")

    # 汇总
    print("\n" + "=" * 70)
    print("【清理汇总 v2】")
    print("=" * 70)

    total_del = sum(x[1] for x in results["delete"])
    total_tool = sum(x[2] for x in results["move_tools"])
    total_man = sum(x[2] for x in results["move_manual"])
    total_files = len(results["delete"]) + len(results["move_tools"]) + len(results["move_manual"])
    total_size = total_del + total_tool + total_man

    print(f"  A1 删除:   {len(results['delete'])} 文件,  {human_size(total_del)}")
    print(f"  A2 工具:   {len(results['move_tools'])} 文件,  {human_size(total_tool)}")
    print(f"  A3 验收:   {len(results['move_manual'])} 文件,  {human_size(total_man)}")
    print(f"  跳过:      {len(results['skip'])} 文件")
    print(f"  ─────────────────────────────────────────")
    print(f"  总计:      {total_files} 文件,  {human_size(total_size)}")
    print()
    print("✅ 清理完成！")


if __name__ == "__main__":
    main()
