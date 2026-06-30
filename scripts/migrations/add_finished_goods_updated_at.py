"""v6.0.2 修补: finished_goods 表加 updated_at 列
6 处 SQL 都用 updated_at=NOW() 但表无此列 → ship_out 失败
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env", override=False)

import pymysql

conn = pymysql.connect(
    host=os.environ["MYSQL_HOST"], port=int(os.environ["MYSQL_PORT"]),
    user=os.environ["MYSQL_USER"], password=os.environ["MYSQL_PASSWORD"],
    database=os.environ["MYSQL_DATABASE"], charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)
try:
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) AS cnt FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = 'finished_goods'
          AND column_name = 'updated_at'
    """)
    row = c.fetchone()
    cnt = row["cnt"] if isinstance(row, dict) else row[0]
    if cnt:
        print("updated_at 列已存在, 跳过")
    else:
        c.execute("""
            ALTER TABLE finished_goods
            ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP
            COMMENT '更新时间（v6.0.2）' AFTER in_date
        """)
        conn.commit()
        print("已添加 updated_at 列")
finally:
    conn.close()
