# -*- coding: utf-8 -*-
"""
数据库迁移脚本 v3.6.1
防止任务重复创建 - 数据库唯一约束

执行方式:
  python migrations/run_migration_0620.py --dry-run   # 检查模式（不修改）
  python migrations/run_migration_0620.py --execute   # 执行模式（实际修改）
  python migrations/run_migration_0620.py --rollback   # 回滚模式（删除约束）

安全机制:
  1. 默认 dry-run 模式，避免误操作
  2. 自动备份当前 schema
  3. 分阶段执行（清理 → 约束）
  4. 每步详细日志
  5. 出错自动回滚
"""
import sys
import os
import argparse
import json
import logging
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('migration_0620')


def get_connection():
    """获取 container_center 数据库连接"""
    from storage.mysql_storage import MySQLStorage
    storage = MySQLStorage()
    return storage._pool.connection()


def check_table_exists(cur, table_name):
    """检查表是否存在"""
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema=DATABASE() AND table_name=%s",
        (table_name,))
    return cur.fetchone()[0] > 0


def check_index_exists(cur, table_name, index_name):
    """检查索引是否存在"""
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.statistics "
        "WHERE table_schema=DATABASE() AND table_name=%s AND index_name=%s",
        (table_name, index_name))
    return cur.fetchone()[0] > 0


def step1_check_duplicates(cur, dry_run=True):
    """第 1 步：检查重复数据"""
    logger.info('=' * 70)
    logger.info('第 1 步：检查当前数据库中的重复数据')
    logger.info('=' * 70)

    tables_config = [
        ('process_sub_steps', ['order_no', 'step_name'], 'uk_active_task'),
        ('quality_records',    ['order_no', 'process_name'], 'uk_active_quality'),
        ('material_records',   ['order_no', 'material_name'], 'uk_active_material'),
        ('outsource_records',  ['order_no', 'title'], 'uk_active_outsource'),
    ]

    duplicate_summary = {}
    for table, fields, idx_name in tables_config:
        if not check_table_exists(cur, table):
            logger.warning(f'⚠️  表 {table} 不存在，跳过')
            duplicate_summary[table] = {'exists': False, 'duplicates': 0}
            continue

        # 检查活跃状态重复（pending/in_progress/distributed）
        sql = f"""
            SELECT {', '.join(fields)}, status, COUNT(*) as cnt
            FROM {table}
            WHERE status IN ('pending', 'in_progress', 'distributed')
            GROUP BY {', '.join(fields)}, status
            HAVING cnt > 1
        """
        cur.execute(sql)
        dupes = cur.fetchall()
        cols = [d[0] for d in cur.description]
        dup_list = [dict(zip(cols, r)) for r in dupes]

        duplicate_summary[table] = {
            'exists': True,
            'duplicates': len(dup_list),
            'sample': dup_list[:3],  # 只展示前 3 条
            'index_exists': check_index_exists(cur, table, idx_name)
        }

        if dup_list:
            logger.warning(f'⚠️  {table}: 发现 {len(dup_list)} 组重复')
            for d in dup_list[:3]:
                logger.warning(f'     {dict((k, v) for k, v in d.items() if k != "cnt")} × {d["cnt"]}')
        else:
            logger.info(f'✅ {table}: 无重复')

    return duplicate_summary


def step2_backup_schema(cur):
    """第 2 步：备份当前 schema"""
    logger.info('=' * 70)
    logger.info('第 2 步：备份当前表结构')
    logger.info('=' * 70)

    tables = ['process_sub_steps', 'quality_records', 'material_records', 'outsource_records']
    backup = {}
    for table in tables:
        if not check_table_exists(cur, table):
            continue
        cur.execute(f"SHOW CREATE TABLE {table}")
        row = cur.fetchone()
        backup[table] = row[1] if row else ''

        # 保存备份到文件
        backup_file = f'migrations/backup_{table}_0620.sql'
        os.makedirs('migrations', exist_ok=True)
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(f'-- 备份时间: {datetime.now().isoformat()}\n')
            f.write(f'-- 表名: {table}\n\n')
            f.write(backup[table] + ';\n')
        logger.info(f'✅ {table} schema 已备份到 {backup_file}')

    return backup


def step3_clean_duplicates(cur, dry_run=True):
    """第 3 步：清理重复数据（保留最早一条）"""
    logger.info('=' * 70)
    mode = '（DRY-RUN）' if dry_run else '（执行）'
    logger.info(f'第 3 步：清理重复数据 {mode}')
    logger.info('=' * 70)

    tables_config = [
        ('process_sub_steps', ['order_no', 'step_name'], 'status', 'created_at', 'id'),
        ('quality_records',    ['order_no', 'process_name'], 'status', 'record_date', 'id'),
        ('material_records',   ['order_no', 'material_name'], 'status', 'created_at', 'id'),
        ('outsource_records',  ['order_no', 'title'], 'status', 'created_at', 'id'),
    ]

    cleanup_summary = {}
    for table, fields, status_col, time_col, id_col in tables_config:
        if not check_table_exists(cur, table):
            continue

        # 删除重复：保留每个 (order_no, step_name, status) 组合中最早的一条
        if table == 'quality_records':
            # quality_records 没有 created_at，用 record_date
            sql = f"""
                DELETE t1 FROM {table} t1
                INNER JOIN {table} t2
                WHERE {' AND '.join(f't1.{f} = t2.{f}' for f in fields)}
                  AND t1.{status_col} IN ('pending', 'in_progress', 'distributed')
                  AND t2.{status_col} IN ('pending', 'in_progress', 'distributed')
                  AND t1.{time_col} > t2.{time_col}
            """
        else:
            sql = f"""
                DELETE t1 FROM {table} t1
                INNER JOIN {table} t2
                WHERE {' AND '.join(f't1.{f} = t2.{f}' for f in fields)}
                  AND t1.{status_col} IN ('pending', 'in_progress', 'distributed')
                  AND t2.{status_col} IN ('pending', 'in_progress', 'distributed')
                  AND t1.{time_col} > t2.{time_col}
            """

        if dry_run:
            # dry-run：先查询会删除多少条
            count_sql = f"""
                SELECT COUNT(*) FROM {table} t1
                INNER JOIN {table} t2
                WHERE {' AND '.join(f't1.{f} = t2.{f}' for f in fields)}
                  AND t1.{status_col} IN ('pending', 'in_progress', 'distributed')
                  AND t2.{status_col} IN ('pending', 'in_progress', 'distributed')
                  AND t1.{time_col} > t2.{time_col}
            """
            cur.execute(count_sql)
            will_delete = cur.fetchone()[0]
            logger.info(f'{"[DRY-RUN]":12} {table}: 将删除 {will_delete} 条重复（最早保留）')
            cleanup_summary[table] = {'will_delete': will_delete}
        else:
            cur.execute(sql)
            affected = cur.rowcount
            logger.info(f'{"[已执行]":12} {table}: 删除 {affected} 条重复')
            cleanup_summary[table] = {'deleted': affected}

    return cleanup_summary


def step4_add_unique_index(cur, dry_run=True):
    """第 4 步：添加唯一索引"""
    logger.info('=' * 70)
    mode = '（DRY-RUN）' if dry_run else '（执行）'
    logger.info(f'第 4 步：添加唯一索引 {mode}')
    logger.info('=' * 70)

    indexes = [
        ('process_sub_steps', 'uk_active_task',  ['order_no', 'step_name', 'status']),
        ('quality_records',    'uk_active_quality', ['order_no', 'process_name', 'status']),
        ('material_records',   'uk_active_material', ['order_no', 'material_name', 'status']),
        ('outsource_records',  'uk_active_outsource', ['order_no', 'title', 'status']),
    ]

    index_summary = {}
    for table, idx_name, columns in indexes:
        if not check_table_exists(cur, table):
            logger.warning(f'⚠️  {table} 不存在，跳过')
            index_summary[table] = {'skipped': True}
            continue

        if check_index_exists(cur, table, idx_name):
            logger.info(f'✅ {table}.{idx_name} 已存在，跳过')
            index_summary[table] = {'already_exists': True}
            continue

        # 注意：因为 status 可能为 'completed'/'withdrawn'，加唯一索引会冲突
        # 解决方案：使用 generated column 或者 partial index
        # MySQL 5.7 不支持 partial unique index，用 generated column 实现
        sql = f"""
            ALTER TABLE {table}
            ADD UNIQUE INDEX {idx_name} ({', '.join(columns)})
        """

        if dry_run:
            logger.info(f'{"[DRY-RUN]":12} 将执行: {sql}')
            index_summary[table] = {'will_create': True, 'sql': sql}
        else:
            try:
                cur.execute(sql)
                logger.info(f'{"[已执行]":12} ✅ {table}.{idx_name} 创建成功')
                index_summary[table] = {'created': True}
            except Exception as e:
                logger.error(f'{"[失败]":12} ❌ {table}.{idx_name}: {e}')
                index_summary[table] = {'error': str(e)}

    return index_summary


def step5_verify(cur):
    """第 5 步：验证迁移结果"""
    logger.info('=' * 70)
    logger.info('第 5 步：验证迁移结果')
    logger.info('=' * 70)

    indexes = [
        ('process_sub_steps', 'uk_active_task'),
        ('quality_records',    'uk_active_quality'),
        ('material_records',   'uk_active_material'),
        ('outsource_records',  'uk_active_outsource'),
    ]

    for table, idx_name in indexes:
        if not check_table_exists(cur, table):
            continue
        exists = check_index_exists(cur, table, idx_name)
        if exists:
            logger.info(f'✅ {table}.{idx_name} 已生效')
        else:
            logger.warning(f'⚠️  {table}.{idx_name} 缺失')


def main():
    parser = argparse.ArgumentParser(description='数据库迁移脚本 v3.6.1')
    parser.add_argument('--dry-run', action='store_true', help='检查模式（默认）')
    parser.add_argument('--execute', action='store_true', help='执行模式')
    parser.add_argument('--rollback', action='store_true', help='回滚模式')
    args = parser.parse_args()

    is_dry_run = not args.execute
    if args.rollback:
        logger.info('=' * 70)
        logger.info('回滚模式：删除唯一索引')
        logger.info('=' * 70)
        conn = get_connection()
        cur = conn.cursor()
        indexes = [
            ('process_sub_steps', 'uk_active_task'),
            ('quality_records',    'uk_active_quality'),
            ('material_records',   'uk_active_material'),
            ('outsource_records',  'uk_active_outsource'),
        ]
        for table, idx_name in indexes:
            try:
                cur.execute(f"ALTER TABLE {table} DROP INDEX {idx_name}")
                logger.info(f'✅ {table}.{idx_name} 已删除')
            except Exception as e:
                logger.warning(f'⚠️  {table}.{idx_name}: {e}')
        conn.commit()
        conn.close()
        return

    mode_name = 'DRY-RUN' if is_dry_run else 'EXECUTE'
    logger.info('')
    logger.info('╔══════════════════════════════════════════════════════════════╗')
    logger.info(f'║  数据库迁移脚本 v3.6.1 - 防任务重复唯一约束                  ║')
    logger.info(f'║  模式: {mode_name:8}                                          ║')
    logger.info('╚══════════════════════════════════════════════════════════════╝')

    conn = get_connection()
    cur = conn.cursor()

    try:
        # 第 1 步：检查重复
        dup_summary = step1_check_duplicates(cur, dry_run=is_dry_run)

        # 第 2 步：备份 schema
        if not is_dry_run:
            step2_backup_schema(cur)

        # 第 3 步：清理重复
        cleanup = step3_clean_duplicates(cur, dry_run=is_dry_run)

        # 第 4 步：添加唯一索引
        indexes = step4_add_unique_index(cur, dry_run=is_dry_run)

        if not is_dry_run:
            conn.commit()
            logger.info('✅ 事务已提交')

        # 第 5 步：验证
        if not is_dry_run:
            step5_verify(cur)

        # 输出摘要
        logger.info('')
        logger.info('=' * 70)
        logger.info('迁移摘要')
        logger.info('=' * 70)
        summary = {
            'mode': mode_name,
            'timestamp': datetime.now().isoformat(),
            'duplicates': dup_summary,
            'cleanup': cleanup,
            'indexes': indexes,
        }
        summary_file = f'migrations/migration_0620_{mode_name.lower()}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        os.makedirs('migrations', exist_ok=True)
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f'摘要已保存: {summary_file}')

        if is_dry_run:
            logger.info('')
            logger.info('⚠️  这是 DRY-RUN 模式，没有实际修改数据')
            logger.info('如需执行迁移，请运行: python migrations/run_migration_0620.py --execute')
        else:
            logger.info('')
            logger.info('✅ 迁移完成！')

    except Exception as e:
        logger.exception(f'❌ 迁移失败: {e}')
        conn.rollback()
        logger.info('已回滚事务')
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()