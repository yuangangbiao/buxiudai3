#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RE-006 P6 兜底:用 Python 文本替换强制修改 collect_repair/collect_material 的 data_type"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "mobile_api_ai/container_center_v5.py")

src = open(TARGET, encoding="utf-8").read()
orig = src

# 1. collect_repair: 替换 'data_type=\'repair\'' (在 collect_repair 方法体里)
needle = "        pkg = self.collector.collect(\n            data_type='repair',"
replacement = "        pkg = self.collector.collect(\n            data_type=NEW_DATA_TYPE_FOR_COLLECT['repair'],"
if needle in src:
    src = src.replace(needle, replacement, 1)
    print("[1] collect_repair 修复 OK")
else:
    print("[1] collect_repair needle 未找到")

# 2. collect_material: 替换 'data_type=\'material\''
needle2 = "        return self.collector.collect(\n            data_type='material',"
replacement2 = "        return self.collector.collect(\n            data_type=NEW_DATA_TYPE_FOR_COLLECT['material'],"
if needle2 in src:
    src = src.replace(needle2, replacement2, 1)
    print("[2] collect_material 修复 OK")
else:
    print("[2] collect_material needle 未找到")

# 3. 验证
if src == orig:
    print("\n[INFO] 无需修改")
    sys.exit(0)# 写回
with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)
print(f"\n✅ 已写回 {TARGET}")
print("   字节数:", len(src))

# 4. 验证
import re
print("\n【验证】所有 data_type 赋值:")
for m in re.finditer(r"data_type\s*=\s*['\"]?(\w+)['\"]?|data_type\s*=\s*NEW_DATA_TYPE_FOR_COLLECT\['(\w+)'\]", src):
    print(f"  L{ src[:m.start()].count(chr(10)) + 1 }  {m.group(0)}")
