# -*- coding: utf-8 -*-
"""
数据库结构对比工具
用于对比两个数据库或两个版本的表结构差异，生成：
1. 新增字段列表
2. 删除字段列表
3. 修改字段列表
4. 完整的迁移SQL脚本
"""
import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class FieldDefinition:
    """字段定义"""
    name: str
    type: str
    nullable: bool = True
    default: Optional[Any] = None
    comment: Optional[str] = None
    extra: Optional[str] = None


@dataclass
class TableSchema:
    """表结构"""
    table_name: str
    fields: List[FieldDefinition]
    primary_key: List[str]
    indexes: List[Dict]
    foreign_keys: List[Dict]


@dataclass
class SchemaDiff:
    """结构差异"""
    added_fields: List[Dict]
    removed_fields: List[Dict]
    modified_fields: List[Dict]
    unchanged_fields: List[str]


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


class SchemaComparator:
    """数据库结构对比器"""

    def __init__(self, db_config: Optional[Dict] = None):
        self.db_config = db_config or get_db_config()
        self._conn = None

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

    def get_table_schema(self, table_name: str) -> TableSchema:
        """获取表结构"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(f"DESCRIBE `{table_name}`")
        columns = cursor.fetchall()

        cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
        create_stmt = cursor.fetchone()["Create Table"]

        fields = []
        primary_key = []
        indexes = []
        foreign_keys = []

        for col in columns:
            field = FieldDefinition(
                name=col["Field"],
                type=col["Type"],
                nullable=(col["Null"] == "YES"),
                default=col["Default"],
                extra=col["Extra"]
            )
            fields.append(field)

            if col["Key"] == "PRI":
                primary_key.append(col["Field"])

        cursor.execute(f"""
            SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE, SEQ_IN_INDEX
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND INDEX_NAME != 'PRIMARY'
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """, (self.db_config["database"], table_name))

        stats = cursor.fetchall()
        index_map = {}
        for stat in stats:
            idx_name = stat["INDEX_NAME"]
            if idx_name not in index_map:
                index_map[idx_name] = {
                    "name": idx_name,
                    "unique": (stat["NON_UNIQUE"] == 0),
                    "columns": []
                }
            index_map[idx_name]["columns"].append(stat["COLUMN_NAME"])

        indexes = list(index_map.values())

        pk_fields = set(primary_key)
        for idx in indexes[:]:
            if set(idx["columns"]) == pk_fields and idx["unique"]:
                indexes.remove(idx)

        cursor.close()

        return TableSchema(
            table_name=table_name,
            fields=fields,
            primary_key=primary_key,
            indexes=indexes,
            foreign_keys=foreign_keys
        )

    def get_all_tables(self) -> List[str]:
        """获取所有表名"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """, (self.db_config["database"],))
        tables = [row["TABLE_NAME"] for row in cursor.fetchall()]
        cursor.close()
        return tables

    def compare_fields(
        self,
        current_fields: List[FieldDefinition],
        expected_fields: List[FieldDefinition]
    ) -> SchemaDiff:
        """对比字段"""
        current_map = {f.name: f for f in current_fields}
        expected_map = {f.name: f for f in expected_fields}

        added = []
        removed = []
        modified = []
        unchanged = []

        for name, field in expected_map.items():
            if name not in current_map:
                added.append({
                    "field": name,
                    "definition": asdict(field)
                })
            else:
                old_field = current_map[name]
                is_same = (
                    old_field.type.upper() == field.type.upper() and
                    old_field.nullable == field.nullable and
                    old_field.default == field.default
                )
                if not is_same:
                    modified.append({
                        "field": name,
                        "old": asdict(old_field),
                        "new": asdict(field)
                    })
                else:
                    unchanged.append(name)

        for name in current_map:
            if name not in expected_map:
                removed.append({
                    "field": name,
                    "type": current_map[name].type,
                    "nullable": current_map[name].nullable,
                    "default": current_map[name].default
                })

        return SchemaDiff(
            added_fields=added,
            removed_fields=removed,
            modified_fields=modified,
            unchanged_fields=unchanged
        )

    def generate_migration_sql(
        self,
        table_name: str,
        diff: SchemaDiff,
        add_after: Optional[str] = None
    ) -> tuple:
        """
        生成迁移SQL

        Returns:
            (sql_statements, rollback_statements)
        """
        sqls = []
        rollbacks = []

        for item in diff.added_fields:
            field = item["definition"]
            sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{field['name']}` {field['type']}"
            if not field["nullable"]:
                sql += " NOT NULL"
            if field["default"] is not None:
                if isinstance(field["default"], str):
                    sql += f" DEFAULT '{field['default']}'"
                else:
                    sql += f" DEFAULT {field['default']}"
            if add_after:
                sql += f" AFTER `{add_after}`"
                add_after = field["name"]
            else:
                add_after = field["name"]
            sqls.append(sql)
            rollbacks.append(f"ALTER TABLE `{table_name}` DROP COLUMN `{field['name']}`")

        for item in diff.removed_fields:
            field_name = item["field"]
            field_type = item["type"]
            field_nullable = item["nullable"]
            field_default = item["default"]

            add_back = f"ALTER TABLE `{table_name}` ADD COLUMN `{field_name}` {field_type}"
            if not field_nullable:
                add_back += " NOT NULL"
            if field_default is not None:
                if isinstance(field_default, str):
                    add_back += f" DEFAULT '{field_default}'"
                else:
                    add_back += f" DEFAULT {field_default}"

            sqls.append(f"ALTER TABLE `{table_name}` DROP COLUMN `{field_name}`")
            rollbacks.append(add_back)

        for item in diff.modified_fields:
            field_name = item["field"]
            new_def = item["new"]

            sql = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{field_name}` {new_def['type']}"
            if not new_def["nullable"]:
                sql += " NOT NULL"
            if new_def["default"] is not None:
                if isinstance(new_def["default"], str):
                    sql += f" DEFAULT '{new_def['default']}'"
                else:
                    sql += f" DEFAULT {new_def['default']}"
            sqls.append(sql)

            old_def = item["old"]
            rollback = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{field_name}` {old_def['type']}"
            if not old_def["nullable"]:
                rollback += " NOT NULL"
            if old_def["default"] is not None:
                if isinstance(old_def["default"], str):
                    rollback += f" DEFAULT '{old_def['default']}'"
                else:
                    rollback += f" DEFAULT {old_def['default']}"
            rollbacks.append(rollback)

        return sqls, rollbacks

    def export_schema_to_dict(self, table_name: str) -> Dict:
        """导出表结构为字典"""
        schema = self.get_table_schema(table_name)
        return {
            "table_name": schema.table_name,
            "fields": [asdict(f) for f in schema.fields],
            "primary_key": schema.primary_key,
            "indexes": schema.indexes,
            "foreign_keys": schema.foreign_keys
        }

    def export_all_schemas(self) -> Dict[str, Dict]:
        """导出所有表结构"""
        schemas = {}
        for table in self.get_all_tables():
            schemas[table] = self.export_schema_to_dict(table)
        return schemas

    def save_schema_snapshot(self, file_path: str):
        """保存结构快照"""
        schemas = self.export_all_schemas()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(schemas, f, ensure_ascii=False, indent=2)
        logger.info(f"结构快照已保存: {file_path}")

    def load_schema_snapshot(self, file_path: str) -> Dict[str, Dict]:
        """加载结构快照"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)


class DualSchemaComparator:
    """双数据库结构对比器"""

    def __init__(
        self,
        source_config: Optional[Dict] = None,
        target_config: Optional[Dict] = None
    ):
        self.source = SchemaComparator(source_config)
        self.target = SchemaComparator(target_config)

    def compare_table(self, table_name: str) -> SchemaDiff:
        """对比指定表"""
        source_schema = self.source.get_table_schema(table_name)
        target_schema = self.target.get_table_schema(table_name)
        return self.source.compare_fields(source_schema.fields, target_schema.fields)

    def compare_all_tables(self) -> Dict[str, SchemaDiff]:
        """对比所有表"""
        source_tables = set(self.source.get_all_tables())
        target_tables = set(self.target.get_all_tables())

        result = {}

        common_tables = source_tables & target_tables
        for table in common_tables:
            result[table] = self.compare_table(table)

        return result

    def generate_full_migration_report(self) -> Dict:
        """生成完整的迁移报告"""
        source_tables = set(self.source.get_all_tables())
        target_tables = set(self.target.get_all_tables())

        common_tables = source_tables & target_tables
        only_in_source = source_tables - target_tables
        only_in_target = target_tables - source_tables

        all_diffs = self.compare_all_tables()

        report = {
            "generated_at": datetime.now().isoformat(),
            "source_database": self.source.db_config["database"],
            "target_database": self.target.db_config["database"],
            "summary": {
                "total_tables": len(target_tables),
                "tables_to_create": len(only_in_target),
                "tables_to_drop": len(only_in_source),
                "tables_to_modify": len([t for t, d in all_diffs.items()
                                        if d.added_fields or d.removed_fields or d.modified_fields])
            },
            "tables_only_in_source": list(only_in_source),
            "tables_only_in_target": list(only_in_target),
            "table_differences": {}
        }

        for table, diff in all_diffs.items():
            if diff.added_fields or diff.removed_fields or diff.modified_fields:
                sqls, rollbacks = self.source.generate_migration_sql(table, diff)
                report["table_differences"][table] = {
                    "added_fields": diff.added_fields,
                    "removed_fields": diff.removed_fields,
                    "modified_fields": diff.modified_fields,
                    "unchanged_fields": diff.unchanged_fields,
                    "migration_sql": sqls,
                    "rollback_sql": rollbacks
                }

        return report


def print_diff_report(diff: SchemaDiff):
    """打印差异报告"""
    print("\n" + "=" * 60)

    if diff.added_fields:
        print("\n📗 新增字段:")
        for item in diff.added_fields:
            print(f"  + {item['field']} ({item['definition']['type']})")
            if item['definition'].get('comment'):
                print(f"    说明: {item['definition']['comment']}")

    if diff.removed_fields:
        print("\n📕 删除字段:")
        for item in diff.removed_fields:
            print(f"  - {item['field']} ({item['type']})")

    if diff.modified_fields:
        print("\n📙 修改字段:")
        for item in diff.modified_fields:
            print(f"  ~ {item['field']}")
            print(f"    原: {item['old']['type']} "
                  f"{'NOT NULL' if not item['old']['nullable'] else 'NULL'}")
            print(f"    新: {item['new']['type']} "
                  f"{'NOT NULL' if not item['new']['nullable'] else 'NULL'}")

    if diff.unchanged_fields:
        print(f"\n📗 未变化: {', '.join(diff.unchanged_fields)}")


def export_migration_script(report: Dict, output_file: str):
    """导出迁移脚本"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- 数据库迁移脚本\n")
        f.write(f"-- 生成时间: {report['generated_at']}\n")
        f.write(f"-- 源数据库: {report['source_database']}\n")
        f.write(f"-- 目标数据库: {report['target_database']}\n")
        f.write("-- " + "=" * 58 + "\n\n")

        f.write("-- 迁移摘要\n")
        f.write(f"-- 需要创建的表: {report['summary']['tables_to_create']}\n")
        f.write(f"-- 需要删除的表: {report['summary']['tables_to_drop']}\n")
        f.write(f"-- 需要修改的表: {report['summary']['tables_to_modify']}\n\n")

        if report.get('tables_only_in_target'):
            f.write("-- 需要新建的表:\n")
            for table in report['tables_only_in_target']:
                f.write(f"--   - {table}\n")
            f.write("\n")

        if report.get('tables_only_in_source'):
            f.write("-- 警告: 以下表在源数据库中存在，目标数据库中没有:\n")
            for table in report['tables_only_in_source']:
                f.write(f"--   - {table}\n")
            f.write("-- 如果继续迁移，这些表的数据将丢失！\n\n")

        f.write("-- " + "=" * 58 + "\n")
        f.write("-- 迁移SQL\n")
        f.write("-- " + "=" * 58 + "\n\n")

        for table, diff in report.get('table_differences', {}).items():
            f.write(f"\n-- 表: {table}\n")
            f.write("-- " + "-" * 40 + "\n")

            if diff.get('migration_sql'):
                f.write("-- 执行以下SQL:\n")
                for sql in diff['migration_sql']:
                    f.write(f"{sql};\n")

                f.write("\n-- 回滚SQL (如需回滚，执行以下SQL):\n")
                for sql in diff.get('rollback_sql', []):
                    f.write(f"{sql};\n")

    logger.info(f"迁移脚本已导出: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="数据库结构对比工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--source-config', help='源数据库配置文件(JSON)')
    parser.add_argument('--target-config', help='目标数据库配置文件(JSON)')
    parser.add_argument('--source-db', help='源数据库名')
    parser.add_argument('--target-db', help='目标数据库名')
    parser.add_argument('--table', help='对比指定表')
    parser.add_argument('--all-tables', action='store_true', help='对比所有表')
    parser.add_argument('--export-snapshot', metavar='FILE', help='导出结构快照')
    parser.add_argument('--load-snapshot', metavar='FILE', help='加载结构快照进行对比')
    parser.add_argument('--output', '-o', metavar='FILE', help='输出文件')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    if args.export_snapshot:
        comparator = SchemaComparator()
        comparator.save_schema_snapshot(args.export_snapshot)
        comparator.close()
        return

    if args.load_snapshot:
        comparator = SchemaComparator()
        snapshot = comparator.load_schema_snapshot(args.load_snapshot)

        print("快照中的表:")
        for table in sorted(snapshot.keys()):
            print(f"  - {table}: {len(snapshot[table]['fields'])} 字段")

        comparator.close()
        return

    if args.table:
        comparator = SchemaComparator()
        diff = comparator.compare_table(args.table)
        print_diff_report(diff)
        comparator.close()
        return

    if args.all_tables:
        comparator = SchemaComparator()
        all_diffs = comparator.compare_all_tables()

        modify_count = 0
        for table, diff in all_diffs.items():
            if diff.added_fields or diff.removed_fields or diff.modified_fields:
                modify_count += 1
                print_diff_report(diff)

        print(f"\n共有 {len(all_diffs)} 个表，其中 {modify_count} 个有变化")
        comparator.close()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
