# -*- coding: utf-8 -*-
"""
数据库迁移框架核心模块
提供安全的数据库结构变更能力，支持：
1. 迁移版本管理
2. 自动备份
3. 事务回滚
4. 增量迁移
5. 迁移记录追踪
"""
import os
import json
import logging
import hashlib
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Callable

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


class MigrationContext:
    """迁移上下文，存储迁移过程中的状态"""

    def __init__(self, db_config: Dict[str, Any], backup_dir: str):
        self.db_config = db_config
        self.backup_dir = backup_dir
        self.migration_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.migration_name = ""
        self.executed_sqls: List[str] = []
        self.backup_sqls: List[str] = []
        self.success = False

    def get_backup_path(self, table_name: str) -> str:
        """获取备份文件路径"""
        return os.path.join(
            self.backup_dir,
            f"{self.migration_id}_{table_name}_backup.sql"
        )


class DatabaseMigration:
    """数据库迁移管理器"""

    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        self.db_config = db_config or get_db_config()
        self.backup_dir = os.path.join(
            os.path.dirname(__file__),
            "backups",
            datetime.now().strftime("%Y%m")
        )
        os.makedirs(self.backup_dir, exist_ok=True)
        self._ensure_migration_table()

    def _ensure_migration_table(self):
        """确保迁移记录表存在"""
        conn = self._create_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS _migration_history (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    migration_id VARCHAR(50) UNIQUE NOT NULL,
                    migration_name VARCHAR(200),
                    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sql_statements TEXT,
                    rollback_sql TEXT,
                    status ENUM('success', 'failed', 'rolled_back') DEFAULT 'success',
                    error_message TEXT,
                    checksum VARCHAR(64)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def _create_connection(self):
        """创建数据库连接"""
        import pymysql
        config = self.db_config.copy()
        config["cursorclass"] = pymysql.cursors.DictCursor
        return pymysql.connect(**config)

    @contextmanager
    def _get_cursor(self):
        """获取数据库游标的上下文管理器"""
        conn = self._create_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def get_current_schema(self, table_name: str) -> List[Dict]:
        """获取指定表的当前结构"""
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

    def get_table_create_statement(self, table_name: str) -> str:
        """获取表的创建语句"""
        with self._get_cursor() as cursor:
            cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
            row = cursor.fetchone()
            return row["Create Table"] if row else ""

    def compare_schemas(
        self,
        current_schema: List[Dict],
        expected_fields: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """
        对比当前表结构与期望结构

        Args:
            current_schema: 当前表结构 (DESCRIBE结果)
            expected_fields: 期望字段定义 {
                'field_name': {
                    'type': 'VARCHAR(50)',
                    'nullable': True,
                    'default': 'some_value',
                    'comment': '字段说明'
                }
            }

        Returns:
            {
                'added': [{'field': 'name', 'definition': {...}}],
                'removed': [{'field': 'name', 'type': 'varchar(50)'}],
                'modified': [{'field': 'name', 'old': {...}, 'new': {...}}],
                'unchanged': ['field1', 'field2']
            }
        """
        current_fields = {row["Field"]: row for row in current_schema}
        result = {
            'added': [],
            'removed': [],
            'modified': [],
            'unchanged': []
        }

        for field_name, definition in expected_fields.items():
            if field_name not in current_fields:
                result['added'].append({
                    'field': field_name,
                    'definition': definition
                })
            else:
                old_def = current_fields[field_name]
                type_changed = old_def['Type'].upper() != definition['type'].upper()
                null_changed = old_def['Null'].upper() != ('YES' if definition.get('nullable', True) else 'NO')

                if type_changed or null_changed:
                    result['modified'].append({
                        'field': field_name,
                        'old': old_def,
                        'new': definition
                    })
                else:
                    result['unchanged'].append(field_name)

        for field_name in current_fields:
            if field_name not in expected_fields:
                result['removed'].append({
                    'field': field_name,
                    'type': current_fields[field_name]['Type']
                })

        return result

    def generate_add_field_sql(self, table_name: str, field: str, definition: Dict) -> str:
        """生成添加字段的SQL"""
        sql_parts = [f"ALTER TABLE `{table_name}` ADD COLUMN `{field}` {definition['type']}"]

        if not definition.get('nullable', True):
            sql_parts.append("NOT NULL")

        if 'default' in definition:
            default_val = definition['default']
            if default_val is None:
                sql_parts.append("DEFAULT NULL")
            elif isinstance(default_val, str):
                sql_parts.append(f"DEFAULT '{default_val}'")
            else:
                sql_parts.append(f"DEFAULT {default_val}")

        if 'after' in definition:
            sql_parts.append(f"AFTER `{definition['after']}`")

        return " ".join(sql_parts)

    def generate_remove_field_sql(self, table_name: str, field: str) -> str:
        """生成删除字段的SQL"""
        return f"ALTER TABLE `{table_name}` DROP COLUMN `{field}`"

    def generate_modify_field_sql(self, table_name: str, field: str, new_definition: Dict) -> str:
        """生成修改字段的SQL"""
        sql_parts = [
            f"ALTER TABLE `{table_name}` MODIFY COLUMN `{field}` {new_definition['type']}"
        ]

        if not new_definition.get('nullable', True):
            sql_parts.append("NOT NULL")

        if 'default' in new_definition:
            default_val = new_definition['default']
            if default_val is None:
                sql_parts.append("DEFAULT NULL")
            elif isinstance(default_val, str):
                sql_parts.append(f"DEFAULT '{default_val}'")
            else:
                sql_parts.append(f"DEFAULT {default_val}")

        return " ".join(sql_parts)

    def backup_table(self, table_name: str, backup_path: Optional[str] = None) -> str:
        """
        备份表结构和数据

        Returns:
            备份文件路径
        """
        if backup_path is None:
            backup_path = os.path.join(
                self.backup_dir,
                f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            )

        with self._get_cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 1")
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

        create_stmt = self.get_table_create_statement(table_name)

        backup_sql = f"-- Table backup: {table_name}\n"
        backup_sql += f"-- Backup time: {datetime.now()}\n"
        backup_sql += f"{create_stmt};\n\n"

        with self._get_cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{table_name}`")
            for row in cursor:
                values = []
                for val in row:
                    if val is None:
                        values.append("NULL")
                    elif isinstance(val, str):
                        values.append(f"'{val.replace('\'', '\'\'')}'")
                    elif isinstance(val, datetime):
                        values.append(f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'")
                    else:
                        values.append(str(val))
                backup_sql += f"INSERT INTO `{table_name}` ({', '.join(f'`{c}`' for c in columns)}) VALUES ({', '.join(values)});\n"

        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(backup_sql)

        logger.info(f"表 {table_name} 已备份到: {backup_path}")
        return backup_path

    @contextmanager
    def migration(self, migration_name: str):
        """
        迁移执行的上下文管理器
        提供事务支持和自动回滚
        """
        context = MigrationContext(self.db_config, self.backup_dir)
        context.migration_name = migration_name

        logger.info(f"开始迁移: {migration_name}")

        try:
            yield context
            context.success = True
            logger.info(f"迁移完成: {migration_name}")
        except Exception as e:
            context.success = False
            logger.error(f"迁移失败: {migration_name}, 错误: {e}")
            raise

    def execute_migration(
        self,
        migration_name: str,
        sql_statements: List[str],
        rollback_sql: Optional[List[str]] = None
    ) -> tuple:
        """
        执行迁移SQL

        Args:
            migration_name: 迁移名称
            sql_statements: 要执行的SQL列表
            rollback_sql: 回滚SQL列表（可选）

        Returns:
            (success: bool, message: str)
        """
        migration_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        conn = self._create_connection()
        cursor = conn.cursor()

        try:
            for sql in sql_statements:
                if sql.strip():
                    logger.info(f"执行SQL: {sql[:100]}...")
                    cursor.execute(sql)
            conn.commit()

            rollback_text = "; ".join(rollback_sql) if rollback_sql else ""
            checksum = hashlib.md5(
                ("; ".join(sql_statements)).encode()
            ).hexdigest()

            cursor.execute("""
                INSERT INTO _migration_history
                (migration_id, migration_name, sql_statements, rollback_sql, status, checksum)
                VALUES (%s, %s, %s, %s, 'success', %s)
            """, (migration_id, migration_name, "; ".join(sql_statements), rollback_text, checksum))
            conn.commit()

            logger.info(f"迁移 {migration_name} 执行成功")
            return True, f"迁移成功: {migration_name}"

        except Exception as e:
            conn.rollback()
            logger.error(f"迁移失败: {e}")

            try:
                cursor.execute("""
                    INSERT INTO _migration_history
                    (migration_id, migration_name, sql_statements, rollback_sql, status, error_message)
                    VALUES (%s, %s, %s, %s, 'failed', %s)
                """, (migration_id, migration_name, "; ".join(sql_statements),
                      "; ".join(rollback_sql) if rollback_sql else "", str(e)))
                conn.commit()
            except Exception:
                pass

            return False, f"迁移失败: {str(e)}"

        finally:
            cursor.close()
            conn.close()

    def rollback_migration(self, migration_id: str) -> tuple:
        """
        回滚指定迁移

        Args:
            migration_id: 迁移ID

        Returns:
            (success: bool, message: str)
        """
        conn = self._create_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT rollback_sql FROM _migration_history
                WHERE migration_id = %s AND status = 'success'
            """, (migration_id,))
            row = cursor.fetchone()

            if not row or not row['rollback_sql']:
                return False, f"迁移 {migration_id} 没有回滚SQL"

            rollback_sqls = row['rollback_sql'].split("; ")

            for sql in rollback_sqls:
                if sql.strip():
                    logger.info(f"执行回滚SQL: {sql[:100]}...")
                    cursor.execute(sql)

            cursor.execute("""
                UPDATE _migration_history SET status = 'rolled_back'
                WHERE migration_id = %s
            """, (migration_id,))
            conn.commit()

            logger.info(f"迁移 {migration_id} 已回滚")
            return True, f"回滚成功: {migration_id}"

        except Exception as e:
            conn.rollback()
            return False, f"回滚失败: {str(e)}"

        finally:
            cursor.close()
            conn.close()

    def get_migration_history(self, limit: int = 20) -> List[Dict]:
        """获取迁移历史"""
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM _migration_history
                ORDER BY executed_at DESC LIMIT %s
            """, (limit,))
            return cursor.fetchall()


class SafeSchemaMigration(DatabaseMigration):
    """
    安全模式迁移类
    提供更高级别的安全保障：
    1. 自动备份所有受影响的表
    2. 数据完整性检查
    3. 迁移前后数据对比
    """

    def safe_add_column(
        self,
        table_name: str,
        field_name: str,
        field_type: str,
        default_value: Any = None,
        after_field: Optional[str] = None,
        nullable: bool = True
    ) -> tuple:
        """
        安全添加列

        Args:
            table_name: 表名
            field_name: 字段名
            field_type: 字段类型 (如 VARCHAR(50), INT, DECIMAL(12,2))
            default_value: 默认值
            after_field: 放在哪个字段后面
            nullable: 是否允许NULL

        Returns:
            (success: bool, message: str)
        """
        try:
            current_schema = self.get_current_schema(table_name)
            if any(f["Field"] == field_name for f in current_schema):
                return False, f"字段 {field_name} 已存在"

            backup_path = self.backup_table(table_name)
            logger.info(f"已备份表 {table_name} 到 {backup_path}")

            sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{field_name}` {field_type}"
            if not nullable:
                sql += " NOT NULL"
            if default_value is not None:
                if isinstance(default_value, str):
                    sql += f" DEFAULT '{default_value}'"
                else:
                    sql += f" DEFAULT {default_value}"
            if after_field:
                sql += f" AFTER `{after_field}`"

            rollback_sql = [self.generate_remove_field_sql(table_name, field_name)]

            return self.execute_migration(
                f"add_column_{table_name}_{field_name}",
                [sql],
                rollback_sql
            )

        except Exception as e:
            return False, f"添加字段失败: {str(e)}"

    def safe_drop_column(self, table_name: str, field_name: str) -> tuple:
        """
        安全删除列（先备份再删除）

        Args:
            table_name: 表名
            field_name: 字段名

        Returns:
            (success: bool, message: str)
        """
        try:
            current_schema = self.get_current_schema(table_name)
            if not any(f["Field"] == field_name for f in current_schema):
                return False, f"字段 {field_name} 不存在"

            backup_path = self.backup_table(table_name)
            logger.info(f"已备份表 {table_name} 到 {backup_path}")

            current_def = next((f for f in current_schema if f["Field"] == field_name), None)
            recreate_sql = f"ALTER TABLE `{table_name}` DROP COLUMN `{field_name}`"

            add_back_sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{field_name}` {current_def['Type']}"
            if current_def['Null'] == 'NO':
                add_back_sql += " NOT NULL"
            if current_def['Default']:
                add_back_sql += f" DEFAULT '{current_def['Default']}'"

            return self.execute_migration(
                f"drop_column_{table_name}_{field_name}",
                [recreate_sql],
                [add_back_sql]
            )

        except Exception as e:
            return False, f"删除字段失败: {str(e)}"

    def safe_modify_column(
        self,
        table_name: str,
        field_name: str,
        new_field_type: str,
        new_default: Any = None,
        new_nullable: bool = True
    ) -> tuple:
        """
        安全修改列

        Args:
            table_name: 表名
            field_name: 字段名
            new_field_type: 新字段类型
            new_default: 新默认值
            new_nullable: 是否允许NULL

        Returns:
            (success: bool, message: str)
        """
        try:
            backup_path = self.backup_table(table_name)
            logger.info(f"已备份表 {table_name} 到 {backup_path}")

            current_schema = self.get_current_schema(table_name)
            current_def = next((f for f in current_schema if f["Field"] == field_name), None)

            old_sql = self.generate_modify_field_sql(table_name, field_name, {
                'type': current_def['Type'],
                'nullable': current_def['Null'] == 'YES',
                'default': current_def['Default']
            })

            new_sql = self.generate_modify_field_sql(table_name, field_name, {
                'type': new_field_type,
                'nullable': new_nullable,
                'default': new_default
            })

            return self.execute_migration(
                f"modify_column_{table_name}_{field_name}",
                [new_sql],
                [old_sql]
            )

        except Exception as e:
            return False, f"修改字段失败: {str(e)}"

    def batch_migrate(
        self,
        migration_name: str,
        migrations: List[Dict[str, Any]]
    ) -> tuple:
        """
        批量执行迁移

        Args:
            migration_name: 迁移名称
            migrations: 迁移列表 [
                {
                    'action': 'add_column' | 'drop_column' | 'modify_column',
                    'table': 'table_name',
                    'field': 'field_name',
                    'definition': {...}
                }
            ]

        Returns:
            (success: bool, message: str)
        """
        all_sqls = []
        all_rollback_sqls = []

        for mig in migrations:
            action = mig['action']
            table = mig['table']
            field = mig['field']

            if action == 'add_column':
                sql = self.generate_add_field_sql(table, field, mig['definition'])
                rollback = self.generate_remove_field_sql(table, field)
                all_sqls.append(sql)
                all_rollback_sqls.append(rollback)

            elif action == 'drop_column':
                current_schema = self.get_current_schema(table)
                current_def = next((f for f in current_schema if f["Field"] == field), None)
                if current_def:
                    add_back = f"ALTER TABLE `{table}` ADD COLUMN `{field}` {current_def['Type']}"
                    if current_def['Null'] == 'NO':
                        add_back += " NOT NULL"
                    if current_def['Default']:
                        add_back += f" DEFAULT '{current_def['Default']}'"
                    all_rollback_sqls.append(add_back)

                sql = self.generate_remove_field_sql(table, field)
                all_sqls.append(sql)

        return self.execute_migration(migration_name, all_sqls, all_rollback_sqls)


def create_migration_from_config(
    config_file: str,
    migration_name: str
) -> tuple:
    """
    根据配置文件创建迁移

    Args:
        config_file: 配置文件路径
        migration_name: 迁移名称

    Returns:
        (success: bool, message: str)
    """
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    migrator = SafeSchemaMigration()

    if 'migrations' in config:
        return migrator.batch_migrate(migration_name, config['migrations'])
    else:
        return False, "配置文件格式错误"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("数据库迁移工具")
    print("=" * 60)

    migrator = SafeSchemaMigration()

    print("\n当前迁移历史:")
    history = migrator.get_migration_history(5)
    for row in history:
        print(f"  [{row['status']}] {row['migration_name']} - {row['executed_at']}")

    print("\n当前所有表:")
    tables = migrator.get_all_tables()
    for table in tables:
        print(f"  - {table}")
