"""
删除 9 个 .hash 文件（50B hash 摘要，无源码价值）
"""
import os
from pathlib import Path

ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")

HASH_FILES = [
    r"mobile_api_ai\container_center_api.py.hash",
    r"mobile_api_ai\dispatch_center.py.hash",  # 孤儿（源已删）
    r"mobile_api_ai\standalone_dispatch_server.py.hash",
    r"mobile_api_ai\api\quality_inspection.py.hash",
    r"mobile_api_ai\storage\mysql_storage.py.hash",
    r"models\quality.py.hash",
    r"models\quality_rule.py.hash",
    r"services\schedule_dispatch_service.py.hash",
    r"services\wechat_report_service.py.hash",
]

removed = []
errors = []

for rel in HASH_FILES:
    full = ROOT / rel
    if not full.exists():
        errors.append((rel, "不存在"))
        continue
    try:
        size = full.stat().st_size
        os.remove(full)
        removed.append((rel, size))
    except Exception as e:
        errors.append((rel, str(e)))

print("=" * 70)
print(f"✅ 已删除 .hash 文件: {len(removed)} 个")
total_bytes = 0
for rel, sz in removed:
    print(f"  {rel} ({sz}B)")
    total_bytes += sz
print(f"\n  释放空间: {total_bytes} 字节 ({total_bytes/1024:.1f} KB)")

if errors:
    print(f"\n❌ 错误: {len(errors)}")
    for rel, e in errors:
        print(f"  {rel}: {e}")

print("=" * 70)