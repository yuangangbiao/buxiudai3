# -*- coding: utf-8 -*-
"""检查 manual_acceptance 目录中 11 个有 test_* 函数的文件"""
import os

PROJECT_ROOT = r"d:\yuan\不锈钢网带跟单3.0"
MANUAL_DIR = os.path.join(PROJECT_ROOT, "scripts", "manual_acceptance")

HAS_TEST_FILES = [
    "_moved_test_5008_b3_b4_fixed.py",
    "_moved_test_8008_5008_full.py",
    "_moved_test_consistency_xiaosheng.py",
    "_moved_test_data_source_direct_0620.py",
    "_moved_test_finished_goods.py",
    "_moved_test_full_ux.py",
    "_moved_test_functional_xiaoh.py",
    "_moved_test_independent_tables_sync_0620.py",
    "_moved_test_login.py",
    "_moved_test_main_software_sync_0620.py",
    "_moved_test_metrics_integration.py",
    "_moved_test_mobile_desktop_sync_0620.py",
    "_moved_test_order_detail.py",
    "_moved_test_orders_list.py",
    "_moved_test_process_api.py",
    "_moved_test_process_detail.py",
    "_moved_test_production_list.py",
    "_moved_test_regression_api_0620.py",
    "_moved_test_schedule_list.py",
    "_moved_test_security_xiaoyu.py",
    "_moved_test_shipment_api.py",
    "_moved_test_shipment_full.py",
    "_moved_test_ux_xiaoxi.py",
    "_moved_test_5003.py",
]


def get_test_functions(filepath):
    """提取所有 def test_* 函数名"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return []
    lines = content.split("\n")
    funcs = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("def test_") or stripped.startswith("async def test_"):
            funcs.append(stripped.split("(")[0].replace("async def ", ""))
    return funcs


def has_marker(filepath, marker):
    """检查是否有指定 marker"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return marker in content
    except Exception:
        return False


def check_file(filepath):
    info = {
        "path": filepath,
        "size": 0,
        "test_funcs": [],
        "has_integration": False,
        "has_manual": False,
        "has_e2e": False,
        "has_unit": False,
        "has_pytestmark": False,
        "imports": [],
    }
    try:
        info["size"] = os.path.getsize(filepath)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        info["test_funcs"] = get_test_functions(filepath)
        info["has_integration"] = has_marker(filepath, "@pytest.mark.integration")
        info["has_manual"] = has_marker(filepath, "@pytest.mark.manual")
        info["has_e2e"] = has_marker(filepath, "@pytest.mark.e2e")
        info["has_unit"] = has_marker(filepath, "@pytest.mark.unit")
        info["has_pytestmark"] = "pytestmark" in content
        # 简单检查导入
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                if "pytest" not in stripped and "unittest" not in stripped:
                    info["imports"].append(stripped[:60])
    except Exception as e:
        info["error"] = str(e)
    return info


def main():
    print("=" * 80)
    print("manual_acceptance 目录文件分析")
    print("=" * 80)

    has_test_files = []
    no_test_files = []

    for fname in sorted(os.listdir(MANUAL_DIR)):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(MANUAL_DIR, fname)
        rel = os.path.relpath(fpath, PROJECT_ROOT).replace("\\", "/")
        info = check_file(fpath)
        info["name"] = fname

        if info["test_funcs"]:
            has_test_files.append(info)
        else:
            no_test_files.append(info)

    print(f"\n【有 def test_* 的文件】({len(has_test_files)} 个)")
    print("-" * 80)
    for info in sorted(has_test_files, key=lambda x: x["name"]):
        markers = []
        if info["has_integration"]:
            markers.append("integration")
        if info["has_manual"]:
            markers.append("manual")
        if info["has_e2e"]:
            markers.append("e2e")
        if info["has_unit"]:
            markers.append("unit")
        marker_str = ", ".join(markers) if markers else "无marker"
        print(f"\n  {info['name']} ({info['size']//1024} KB)")
        print(f"    Marker: {marker_str}")
        print(f"    test函数: {', '.join(info['test_funcs'])}")
        # 只显示前3个非pytest导入
        imports = [i for i in info["imports"] if not i.startswith("from unittest")]
        if imports:
            print(f"    导入: {', '.join(imports[:3])}")

    print(f"\n【无 def test_* 的文件】({len(no_test_files)} 个)")
    print("-" * 80)
    for info in sorted(no_test_files, key=lambda x: x["name"]):
        print(f"  {info['name']} ({info['size']//1024} KB)")

    print(f"\n汇总: 有test {len(has_test_files)} 个, 无test {len(no_test_files)} 个")
    print(f"有test中已有marker: {sum(1 for i in has_test_files if i['has_integration'] or i['has_manual'] or i['has_e2e'] or i['has_unit'])} 个")


if __name__ == "__main__":
    main()
