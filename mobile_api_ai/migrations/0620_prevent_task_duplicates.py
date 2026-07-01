# -*- coding: utf-8 -*-
"""
迁移: 防任务重复 - 数据库唯一约束 (v3.6.1)
版本: 20260620_prevent_task_duplicates
创建时间: 2026-06-20

目的: 即使应用层去重逻辑失效，数据库层也能保证任务不重复

约束:
- process_sub_steps: 同一 (order_no, step_name, status) 唯一（status ∈ active）
- quality_records:   同一 (order_no, process_name, status) 唯一
- material_records:  同一 (order_no, material_name, status) 唯一
- outsource_records: 同一 (order_no, title, status) 唯一

执行方式:
    python migrations/run.py status
    python migrations/run.py upgrade
    python migrations/run.py downgrade -v 20260620_prevent_task_duplicates

或直接执行（独立运行）:
    python migrations/0620_prevent_task_duplicates.py
"""
import os
import sys
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════════════════

def get_conn():
    """获取 container_center 数据库连接"""
    try:
        from storage.mysql_storage import MySQLStorage
        storage = MySQLStorage()
        return storage._pool.connection()
    except Exception as e:
        logger.warning(f'[MIG] MySQLStorage 失败，回退直连: {e}')
        import pymysql
        return pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DATABASE', 'container_center'),
            charset='utf8mb4'
        )


def check_table_exists(cursor, table_name):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema=DATABASE() AND table_name=%s",
        (table_name,))
    return cursor.fetchone()[0] > 0


def check_index_exists(cursor, table_name, index_name):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.statistics "
        "WHERE table_schema=DATABASE() AND table_name=%s AND index_name=%s",
        (table_name, index_name))
    return cursor.fetchone()[0] > 0


def step_log(step, msg):
    """打印步骤日志"""
    logger.info(f"[{step}] {msg}")


# ═══════════════════════════════════════════════════════════════════════════════
# 升级操作
# ═══════════════════════════════════════════════════════════════════════════════

def upgrade(conn, dry_run=False):
    """执行迁移升级

    Args:
        conn: 数据库连接
        dry_run: 是否为预演（只读不写）
    """
    cur = conn.cursor()
    try:
        # ─────────────────────────────────────────
        # 1. process_sub_steps
        # ─────────────────────────────────────────
        step_log(1, 'process_sub_steps 表去重约束')
        if not check_table_exists(cur, 'process_sub_steps'):
            logger.warning('⚠️  process_sub_steps 表不存在，跳过')
        else:
            # 清理重复
            if not dry_run:
                cur.execute("""
                    DELETE p1 FROM process_sub_steps p1
                    INNER JOIN process_sub_steps p2
                    WHERE p1.order_no = p2.order_no
                      AND p1.step_name = p2.step_name
                      AND p1.status IN ('pending', 'in_progress', 'distributed')
                      AND p2.status IN ('pending', 'in_progress', 'distributed')
                      AND p1.created_at > p2.created_at
                """)
                affected = cur.rowcount
                logger.info(f'   清理重复: {affected} 条')

            # 添加唯一索引
            idx = 'uk_active_task'
            if check_index_exists(cur, 'process_sub_steps', idx):
                logger.info(f'   索引 {idx} 已存在，跳过')
            else:
                if dry_run:
                    logger.info(f'   [DRY-RUN] 将创建索引 {idx}')
                else:
                    cur.execute(
                        f"ALTER TABLE process_sub_steps "
                        f"ADD UNIQUE INDEX {idx} (order_no, step_name, status)"
                    )
                    logger.info(f'   ✅ 索引 {idx} 创建成功')

        # ─────────────────────────────────────────
        # 2. quality_records
        # ─────────────────────────────────────────
        step_log(2, 'quality_records 表去重约束')
        if not check_table_exists(cur, 'quality_records'):
            logger.warning('⚠️  quality_records 表不存在，跳过')
        else:
            if not dry_run:
                cur.execute("""
                    DELETE q1 FROM quality_records q1
                    INNER JOIN quality_records q2
                    WHERE q1.order_no = q2.order_no
                      AND q1.process_name = q2.process_name
                      AND q1.status IN ('pending', 'in_progress')
                      AND q2.status IN ('pending', 'in_progress')
                      AND q1.record_date > q2.record_date
                """)
                affected = cur.rowcount
                logger.info(f'   清理重复: {affected} 条')

            idx = 'uk_active_quality'
            if check_index_exists(cur, 'quality_records', idx):
                logger.info(f'   索引 {idx} 已存在，跳过')
            else:
                if dry_run:
                    logger.info(f'   [DRY-RUN] 将创建索引 {idx}')
                else:
                    cur.execute(
                        f"ALTER TABLE quality_records "
                        f"ADD UNIQUE INDEX {idx} (order_no, process_name, status)"
                    )
                    logger.info(f'   ✅ 索引 {idx} 创建成功')

        # ─────────────────────────────────────────
        # 3. material_records
        # ─────────────────────────────────────────
        step_log(3, 'material_records 表去重约束')
        if not check_table_exists(cur, 'material_records'):
            logger.warning('⚠️  material_records 表不存在，跳过')
        else:
            if not dry_run:
                cur.execute("""
                    DELETE m1 FROM material_records m1
                    INNER JOIN material_records m2
                    WHERE m1.order_no = m2.order_no
                      AND m1.material_name = m2.material_name
                      AND m1.status IN ('pending', 'in_progress')
                      AND m2.status IN ('pending', 'in_progress')
                      AND m1.created_at > m2.created_at
                """)
                affected = cur.rowcount
                logger.info(f'   清理重复: {affected} 条')

            idx = 'uk_active_material'
            if check_index_exists(cur, 'material_records', idx):
                logger.info(f'   索引 {idx} 已存在，跳过')
            else:
                if dry_run:
                    logger.info(f'   [DRY-RUN] 将创建索引 {idx}')
                else:
                    cur.execute(
                        f"ALTER TABLE material_records "
                        f"ADD UNIQUE INDEX {idx} (order_no, material_name, status)"
                    )
                    logger.info(f'   ✅ 索引 {idx} 创建成功')

        # ─────────────────────────────────────────
        # 4. outsource_records
        # ─────────────────────────────────────────
        step_log(4, 'outsource_records 表去重约束')
        if not check_table_exists(cur, 'outsource_records'):
            logger.warning('⚠️  outsource_records 表不存在，跳过')
        else:
            if not dry_run:
                cur.execute("""
                    DELETE o1 FROM outsource_records o1
                    INNER JOIN outsource_records o2
                    WHERE o1.order_no = o2.order_no
                      AND o1.title = o2.title
                      AND o1.status IN ('pending', 'in_progress')
                      AND o2.status IN ('pending', 'in_progress')
                      AND o1.created_at > o2.created_at
                """)
                affected = cur.rowcount
                logger.info(f'   清理重复: {affected} 条')

            idx = 'uk_active_outsource'
            if check_index_exists(cur, 'outsource_records', idx):
                logger.info(f'   索引 {idx} 已存在，跳过')
            else:
                if dry_run:
                    logger.info(f'   [DRY-RUN] 将创建索引 {idx}')
                else:
                    cur.execute(
                        f"ALTER TABLE outsource_records "
                        f"ADD UNIQUE INDEX {idx} (order_no, title, status)"
                    )
                    logger.info(f'   ✅ 索引 {idx} 创建成功')

        # ─────────────────────────────────────────
        # 5. 验证
        # ─────────────────────────────────────────
        step_log(5, '验证迁移结果')
        targets = [
            ('process_sub_steps', 'uk_active_task'),
            ('quality_records',   'uk_active_quality'),
            ('material_records',  'uk_active_material'),
            ('outsource_records', 'uk_active_outsource'),
        ]
        for table, idx in targets:
            if not check_table_exists(cur, table):
                continue
            if check_index_exists(cur, table, idx):
                logger.info(f'   ✅ {table}.{idx} 已生效')
            else:
                logger.warning(f'   ⚠️  {table}.{idx} 缺失')

        if not dry_run:
            conn.commit()
            logger.info('')
            logger.info('=' * 60)
            logger.info('✅ v3.6.1 防任务重复唯一约束已添加')
            logger.info('=' * 60)
        else:
            logger.info('')
            logger.info('=' * 60)
            logger.info('[DRY-RUN] 预演完成，无数据修改')
            logger.info('=' * 60)

    except Exception as e:
        if not dry_run:
            conn.rollback()
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# 回滚操作
# ═══════════════════════════════════════════════════════════════════════════════

def downgrade(conn):
    """回滚迁移"""
    cur = conn.cursor()
    try:
        logger.info('回滚 v3.6.1 防任务重复约束...')
        targets = [
            ('process_sub_steps', 'uk_active_task'),
            ('quality_records',   'uk_active_quality'),
            ('material_records',  'uk_active_material'),
            ('outsource_records', 'uk_active_outsource'),
        ]
        for table, idx in targets:
            if not check_table_exists(cur, table):
                continue
            if not check_index_exists(cur, table, idx):
                logger.info(f'   {table}.{idx} 不存在，跳过')
                continue
            cur.execute(f"ALTER TABLE {table} DROP INDEX {idx}")
            logger.info(f'   ✅ {table}.{idx} 已删除')
        conn.commit()
        logger.info('✅ 回滚完成')
    except Exception as e:
        conn.rollback()
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# 独立运行入口
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    parser = argparse.ArgumentParser(description='v3.6.1 防任务重复迁移')
    parser.add_argument('--dry-run', action='store_true', help='仅检查不修改')
    parser.add_argument('--rollback', action='store_true', help='回滚迁移')
    args = parser.parse_args()

    conn = get_conn()
    try:
        if args.rollback:
            downgrade(conn)
        else:
            upgrade(conn, dry_run=args.dry_run)
    finally:
        conn.close()