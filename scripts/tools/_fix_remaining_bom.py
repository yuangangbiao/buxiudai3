"""
补充修复 3 个非测试文件的 BOM
"""
import os
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
BOM = b'\xef\xbb\xbf'

TARGETS = [
    r"mobile_api_ai\cloud_matching.py",
    r"mobile_api_ai\temp_check.py",
    r"mobile_api_ai\scripts\tools\add_index_wo_no.py",
]

for rel in TARGETS:
    full = ROOT / rel
    if not full.exists():
        print(f"  ⚠️ 不存在: {rel}")
        continue
    data = full.read_bytes()
    if data[:3] == BOM:
        bak_path = full.with_suffix(full.suffix + ".bak_bom")
        bak_path.write_bytes(data)
        full.write_bytes(data[3:])
        print(f"  ✅ 修复: {rel} ({len(data)} → {len(data)-3} bytes, 备份 → {bak_path.name})")
    else:
        print(f"  ⏭️ 无 BOM: {rel}")