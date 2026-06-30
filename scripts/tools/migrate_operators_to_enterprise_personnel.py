"""
将 dispatch_operators 表数据迁移到 enterprise_personnel 表

迁移逻辑：
1. 读取 dispatch_operators 表中所有操作员记录
2. 将每条记录 upsert 到 enterprise_personnel 表，设置 is_operator=1
3. 仅迁移不存在的记录或更新已有记录的 is_operator 标志位
4. 幂等：可重复执行，不会产生重复数据

用法：
    python scripts/tools/migrate_operators_to_enterprise_personnel.py
"""
import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

_PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from core.config import MYSQL_CFG


def get_connection():
    import pymysql
    return pymysql.connect(**MYSQL_CFG, charset='utf8mb4')


def migrate():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM dispatch_operators")
        total = cursor.fetchone()[0]
        logger.info('dispatch_operators 表中记录数: %d', total)

        cursor.execute("""
            SELECT operator_id, name, wechat_userid, code, role, department,
                   enabled, notify_enabled, max_tasks, resigned_at
            FROM dispatch_operators
        """)
        rows = cursor.fetchall()
        migrated = 0
        skipped = 0
        for row in rows:
            operator_id = row[0]
            name = row[1] or ''
            wechat_userid = row[2] or operator_id
            code = row[3] or ''
            role = row[4] or '操作员'
            enabled = bool(row[6]) if row[6] is not None else True
            notify_enabled = bool(row[7]) if row[7] is not None else True
            max_tasks = row[8] if row[8] is not None else 10

            cursor.execute("SELECT is_operator FROM enterprise_personnel WHERE userid = %s", (operator_id,))
            existing = cursor.fetchone()

            if existing:
                if existing[0]:
                    skipped += 1
                    continue
                cursor.execute("""
                    UPDATE enterprise_personnel
                    SET is_operator=1, operator_id=%s, name=%s, code=%s, role=%s,
                        enabled=%s, notify_enabled=%s, max_tasks=%s
                    WHERE userid=%s
                """, (operator_id, name, code, role, enabled, notify_enabled, max_tasks, operator_id))
            else:
                cursor.execute("""
                    INSERT INTO enterprise_personnel
                        (userid, name, code, role, is_operator, operator_id,
                         enabled, notify_enabled, max_tasks)
                    VALUES (%s, %s, %s, %s, 1, %s, %s, %s, %s)
                """, (operator_id, name, code, role, operator_id, enabled, notify_enabled, max_tasks))
            migrated += 1

        conn.commit()
        logger.info('迁移完成: 已迁移 %d 条, 已存在跳过 %d 条, 共 %d 条', migrated, skipped, total)
        return True
    except Exception as e:
        conn.rollback()
        logger.error('迁移失败: %s', e)
        return False
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
