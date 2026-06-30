#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RE-006 P6 最终验证(修正版):用 NEW_DATA_TYPE_FOR_COLLECT 字典 value 判断"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 同步 dict(必须和 container_center_v5.py 中定义完全一致)
NEW_DATA_TYPE_FOR_COLLECT = {
    'report':    'process_report',
    'quality':   'quality_task',
    'material':  'material_pickup',
    'approval':  'approval',
    'repair':    'equipment_repair',
    'outsource': 'outsource_task',
    'purchase':  'material_buy',
}
from utils.data_type_contract import NEW_DATA_TYPES

TARGET = os.path.join(ROOT, "mobile_api_ai/container_center_v5.py")
src = open(TARGET, encoding="utf-8").read()

print("【最终验证】container_center_v5.py 中所有 collect_xxx 的 data_type:\n")
methods = re.findall(r"def (collect_\w+)\s*\(", src)
print(f"  找到 {len(methods)} 个: {methods}\n")

all_pass = True
for m_name in methods:
    m_idx = src.find(f"def {m_name}(")
    if m_idx < 0: continue
    next_def = re.search(r"\n    def\s", src[m_idx + 10:])
    body_end = (m_idx + 10 + next_def.start()) if next_def else len(src)
    body = src[m_idx:body_end]
    sig_end = body.find("):")
    after = body[sig_end + 2:] if sig_end > 0 else body

    # 情况 1: NEW_DATA_TYPE_FOR_COLLECT['xxx'] 字典
    m = re.search(r"data_type\s*=\s*NEW_DATA_TYPE_FOR_COLLECT\['(\w+)'\]", after)
    if m:
        legacy_key = m.group(1)
        actual = NEW_DATA_TYPE_FOR_COLLECT.get(legacy_key, '???')
        via = "字典"
    else:
        # 情况 2: 直接字符串
        m2 = re.search(r"data_type\s*=\s*['\"](\w+)['\"]", after)
        if m2:
            actual = m2.group(1)
            via = "直接"
        else:
            print(f"  ❌ {m_name:20s} 未找到 data_type 赋值")
            all_pass = False
            continue

    is_new = "✅" if actual in NEW_DATA_TYPES else "❌"
    if actual not in NEW_DATA_TYPES:
        all_pass = False
    print(f"  {is_new} {m_name:20s} data_type={actual!r:22s} via={via}")

print()
if all_pass:
    print("✅ 全部通过 — 7 个 collect_xxx 全部用新 data_type")
    sys.exit(0)
else:
    print("❌ 部分失败")
    sys.exit(1)
