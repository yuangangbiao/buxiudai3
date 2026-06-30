#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RE-006 P6 最终修复:强制 5 处 data_type 改为新值"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

TARGET = os.path.join(ROOT, "mobile_api_ai/container_center_v5.py")
src = open(TARGET, encoding="utf-8").read()
orig = src

# 每个方法的"def 起始" → "下一个 def 之前",块内替换 data_type
methods = [
    ("collect_report",    "data_type='report'",     "data_type=NEW_DATA_TYPE_FOR_COLLECT['report']"),
    ("collect_quality",   "data_type='quality'",    "data_type=NEW_DATA_TYPE_FOR_COLLECT['quality']"),
    ("collect_material",  "data_type='material'",   "data_type=NEW_DATA_TYPE_FOR_COLLECT['material']"),
    ("collect_approval",  "data_type='approval'",   "data_type=NEW_DATA_TYPE_FOR_COLLECT['approval']"),
    ("collect_repair",    "data_type='repair'",     "data_type=NEW_DATA_TYPE_FOR_COLLECT['repair']"),
    ("collect_outsource", "data_type='outsource'",  "data_type=NEW_DATA_TYPE_FOR_COLLECT['outsource']"),
]

fixed = 0
for m_name, old, new in methods:
    m_idx = src.find(f"def {m_name}(")
    if m_idx < 0:
        print(f"  [SKIP] {m_name} 未找到")
        continue
    next_def = re.search(r"\n    def\s", src[m_idx + 10:])
    body_end = (m_idx + 10 + next_def.start()) if next_def else len(src)
    body = src[m_idx:body_end]
    if old in body:
        new_body = body.replace(old, new, 1)
        src = src.replace(body, new_body, 1)
        print(f"  [OK] {m_name}: {old} → {new}")
        fixed += 1
    else:
        print(f"  [DONE] {m_name}: 已修复或不需要")

if src == orig:
    print("\n[INFO] 无需修改")
    sys.exit(0)

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)
print(f"\n✅ 写回 {TARGET} (修复 {fixed} 处)")

# 验证
from utils.data_type_contract import NEW_DATA_TYPES
print("\n【验证】")
for m_name in [m[0] for m in methods]:
    m_idx = src.find(f"def {m_name}(")
    if m_idx < 0: continue
    next_def = re.search(r"\n    def\s", src[m_idx + 10:])
    body_end = (m_idx + 10 + next_def.start()) if next_def else len(src)
    body = src[m_idx:body_end]
    sig_end = body.find("):")
    after = body[sig_end + 2:] if sig_end > 0 else body
    m = re.search(r"data_type\s*=\s*NEW_DATA_TYPE_FOR_COLLECT\['(\w+)'\]", after)
    if m:
        actual = m.group(1)
        is_new = "✅" if actual in NEW_DATA_TYPES else "❌"
        print(f"  {is_new} {m_name:20s} data_type={actual!r}")
