"""清理 dry-run 测试数据"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path("d:/yuan/不锈钢网带跟单3.0").resolve()
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env", override=False)

import pymysql
conn = pymysql.connect(
    host=os.environ["MYSQL_HOST"], port=int(os.environ["MYSQL_PORT"]),
    user=os.environ["MYSQL_USER"], password=os.environ["MYSQL_PASSWORD"],
    database=os.environ["MYSQL_DATABASE"], charset="utf8mb4", autocommit=True,
)
c = conn.cursor()
c.execute("DELETE FROM finished_goods")
c.execute("DELETE FROM process_records WHERE order_no LIKE %s", ("DRY-%",))
c.execute("DELETE FROM production_orders WHERE order_no LIKE %s", ("DRY-%",))
c.execute("DELETE FROM orders WHERE order_no LIKE %s", ("DRY-%",))
c.execute("DELETE FROM status_change_logs_current WHERE table_name IN ('orders', 'process_records', 'shipments', 'finished_goods')")
print("cleaned")
conn.close()
