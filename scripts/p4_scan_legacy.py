#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RE-006 P4 扫描 data_packages 表残留旧 data_type"""
import json
import sys
import os

# 根目录 = 脚本所在目录的祖父(脚本在 scripts/)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.data_type_contract import LEGACY_TO_NEW, NEW_DATA_TYPES

import pymysql  # noqa: E402

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "88888888"),
    "database": "container_center",
    "charset": "utf8mb4",
}

conn = pymysql.connect(**DB_CONFIG)
cur = conn.cursor()

# 1. 列出当前 data_packages 表的所有 data_type 分布
cur.execute("SELECT data_type, COUNT(*) FROM data_packages GROUP BY data_type ORDER BY COUNT(*) DESC")
print("data_packages data_type 分布:")
for dt, cnt in cur.fetchall():
    is_new = "新" if dt in NEW_DATA_TYPES else "旧"
    note = " ← LEGACY" if dt in LEGACY_TO_NEW and dt not in NEW_DATA_TYPES else ""
    print(f"  [{is_new}] {dt!r:30s}  {cnt:5d}{note}")

# 2. 找出所有不在 NEW_DATA_TYPES 的旧 data_type
cur.execute("SELECT DISTINCT data_type FROM data_packages WHERE data_type NOT IN %s",
            (tuple(NEW_DATA_TYPES),))
legacy = [r[0] for r in cur.fetchall()]
print(f"\n残留旧 data_type: {legacy}")

# 3. 逐个给出建议
for old in legacy:
    new = LEGACY_TO_NEW.get(old, "__dynamic__")
    print(f"  {old!r:20s} -> {new!r}")

# 4. 看是否还有空字符串
cur.execute("SELECT COUNT(*) FROM data_packages WHERE data_type='' OR data_type IS NULL")
empty_cnt = cur.fetchone()[0]
print(f"\n空/NULL data_type: {empty_cnt}")

conn.close()
