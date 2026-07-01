# -*- coding: utf-8 -*-
"""
[F6 P9 2026-06-10] 一次性清理脚本: 删除 4 张跨库历史表
- steel_belt.enterprise_structure, attendance, data_packages, product_flow_map (这 4 张应在 container_center)
- container_center.process_names, customer_contacts, schedule_records (这 3 张应在 steel_belt)

流程:
  1. 干跑: 列出每张表行数 + 来源库
  2. 真跑: DROP TABLE IF EXISTS
"""
import os
import sys
import argparse
import logging
import pymysql
from pymysql.cursors import DictCursor

_PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
sys.path.insert(0, _PROJECT_ROOT)
os.chdir(_PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('drop_legacy_tables')

# 应在 container_center, 实际在 steel_belt
TABLES_IN_WRONG_DB = {
    'container_center': [
        # 这 3 张应在 steel_belt, 实际在 container_center
        ('process_names', 'steel_belt 业务字典表'),
        ('customer_contacts', 'steel_belt 客户联系表'),
        ('schedule_records', 'schedule_routes 用, 但当前在 container_center'),
    ],
    'steel_belt': [
        # 这 4 张应在 container_center, 实际在 steel_belt
        ('enterprise_structure', 'MySQLStorage 行 168 DDL 历史建表'),
        ('attendance', 'MySQLStorage 行 191 DDL 历史建表'),
        ('data_packages', 'MySQLStorage 行 238 DDL 历史建表'),
        ('product_flow_map', '已废弃, container_center_api:2479 标注'),
    ],
}


def _connect_db(database):
    from core.config import CONTAINER_MYSQL_CFG, MYSQL_CFG, DB_CONNECT_TIMEOUT
    cfg_src = CONTAINER_MYSQL_CFG if database == 'container_center' else MYSQL_CFG
    cfg = {k: v for k, v in cfg_src.items() if k not in ('cursorclass', 'database')}
    cfg['connect_timeout'] = DB_CONNECT_TIMEOUT
    cfg['database'] = database
    cfg['cursorclass'] = DictCursor
    return pymysql.connect(**cfg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    logger.info('=' * 60)
    logger.info(f'{"干跑" if args.dry_run else "真跑"} 模式')
    logger.info('=' * 60)

    stats = {'checked': 0, 'empty': 0, 'has_data': 0, 'dropped': 0, 'failed': 0}

    for source_db, tables in TABLES_IN_WRONG_DB.items():
        logger.info(f'\n=== {source_db} 库的 4 张跨库表 ===')
        conn = _connect_db(source_db)
        try:
            with conn.cursor() as cur:
                for tbl, desc in tables:
                    stats['checked'] += 1
                    cur.execute(f"SELECT COUNT(*) AS cnt FROM `{tbl}`")
                    row = cur.fetchone()
                    cnt = row['cnt'] if row else 0
                    cur.execute(f"SHOW CREATE TABLE `{tbl}`")
                    schema = cur.fetchone()
                    logger.info(f'  {tbl} ({desc})  行数={cnt}')
                    if cnt > 0:
                        stats['has_data'] += 1
                        logger.warning(f'    ⚠️  表非空, 如 DROP 需先备份')

                    if args.dry_run:
                        continue
                    try:
                        cur.execute(f'DROP TABLE IF EXISTS `{tbl}`')
                        logger.info(f'    ✅ DROP 完成')
                        stats['dropped'] += 1
                    except Exception as e:
                        logger.error(f'    ✗ DROP 失败: {e}')
                        stats['failed'] += 1
            conn.commit()
        finally:
            conn.close()

    logger.info('=' * 60)
    logger.info(f'扫描: {stats["checked"]} 张, 非空: {stats["has_data"]}, DROP: {stats["dropped"]}, 失败: {stats["failed"]}')
    logger.info('=' * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
