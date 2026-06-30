# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r"d:\yuan\不锈钢网带跟单3.0")

try:
    import pymysql
    print("pymysql imported successfully")
    print(f"pymysql version: {pymysql.__version__}")
except Exception as e:
    print(f"pymysql import error: {e}")

try:
    from desktop.views.dashboard.dashboard_server import get_db_connection
    print("\nTrying to get database connection...")
    conn = get_db_connection()
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection error: {e}")
    import traceback
    traceback.print_exc()
