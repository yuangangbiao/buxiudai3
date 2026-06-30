"""
批量给 scripts/ 下独立验收脚本加标记
- 直接连 DB 的 → @pytest.mark.integration
- 纯 HTTP/Playwright/集成验收 → @pytest.mark.manual
"""
import os
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0\scripts")

DB_FILES = {
    r"test_functional_xiaoh.py": "integration",          # get_connection()
    r"test_security_xiaoyu.py": "integration",          # pymysql.connect()
    r"test_main_software_sync_0620.py": "integration",  # get_connection()
    r"test_mobile_desktop_sync_0620.py": "integration",# get_connection()
    r"test_data_source_direct_0620.py": "integration", # get_connection()
    r"test_independent_tables_sync_0620.py": "integration",  # MySQLStorage()
    r"test_consistency_xiaosheng.py": "integration",   # pymysql.connect()
    r"tools\test_enterprise_merge.py": "integration",   # get_connection()
    r"tools\test_publish_flow.py": "integration",     # 调用 OrderDAO/ProductionDAO
    r"tools\test_fresh_publish.py": "integration",     # get_connection()
}
MANUAL_FILES = {
    r"test_5008_b3_b4_fixed.py": "manual",   # HTTP 验收脚本
    r"test_8008_5008_full.py": "manual",    # HTTP 集成验收
    r"test_ux_xiaoxi.py": "manual",         # Playwright 脚本
    r"test_full_ux.py": "manual",           # Playwright 脚本
    r"test_regression_api_0620.py": "manual",  # HTTP 验收脚本
}

ALL = {**DB_FILES, **MANUAL_FILES}

added = []
skipped = []
errors = []

for rel, marker_type in ALL.items():
    full = ROOT / rel
    if not full.exists():
        errors.append((rel, f"不存在"))
        continue
    text = full.read_text(encoding='utf-8', errors='ignore')

    if "pytestmark" in text and f"pytest.mark.{marker_type}" in text:
        skipped.append((rel, marker_type))
        continue

    lines = text.split('\n')
    if marker_type == "integration":
        marker = "import pytest\n\npytestmark = pytest.mark.integration  # 直接连 DB，需手动跑\n\n"
    else:
        marker = "import pytest\n\npytestmark = pytest.mark.manual  # 独立验收/Playwright 脚本，不参与 pytest 单元统计\n\n"

    insert_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
            insert_idx = i
            break

    new_lines = lines[:insert_idx] + [marker] + lines[insert_idx:]
    new_text = '\n'.join(new_lines)

    try:
        full.write_text(new_text, encoding='utf-8')
        added.append((rel, marker_type))
    except Exception as e:
        errors.append((rel, str(e)))

print("=" * 70)
print(f"✅ 已添加标记: {len(added)}")
for f, t in added:
    print(f"  [{t}] {f}")

print(f"\n⏭️  已跳过(已有): {len(skipped)}")
for f, t in skipped:
    print(f"  [{t}] {f}")

if errors:
    print(f"\n❌ 错误: {len(errors)}")
    for f, e in errors:
        print(f"  {f}: {e}")

print("=" * 70)