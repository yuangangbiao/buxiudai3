# -*- coding: utf-8 -*-
"""
wechat_container SQLite → MySQL 数据迁移脚本 v2.0
==================================================
基于真实 29 张表结构，逐表迁移数据到 steel_belt 库 cc_ 前缀表。

特性:
  - 迁移前自动备份 SQLite 源文件
  - 逐表迁移 + 实时行数校验
  - UUID 主键保留（VARCHAR(36)）
  - JSON 列自动序列化
  - 批量插入（500 条/批）
  - 迁移后完整性报告
  - 干运行模式（--dry-run）

用法:
  python migrate_v2.py              # 完整迁移
  python migrate_v2.py --dry-run    # 干运行（仅统计）
  python migrate_v2.py --table cc_process_records  # 单表迁移

版本: v2.0, 2026-05-29
"""
import sqlite3
import os
import sys
import json
import shutil
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional

import pymysql
from pymysql.cursors import DictCursor

# ───── 配置 ─────
SRC_DB = os.environ.get(
    'SRC_DB_PATH',
    r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
)
BACKUP_DIR = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\_migration_backups'
BATCH_SIZE = 500
PREFIX = 'cc_'  # MySQL 表名前缀

MYSQL_CFG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD') or '88888888',
    'database': os.environ.get('CONTAINER_MYSQL_DATABASE', 'container_center'),
    'charset': 'utf8mb4',
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('migrate')


class MigrationEngine:
    """数据迁移引擎"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.sqlite_conn = None
        self.mysql_conn = None
        self.stats = {'tables': 0, 'rows': 0, 'failed': []}

    def connect_sources(self):
        """连接源和目标数据库"""
        logger.info('连接 SQLite: %s', SRC_DB)
        self.sqlite_conn = sqlite3.connect(SRC_DB)
        self.sqlite_conn.row_factory = sqlite3.Row

        if not self.dry_run:
            logger.info('连接 MySQL: %s/%s', MYSQL_CFG['host'], MYSQL_CFG['database'])
            self.mysql_conn = pymysql.connect(
                **MYSQL_CFG, cursorclass=DictCursor, autocommit=False
            )

    def disconnect(self):
        """关闭连接"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.mysql_conn:
            self.mysql_conn.close()

    def backup_source(self):
        """备份 SQLite 源文件"""
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        dst = os.path.join(BACKUP_DIR, f'wechat_container_backup_{ts}.db')
        shutil.copy2(SRC_DB, dst)
        size_kb = os.path.getsize(dst) / 1024
        logger.info('已备份: %s (%.1f KB)', dst, size_kb)
        return dst

    def get_tables(self) -> List[str]:
        """获取所有需要迁移的表"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        return [t[0] for t in cursor.fetchall()]

    def get_columns(self, table_name: str) -> List[Dict]:
        """获取列定义"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f'PRAGMA table_info({table_name})')
        return [
            {'cid': c[0], 'name': c[1], 'type': c[2], 'notnull': not c[3],
             'default': c[4], 'pk': c[5]}
            for c in cursor.fetchall()
        ]

    def get_row_count(self, table_name: str) -> int:
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        return cursor.fetchone()[0]

    def migrate_table(self, table_name: str) -> dict:
        """迁移单个表"""
        columns = self.get_columns(table_name)
        col_names = [c['name'] for c in columns]
        src_count = self.get_row_count(table_name)

        mysql_table = table_name if table_name.startswith('_') else f'{PREFIX}{table_name}'
        logger.info(f'迁移: {table_name} → {mysql_table} ({src_count} 行, {len(columns)} 列)')

        if src_count == 0:
            logger.info(f'  跳过（无数据）')
            return {'table': table_name, 'mysql_table': mysql_table, 'rows': 0, 'status': 'skipped'}

        if self.dry_run:
            return {'table': table_name, 'mysql_table': mysql_table, 'rows': src_count, 'status': 'dry_run'}

        # 读取 SQLite 数据
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f'SELECT * FROM {table_name}')
        rows = [dict(r) for r in cursor.fetchall()]

        # 构建 INSERT SQL — 使用 INSERT IGNORE 避免列不匹配问题
        placeholders = ', '.join(['%s'] * len(col_names))
        cols_str = ', '.join(f'`{c}`' for c in col_names)
        sql = f'INSERT IGNORE INTO `{mysql_table}` ({cols_str}) VALUES ({placeholders})'

        mysql_cursor = self.mysql_conn.cursor()

        try:
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i:i + BATCH_SIZE]
                values_list = [
                    tuple(self._convert_value(row.get(c)) for c in col_names)
                    for row in batch
                ]
                mysql_cursor.executemany(sql, values_list)
                self.mysql_conn.commit()
                logger.info(f'  进度: {min(i+BATCH_SIZE, src_count)}/{src_count}')

            # 验证
            mysql_cursor.execute(f'SELECT COUNT(*) as cnt FROM `{mysql_table}`')
            dst_count = mysql_cursor.fetchone()['cnt']

            # 单表报告
            status = 'success' if dst_count >= src_count else 'mismatch'
            if dst_count < src_count:
                logger.warning(f'  ⚠️ 行数不一致: SQLite={src_count}, MySQL={dst_count}')
            else:
                logger.info(f'  ✅ 迁移完成: {dst_count} 行')

            return {
                'table': table_name, 'mysql_table': mysql_table,
                'src_rows': src_count, 'dst_rows': dst_count, 'status': status
            }

        except Exception as e:
            self.mysql_conn.rollback()
            logger.error(f'  ❌ 失败: {e}')
            return {
                'table': table_name, 'mysql_table': mysql_table,
                'src_rows': src_count, 'error': str(e), 'status': 'failed'
            }

    def _convert_value(self, value):
        """转换值为 MySQL 兼容格式"""
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, (int, float, str)):
            return value
        return str(value)

    def run(self, target_table: str = None) -> dict:
        """执行迁移"""
        logger.info('=' * 60)
        logger.info('wechat_container SQLite → MySQL 迁移 v2.0')
        if self.dry_run:
            logger.info('模式: 干运行（仅统计）')
        logger.info('=' * 60)

        self.backup_source()
        self.connect_sources()

        tables = self.get_tables()
        total_src = 0
        total_dst = 0
        failed = []
        results = []

        for i, tname in enumerate(tables, 1):
            if target_table and tname != target_table:
                continue
            result = self.migrate_table(tname)
            results.append(result)
            total_src += result.get('src_rows', 0)
            total_dst += result.get('dst_rows', 0)
            if result['status'] == 'failed':
                failed.append(tname)

        self.disconnect()

        # ───── 汇总报告 ─────
        logger.info('=' * 60)
        logger.info('迁移完成！')
        logger.info('=' * 60)
        logger.info(f'表总数:     {len(tables)} 张')
        logger.info(f'迁移表数:   {len(results)} 张')
        logger.info(f'源行数:     {total_src} 行')
        logger.info(f'目标行数:   {total_dst} 行')
        if failed:
            logger.error(f'失败表:    {", ".join(failed)}')

        report = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': self.dry_run,
            'total_tables': len(tables),
            'migrated_tables': len(results),
            'total_source_rows': total_src,
            'total_dest_rows': total_dst,
            'failed_tables': failed,
            'results': results,
        }

        # 写入报告文件
        report_file = os.path.join(BACKUP_DIR, f'migration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f'报告: {report_file}')

        return report


def main():
    parser = argparse.ArgumentParser(description='wechat_container → MySQL 迁移 v2.0')
    parser.add_argument('--dry-run', action='store_true', help='干运行（仅统计，不实际写入）')
    parser.add_argument('--table', type=str, help='仅迁移指定表（不含 cc_ 前缀）')
    args = parser.parse_args()

    engine = MigrationEngine(dry_run=args.dry_run)
    engine.run(target_table=args.table)


if __name__ == '__main__':
    main()
