# -*- coding: utf-8 -*-
"""
数据合并迁移工具
用于将旧数据库的数据合并到新数据库结构中
场景：
1. 旧数据库有新字段但没有数据
2. 新数据库有数据但没有新字段
3. 需要把两者合并：新字段加到旧数据库，旧数据保留到新数据库

使用前请先备份数据库！
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_db_config():
    """获取数据库配置"""
    try:
        from db_config import MYSQL_CONFIG
        return MYSQL_CONFIG.copy()
    except ImportError:
        return {
            "host": os.getenv('MYSQL_HOST', 'localhost'),
            "port": int(os.getenv('MYSQL_PORT', 3306)),
            "user": os.getenv('MYSQL_USER', 'root'),
            "password": os.getenv('MYSQL_PASSWORD', ''),
            "database": os.getenv('MYSQL_DATABASE', 'steel_belt'),
            "charset": "utf8mb4"
        }


class DataMigrator:
    """数据迁移合并器"""

    def __init__(self, db_config: Optional[Dict] = None):
        self.db_config = db_config or get_db_config()
        self._conn = None
        self.migration_log = []

    def _get_connection(self):
        """获取数据库连接"""
        import pymysql
        if self._conn is None:
            config = self.db_config.copy()
            config["cursorclass"] = pymysql.cursors.DictCursor
            self._conn = pymysql.connect(**config)
        return self._conn

    def close(self):
        """关闭连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def _get_cursor(self):
        """获取游标的上下文管理器"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    def get_table_schema(self, table_name: str) -> List[Dict]:
        """获取表结构"""
        with self._get_cursor() as cursor:
            cursor.execute(f"DESCRIBE `{table_name}`")
            return cursor.fetchall()

    def get_all_tables(self) -> List[str]:
        """获取所有表名"""
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
            """, (self.db_config["database"],))
            return [row["TABLE_NAME"] for row in cursor.fetchall()]

    def get_table_data(self, table_name: str, limit: Optional[int] = None) -> List[Dict]:
        """获取表数据"""
        with self._get_cursor() as cursor:
            query = f"SELECT * FROM `{table_name}`"
            if limit:
                query += f" LIMIT {limit}"
            cursor.execute(query)
            return cursor.fetchall()

    def get_row_count(self, table_name: str) -> int:
        """获取表的行数"""
        with self._get_cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table_name}`")
            return cursor.fetchone()['cnt']

    def check_field_exists(self, table_name: str, field_name: str) -> bool:
        """检查字段是否存在"""
        schema = self.get_table_schema(table_name)
        return any(f['Field'] == field_name for f in schema)

    def add_field_safe(
        self,
        table_name: str,
        field_name: str,
        field_type: str,
        default_value: Any = None,
        after_field: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        安全添加字段（如果不存在才添加）

        Returns:
            (success, message)
        """
        if self.check_field_exists(table_name, field_name):
            return True, f"字段 {field_name} 已存在，跳过"

        schema = self.get_table_schema(table_name)
        if not schema:
            return False, f"表 {table_name} 不存在"

        sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{field_name}` {field_type}"

        if default_value is not None:
            if isinstance(default_value, str):
                sql += f" DEFAULT '{default_value}'"
            else:
                sql += f" DEFAULT {default_value}"

        if after_field and self.check_field_exists(table_name, after_field):
            sql += f" AFTER `{after_field}`"

        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql)

            self.migration_log.append({
                'action': 'add_field',
                'table': table_name,
                'field': field_name,
                'sql': sql,
                'timestamp': datetime.now().isoformat()
            })

            logger.info(f"✅ 添加字段成功: {table_name}.{field_name}")
            return True, f"字段 {field_name} 添加成功"

        except Exception as e:
            error_msg = f"添加字段失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg

    def batch_add_fields(
        self,
        table_name: str,
        fields: Dict[str, Dict]
    ) -> Tuple[bool, str, List[Dict]]:
        """
        批量添加字段

        Args:
            table_name: 表名
            fields: 字段定义 {
                'field_name': {
                    'type': 'VARCHAR(50)',
                    'default': None,
                    'after': 'field_name'
                }
            }

        Returns:
            (success, message, results)
        """
        results = []
        all_success = True

        for field_name, definition in fields.items():
            success, msg = self.add_field_safe(
                table_name,
                field_name,
                definition['type'],
                default_value=definition.get('default'),
                after_field=definition.get('after')
            )
            results.append({
                'field': field_name,
                'success': success,
                'message': msg
            })
            if not success:
                all_success = False

        if all_success:
            return True, f"表 {table_name} 所有字段添加成功", results
        else:
            failed = [r for r in results if not r['success']]
            return False, f"部分字段添加失败: {len(failed)} 个", results

    def update_field_with_value(
        self,
        table_name: str,
        field_name: str,
        value: Any,
        where_clause: str = None,
        where_params: tuple = None
    ) -> Tuple[bool, str]:
        """
        根据条件更新字段值

        Args:
            table_name: 表名
            field_name: 字段名
            value: 要更新的值
            where_clause: WHERE条件 (如 "id > %s AND status = %s")
            where_params: WHERE参数

        Returns:
            (success, message)
        """
        if not self.check_field_exists(table_name, field_name):
            return False, f"字段 {field_name} 不存在"

        if isinstance(value, str):
            sql_value = f"'{value}'"
        elif value is None:
            sql_value = "NULL"
        else:
            sql_value = str(value)

        sql = f"UPDATE `{table_name}` SET `{field_name}` = {sql_value}"

        if where_clause:
            sql += f" WHERE {where_clause}"

        try:
            with self._get_cursor() as cursor:
                if where_params:
                    cursor.execute(sql, where_params)
                else:
                    cursor.execute(sql)

            affected = cursor.rowcount
            logger.info(f"✅ 更新字段 {table_name}.{field_name}: 影响 {affected} 行")
            return True, f"更新成功，影响 {affected} 行"

        except Exception as e:
            error_msg = f"更新字段失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg

    def backup_table(self, table_name: str, backup_suffix: str = None) -> Tuple[bool, str]:
        """
        备份表

        Returns:
            (success, backup_table_name)
        """
        if backup_suffix is None:
            backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_name = f"{table_name}_backup_{backup_suffix}"

        try:
            with self._get_cursor() as cursor:
                cursor.execute(f"CREATE TABLE `{backup_name}` LIKE `{table_name}`")
                cursor.execute(f"INSERT INTO `{backup_name}` SELECT * FROM `{table_name}`")

            logger.info(f"✅ 表 {table_name} 已备份为 {backup_name}")
            return True, backup_name

        except Exception as e:
            error_msg = f"备份表失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg

    def compare_schemas(
        self,
        table_name: str,
        expected_fields: Dict[str, Dict]
    ) -> Dict[str, List]:
        """
        对比表结构，找出缺失的字段

        Returns:
            {
                'missing': [{'field': 'name', 'definition': {...}}],
                'exists': ['field1', 'field2']
            }
        """
        current_schema = self.get_table_schema(table_name)
        current_fields = {f['Field'] for f in current_schema}

        missing = []
        exists = []

        for field_name, definition in expected_fields.items():
            if field_name not in current_fields:
                missing.append({
                    'field': field_name,
                    'definition': definition
                })
            else:
                exists.append(field_name)

        return {
            'missing': missing,
            'exists': exists
        }


class DataMergerConfig:
    """数据合并配置"""

    @staticmethod
    def create_merge_config(
        table_name: str,
        fields_to_add: Dict[str, Dict],
        field_values: Dict[str, Any] = None,
        backup: bool = True
    ) -> Dict:
        """
        创建合并配置

        Args:
            table_name: 表名
            fields_to_add: 要添加的字段 {
                'barcode': {'type': 'VARCHAR(50)', 'default': '', 'after': 'spec'},
                'min_order_qty': {'type': 'DECIMAL(12,2)', 'default': 1.0, 'after': 'price'}
            }
            field_values: 新字段的默认值 {
                'barcode': '',
                'min_order_qty': 1.0
            }
            backup: 是否备份表

        Returns:
            合并配置字典
        """
        return {
            'table': table_name,
            'fields_to_add': fields_to_add,
            'field_values': field_values or {},
            'backup': backup,
            'created_at': datetime.now().isoformat()
        }


class DataMergeExecutor:
    """数据合并执行器"""

    def __init__(self, db_config: Optional[Dict] = None):
        self.migrator = DataMigrator(db_config)
        self.merge_results = []

    def execute_merge(self, config: Dict, dry_run: bool = False) -> Tuple[bool, str]:
        """
        执行数据合并

        Args:
            config: 合并配置
            dry_run: 是否预演（不实际执行）

        Returns:
            (success, message)
        """
        table_name = config['table']
        fields_to_add = config['fields_to_add']
        field_values = config.get('field_values', {})
        backup = config.get('backup', True)

        logger.info(f"\n{'='*60}")
        logger.info(f"开始合并表: {table_name}")
        logger.info(f"{'='*60}")

        if dry_run:
            logger.info("⚠️ 预演模式，不会实际执行任何操作")

        if backup and not dry_run:
            success, backup_name = self.migrator.backup_table(table_name)
            if not success:
                return False, f"备份表失败: {backup_name}"
            logger.info(f"备份表成功: {backup_name}")

        missing_fields = self.migrator.compare_schemas(table_name, fields_to_add)

        if not missing_fields['missing']:
            logger.info(f"表 {table_name} 所有字段已存在，无需添加")
        else:
            logger.info(f"需要添加 {len(missing_fields['missing'])} 个字段")

            if not dry_run:
                success, msg, results = self.migrator.batch_add_fields(
                    table_name,
                    {f['field']: f['definition'] for f in missing_fields['missing']}
                )

                if not success:
                    return False, msg

        for field_name, value in field_values.items():
            if dry_run:
                logger.info(f"预演: 将更新 {table_name}.{field_name} = {value}")
            else:
                success, msg = self.migrator.update_field_with_value(
                    table_name,
                    field_name,
                    value
                )
                if not success:
                    logger.warning(f"更新字段失败: {msg}")

        row_count = self.migrator.get_row_count(table_name)
        logger.info(f"✅ 表 {table_name} 合并完成，当前数据: {row_count} 行")

        self.merge_results.append({
            'table': table_name,
            'row_count': row_count,
            'fields_added': len(fields_to_add),
            'timestamp': datetime.now().isoformat()
        })

        return True, f"合并成功: {table_name}, {row_count} 行数据"

    def execute_batch_merge(
        self,
        configs: List[Dict],
        dry_run: bool = False
    ) -> Tuple[bool, str]:
        """
        批量执行合并

        Returns:
            (success, message)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"开始批量合并，共 {len(configs)} 个表")
        logger.info(f"{'='*60}")

        all_success = True
        results = []

        for i, config in enumerate(configs, 1):
            logger.info(f"\n[{i}/{len(configs)}] 处理表: {config['table']}")

            success, msg = self.execute_merge(config, dry_run=dry_run)
            results.append({
                'table': config['table'],
                'success': success,
                'message': msg
            })

            if not success:
                all_success = False
                logger.error(f"❌ 合并失败: {msg}")

        logger.info(f"\n{'='*60}")
        logger.info("批量合并完成")
        logger.info(f"{'='*60}")

        for result in results:
            status = "✅" if result['success'] else "❌"
            logger.info(f"{status} {result['table']}: {result['message']}")

        if all_success:
            return True, f"全部 {len(configs)} 个表合并成功"
        else:
            failed = [r for r in results if not r['success']]
            return False, f"{len(failed)} 个表合并失败"

    def close(self):
        """关闭连接"""
        self.migrator.close()


def simple_field_merge(
    table_name: str,
    fields: Dict[str, str],
    default_values: Dict[str, Any] = None
) -> bool:
    """
    简单的字段合并函数

    Args:
        table_name: 表名
        fields: 字段定义 {'field_name': 'VARCHAR(50)', ...}
        default_values: 默认值 {'field_name': 'default', ...}

    Returns:
        是否成功
    """
    migrator = DataMigrator()

    try:
        for field_name, field_type in fields.items():
            default = default_values.get(field_name) if default_values else None
            success, msg = migrator.add_field_safe(table_name, field_name, field_type, default)

            if not success and "已存在" not in msg:
                logger.error(f"添加字段失败: {msg}")
                return False

        logger.info(f"✅ 表 {table_name} 字段合并完成")
        return True

    finally:
        migrator.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据合并迁移工具")
    parser.add_argument('--table', help='表名')
    parser.add_argument('--fields', help='字段定义 JSON，如 {"barcode":"VARCHAR(50)"}')
    parser.add_argument('--defaults', help='默认值 JSON，如 {"barcode":""}')
    parser.add_argument('--config-file', help='配置文件路径')
    parser.add_argument('--dry-run', action='store_true', help='预演模式')
    parser.add_argument('--backup', action='store_true', default=True, help='备份表')
    parser.add_argument('--interactive', action='store_true', help='交互模式')

    args = parser.parse_args()

    if args.interactive:
        print("\n" + "="*60)
        print("数据合并迁移工具 - 交互模式")
        print("="*60)

        table = input("请输入表名: ").strip()
        if not table:
            print("表名不能为空")
            sys.exit(1)

        print("\n输入要添加的字段（格式: 字段名 类型, 如: barcode VARCHAR(50)）")
        print("输入空行结束:")

        fields = {}
        while True:
            line = input().strip()
            if not line:
                break
            parts = line.split()
            if len(parts) >= 2:
                fields[parts[0]] = parts[1]

        if not fields:
            print("没有输入字段")
            sys.exit(1)

        print("\n是否设置默认值？(直接回车跳过)")

        defaults = {}
        for field in fields:
            val = input(f"{field} 的默认值: ").strip()
            if val:
                defaults[field] = val

        print(f"\n即将执行:")
        print(f"表名: {table}")
        print(f"添加字段: {fields}")
        print(f"默认值: {defaults}")

        confirm = input("\n确认执行? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("已取消")
            sys.exit(0)

        success = simple_field_merge(table, fields, defaults)
        sys.exit(0 if success else 1)

    if args.table and args.fields:
        import json
        fields = json.loads(args.fields)
        defaults = json.loads(args.defaults) if args.defaults else {}

        print(f"表名: {args.table}")
        print(f"字段: {fields}")
        print(f"默认值: {defaults}")

        if args.dry_run:
            print("\n⚠️ 预演模式")
            migrator = DataMigrator()
            schema = migrator.get_table_schema(args.table)
            current_fields = {f['Field'] for f in schema}

            for field, ftype in fields.items():
                if field in current_fields:
                    print(f"  - {field}: 已存在")
                else:
                    print(f"  + {field}: {ftype} (将添加)")

            migrator.close()
        else:
            success = simple_field_merge(args.table, fields, defaults)
            sys.exit(0 if success else 1)

    else:
        parser.print_help()
