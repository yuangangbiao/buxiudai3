# -*- coding: utf-8 -*-
r"""v6.0.1 修补：status_change_logs_current 表加 remark 列

log_status_change 函数签名扩展为 6 参（含 remark），
但表 status_change_logs_current 没有 remark 列。

执行：
python d:/yuan/不锈钢网带跟单3.0/scripts/migrations/add_status_log_remark.py
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env", override=False)

from core.db import get_connection


def main():
    conn = get_connection()
    try:
        cur = conn.cursor()
        # 检查列是否存在
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'status_change_logs_current'
              AND column_name = 'remark'
        """)
        exists = cur.fetchone()
        # 兼容 dict / tuple 两种返回
        if isinstance(exists, dict):
            exists_count = exists.get("COUNT(*)", 0)
        else:
            exists_count = exists[0] if exists else 0
        if exists_count:
            print("remark 列已存在，跳过")
            return
        # 加列
        cur.execute("""
            ALTER TABLE status_change_logs_current
            ADD COLUMN remark VARCHAR(500) DEFAULT '' COMMENT '变更备注（v6.0.1）' AFTER operator
        """)
        conn.commit()
        print("已添加 remark 列")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
