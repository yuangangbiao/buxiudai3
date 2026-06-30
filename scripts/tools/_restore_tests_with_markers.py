# -*- coding: utf-8 -*-
"""
将 11 个有 def test_* 的验收脚本移回 tests/ 目录

策略:
- integration (连真实 DB/HTTP) → tests/integration/业务域/
- manual (独立验收/playwright) → tests/manual/业务域/

同时确保文件头有正确的 import pytest + pytestmark
"""
import os
import shutil

PROJECT_ROOT = r"d:\yuan\不锈钢网带跟单3.0"
MANUAL_DIR = os.path.join(PROJECT_ROOT, "scripts", "manual_acceptance")
TESTS_ROOT = os.path.join(PROJECT_ROOT, "tests")

INTEGRATION_TESTS = [
    {
        "src": "_moved_test_data_source_direct_0620.py",
        "dst_dir": "tests/integration/data_source",
        "dst_name": "test_data_source_direct.py",
        "marker": "integration",
        "comment": "数据来源验证 - 直接连 DB",
    },
    {
        "src": "_moved_test_consistency_xiaosheng.py",
        "dst_dir": "tests/integration/consistency",
        "dst_name": "test_consistency_xiaosheng.py",
        "marker": "integration",
        "comment": "数据一致性测试",
    },
    {
        "src": "_moved_test_independent_tables_sync_0620.py",
        "dst_dir": "tests/integration/sync",
        "dst_name": "test_independent_tables_sync.py",
        "marker": "integration",
        "comment": "独立表同步测试",
    },
    {
        "src": "_moved_test_main_software_sync_0620.py",
        "dst_dir": "tests/integration/sync",
        "dst_name": "test_main_software_sync.py",
        "marker": "integration",
        "comment": "主软件数据同步测试",
    },
    {
        "src": "_moved_test_mobile_desktop_sync_0620.py",
        "dst_dir": "tests/integration/sync",
        "dst_name": "test_mobile_desktop_sync.py",
        "marker": "integration",
        "comment": "移动端-桌面端同步测试",
    },
    {
        "src": "_moved_test_security_xiaoyu.py",
        "dst_dir": "tests/integration/security",
        "dst_name": "test_security_xiaoyu.py",
        "marker": "integration",
        "comment": "安全测试",
    },
]

MANUAL_TESTS = [
    {
        "src": "_moved_test_5008_b3_b4_fixed.py",
        "dst_dir": "tests/manual/http",
        "dst_name": "test_5008_b3_b4.py",
        "marker": "manual",
        "comment": "5008 B3/B4 修复验收",
    },
    {
        "src": "_moved_test_8008_5008_full.py",
        "dst_dir": "tests/manual/http",
        "dst_name": "test_8008_5008_full.py",
        "marker": "manual",
        "comment": "8008+5008+5003+5001 端到端",
    },
    {
        "src": "_moved_test_full_ux.py",
        "dst_dir": "tests/manual/playwright",
        "dst_name": "test_full_ux_xiaoxi.py",
        "marker": "manual",
        "comment": "UX 测试",
    },
    {
        "src": "_moved_test_regression_api_0620.py",
        "dst_dir": "tests/manual/http",
        "dst_name": "test_regression_api.py",
        "marker": "manual",
        "comment": "回归审计 API 测试",
    },
    {
        "src": "_moved_test_ux_xiaoxi.py",
        "dst_dir": "tests/manual/playwright",
        "dst_name": "test_ux_xiaoxi.py",
        "marker": "manual",
        "comment": "UX 测试",
    },
]

MARKER_TEMPLATE_INTEGRATION = '''# -*- coding: utf-8 -*-
"""%(comment)s"""
import pytest

pytestmark = pytest.mark.integration
'''

MARKER_TEMPLATE_MANUAL = '''# -*- coding: utf-8 -*-
"""%(comment)s"""
import pytest

pytestmark = pytest.mark.manual
'''


def ensure_pytestmark(filepath, marker_type, comment):
    """确保文件头有正确的 pytestmark，不重复添加"""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if "pytestmark = pytest.mark." in content:
        return False  # 已有 marker，无需修改

    # 找到文件头的位置（跳过 # -*- coding: 行）
    lines = content.split("\n")
    marker_text = (MARKER_TEMPLATE_INTEGRATION if marker_type == "integration"
                   else MARKER_TEMPLATE_MANUAL) % {"comment": comment}

    # 在 # -*- coding: 行之后插入 marker
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith("# -*-"):
            insert_pos = i + 1
            break
        elif line.strip() == "":
            insert_pos = i
            break
        elif line.startswith("#!"):
            insert_pos = i + 1
            break
        else:
            insert_pos = i + 1

    new_lines = lines[:insert_pos] + marker_text.split("\n") + [""] + lines[insert_pos:]
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))
    return True


def move_test(test_info):
    """移动单个测试文件到目标目录"""
    src = os.path.join(MANUAL_DIR, test_info["src"])
    dst_dir = os.path.join(PROJECT_ROOT, test_info["dst_dir"])
    dst_name = test_info["dst_name"]
    dst = os.path.join(dst_dir, dst_name)
    marker = test_info["marker"]
    comment = test_info["comment"]

    if not os.path.exists(src):
        return "SKIP_NOT_EXISTS", 0

    # 确保目标目录存在
    os.makedirs(dst_dir, exist_ok=True)

    # 移动文件
    shutil.copy2(src, dst)
    os.remove(src)

    # 确保有 pytestmark
    modified = ensure_pytestmark(dst, marker, comment)

    return ("OK_MODIFIED" if modified else "OK_UNCHANGED"), os.path.getsize(dst)


def main():
    print("=" * 70)
    print("将 11 个验收脚本移回 tests/ 目录")
    print("=" * 70)

    results = []
    for test_info in INTEGRATION_TESTS + MANUAL_TESTS:
        status, size = move_test(test_info)
        marker = test_info["marker"]
        print(f"  {status:15s} [{marker:11s}] {test_info['src']} → {test_info['dst_dir']}/{test_info['dst_name']}")
        results.append((test_info, status, size))

    print("\n" + "=" * 70)
    print("汇总")
    print("=" * 70)
    integration_count = len([r for r in results if r[0]["marker"] == "integration"])
    manual_count = len([r for r in results if r[0]["marker"] == "manual"])
    ok_count = len([r for r in results if r[1].startswith("OK")])
    skip_count = len([r for r in results if r[1] == "SKIP_NOT_EXISTS"])
    print(f"  integration: {integration_count} 个")
    print(f"  manual:      {manual_count} 个")
    print(f"  成功:        {ok_count} 个")
    print(f"  跳过:        {skip_count} 个")
    print()
    print("✅ 完成！")


if __name__ == "__main__":
    main()
