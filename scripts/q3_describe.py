#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q3 看 data_packages 表结构"""
import os
import sys
import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "88888888"),
    "database": "container_center",
    "charset": "utf8mb4",
}

conn = pymysql.connect(**DB)
cur = conn.cursor()
cur.execute("DESCRIBE data_packages")
for row in cur.fetchall():
    print(row)
