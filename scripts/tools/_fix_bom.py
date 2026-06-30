"""
批量去除 24 个测试文件的 UTF-8 BOM (U+FEFF)
修复后 pytest 才能正确解析。
"""
import os
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
BOM = b'\xef\xbb\xbf'

# 需要修复的文件清单（从扫描报告提取）
TARGETS = [
    r"tests\unit\core\test_db_complete.py",
    r"tests\unit\models\test_base_dao_complete.py",
    r"tests\unit\models\test_inventory_complete.py",
    r"tests\unit\models\test_inventory_dao_complete.py",
    r"tests\unit\models\test_order_complete.py",
    r"tests\unit\models\test_process_complete.py",
    r"tests\unit\models\test_production_complete.py",
    r"tests\unit\models\test_product_type_complete.py",
    r"tests\unit\models\test_quality_complete.py",
    r"tests\unit\models\test_shipment_complete.py",
    r"tests\unit\services\test_audit_service_complete.py",
    r"tests\unit\services\test_order_service_complete.py",
    r"tests\unit\services\test_process_service_complete.py",
    r"tests\unit\utils\test_excel_utils_complete.py",
    r"tests\unit\utils\test_helpers_complete.py",
    r"tests\unit\utils\test_logistics_companies_complete.py",
    r"tests\unit\utils\test_material_calculator_complete.py",
    r"tests\unit\utils\test_pagination_complete.py",
    r"tests\unit\utils\test_query_cache_complete.py",
    r"tests\unit\utils\test_settings_manager_complete.py",
    r"tests\unit\utils\test_validators_complete.py",
    r"mobile_api_ai\tests\fixtures\__init__.py",
    r"mobile_api_ai\tests\integration\__init__.py",
    r"mobile_api_ai\tests\unit\__init__.py",
]

fixed = []
skipped = []
errors = []

print(f"准备修复 {len(TARGETS)} 个文件")
print("=" * 70)

for rel in TARGETS:
    full = ROOT / rel
    if not full.exists():
        errors.append((rel, "文件不存在"))
        continue
    try:
        data = full.read_bytes()
    except Exception as e:
        errors.append((rel, f"读取失败: {e}"))
        continue

    if data[:3] == BOM:
        new_data = data[3:]
        try:
            # 备份原文件到 .bak_bom 保险
            bak_path = full.with_suffix(full.suffix + ".bak_bom")
            bak_path.write_bytes(data)
            full.write_bytes(new_data)
            fixed.append((rel, len(data), len(new_data)))
        except Exception as e:
            errors.append((rel, f"写入失败: {e}"))
    else:
        skipped.append((rel, "无 BOM"))

print("\n修复结果:")
print(f"  ✅ 已修复: {len(fixed)}")
for rel, old, new in fixed:
    print(f"    {rel} ({old} → {new} bytes)")

print(f"\n  ⏭️  跳过(无 BOM): {len(skipped)}")
for rel, reason in skipped:
    print(f"    {rel}: {reason}")

if errors:
    print(f"\n  ❌ 错误: {len(errors)}")
    for rel, e in errors:
        print(f"    {rel}: {e}")

print("\n" + "=" * 70)
print(f"备份文件位置: {ROOT}\\*\\*.bak_bom (如需回滚可恢复)")