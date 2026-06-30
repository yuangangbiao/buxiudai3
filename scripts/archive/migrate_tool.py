# -*- coding: utf-8 -*-
"""
数据库迁移执行工具 - 命令行界面
用于执行数据库表结构变更，支持：
1. 查看当前数据库结构
2. 预览迁移SQL
3. 执行安全迁移
4. 回滚迁移
5. 迁移历史查看
"""
import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(__file__))

from database_migration import SafeSchemaMigration, create_migration_from_config
from models.database import get_connection

logger = logging.getLogger(__name__)


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_success(msg: str):
    """打印成功消息"""
    print(f"\n✅ 成功: {msg}")


def print_error(msg: str):
    """打印错误消息"""
    print(f"\n❌ 错误: {msg}")


def print_warning(msg: str):
    """打印警告消息"""
    print(f"\n⚠️  警告: {msg}")


def cmd_list_tables(migrator: SafeSchemaMigration):
    """列出所有表"""
    print_header("数据库所有表")

    tables = migrator.get_all_tables()
    for i, table in enumerate(tables, 1):
        print(f"  {i}. {table}")

    print(f"\n共 {len(tables)} 个表")


def cmd_show_table(migrator: SafeSchemaMigration, table_name: str):
    """显示表结构"""
    print_header(f"表结构: {table_name}")

    schema = migrator.get_current_schema(table_name)

    print(f"\n{'字段名':<20} {'类型':<20} {'可空':<8} {'默认':<15} {'额外'}")
    print("-" * 80)

    for col in schema:
        print(f"{col['Field']:<20} {col['Type']:<20} {col['Null']:<8} "
              f"{str(col['Default']) if col['Default'] else 'None':<15} {col['Extra']}")


def cmd_compare(migrator: SafeSchemaMigration, table_name: str, expected_fields: dict):
    """对比表结构"""
    print_header(f"结构对比: {table_name}")

    current = migrator.get_current_schema(table_name)
    diff = migrator.compare_schemas(current, expected_fields)

    if diff['added']:
        print("\n📗 将新增的字段:")
        for item in diff['added']:
            print(f"  + {item['field']} ({item['definition']['type']})")
            if 'comment' in item['definition']:
                print(f"    说明: {item['definition']['comment']}")

    if diff['removed']:
        print("\n📕 将删除的字段:")
        for item in diff['removed']:
            print(f"  - {item['field']} ({item['type']})")
        print_warning("删除字段会丢失数据，请确认是否继续！")

    if diff['modified']:
        print("\n📙 将修改的字段:")
        for item in diff['modified']:
            print(f"  ~ {item['field']}")
            print(f"    原: {item['old']['Type']} {'NOT NULL' if item['old']['Null'] == 'NO' else ''}")
            print(f"    新: {item['new']['type']} {'NOT NULL' if not item['new'].get('nullable', True) else ''}")

    if diff['unchanged']:
        print(f"\n📗 未变化的字段: {', '.join(diff['unchanged'])}")

    return diff


def cmd_add_column(migrator: SafeSchemaMigration, table: str, field: str,
                   field_type: str, default_value=None, nullable: bool = True,
                   after: str = None, dry_run: bool = False):
    """添加列"""
    print_header("添加字段")

    print(f"表名: {table}")
    print(f"字段: {field}")
    print(f"类型: {field_type}")
    print(f"可空: {'是' if nullable else '否'}")
    if default_value is not None:
        print(f"默认: {default_value}")
    if after:
        print(f"位置: 在 {after} 之后")

    if dry_run:
        print_warning("这是预演模式，不会实际执行")
        expected = {field: {'type': field_type, 'nullable': nullable, 'default': default_value}}
        diff = cmd_compare(migrator, table, {**dict(migrator.get_current_schema(table).field), field: expected[field]})
        return

    confirm = input("\n确认执行? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("已取消")
        return

    success, msg = migrator.safe_add_column(
        table, field, field_type,
        default_value=default_value,
        nullable=nullable,
        after_field=after
    )

    if success:
        print_success(msg)
    else:
        print_error(msg)


def cmd_drop_column(migrator: SafeSchemaMigration, table: str, field: str,
                    dry_run: bool = False):
    """删除列"""
    print_header("删除字段")

    print(f"表名: {table}")
    print(f"字段: {field}")

    schema = migrator.get_current_schema(table)
    field_info = next((f for f in schema if f['Field'] == field), None)
    if field_info:
        print(f"当前类型: {field_info['Type']}")
        print(f"默认值: {field_info['Default']}")

    if dry_run:
        print_warning("这是预演模式，不会实际执行")
        return

    print_warning("删除字段会永久丢失数据！")
    confirm = input("\n确认删除? 请输入 'yes' 确认: ").strip().lower()
    if confirm != 'yes':
        print("已取消")
        return

    success, msg = migrator.safe_drop_column(table, field)

    if success:
        print_success(msg)
    else:
        print_error(msg)


def cmd_modify_column(migrator: SafeSchemaMigration, table: str, field: str,
                      new_type: str, new_default=None, new_nullable: bool = True,
                      dry_run: bool = False):
    """修改列"""
    print_header("修改字段")

    print(f"表名: {table}")
    print(f"字段: {field}")
    print(f"新类型: {new_type}")
    print(f"新默认值: {new_default}")
    print(f"新可空: {'是' if new_nullable else '否'}")

    schema = migrator.get_current_schema(table)
    field_info = next((f for f in schema if f['Field'] == field), None)
    if field_info:
        print(f"\n当前定义:")
        print(f"  类型: {field_info['Type']}")
        print(f"  可空: {field_info['Null']}")
        print(f"  默认: {field_info['Default']}")

    if dry_run:
        print_warning("这是预演模式，不会实际执行")
        return

    confirm = input("\n确认执行? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("已取消")
        return

    success, msg = migrator.safe_modify_column(
        table, field, new_type,
        new_default=new_default,
        new_nullable=new_nullable
    )

    if success:
        print_success(msg)
    else:
        print_error(msg)


def cmd_execute_file(migrator: SafeSchemaMigration, config_file: str):
    """执行配置文件中的迁移"""
    print_header("执行迁移文件")

    print(f"配置文件: {config_file}")

    if not os.path.exists(config_file):
        print_error(f"文件不存在: {config_file}")
        return

    migration_name = input("输入迁移名称: ").strip()
    if not migration_name:
        print_error("迁移名称不能为空")
        return

    confirm = input("\n确认执行? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("已取消")
        return

    success, msg = create_migration_from_config(config_file, migration_name)

    if success:
        print_success(msg)
    else:
        print_error(msg)


def cmd_rollback(migrator: SafeSchemaMigration, migration_id: str = None):
    """回滚迁移"""
    print_header("回滚迁移")

    if not migration_id:
        print("最近的迁移记录:")
        history = migrator.get_migration_history(10)

        for row in history:
            status_icon = "✅" if row['status'] == 'success' else "❌"
            print(f"  {status_icon} {row['migration_id']} - {row['migration_name']}")

        migration_id = input("\n输入要回滚的迁移ID: ").strip()

    if not migration_id:
        print_error("迁移ID不能为空")
        return

    print_warning(f"回滚迁移: {migration_id}")
    confirm = input("确认回滚? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("已取消")
        return

    success, msg = migrator.rollback_migration(migration_id)

    if success:
        print_success(msg)
    else:
        print_error(msg)


def cmd_history(migrator: SafeSchemaMigration, limit: int = 20):
    """查看迁移历史"""
    print_header("迁移历史")

    history = migrator.get_migration_history(limit)

    print(f"\n{'ID':<20} {'名称':<30} {'状态':<10} {'时间':<20}")
    print("-" * 80)

    for row in history:
        status = row['status']
        if status == 'success':
            status = "✅ 成功"
        elif status == 'failed':
            status = "❌ 失败"
        else:
            status = "↩️ 已回滚"

        print(f"{row['migration_id']:<20} {row['migration_name']:<30} {status:<10} "
              f"{str(row['executed_at']):<20}")


def cmd_backup_table(migrator: SafeSchemaMigration, table_name: str):
    """备份表"""
    print_header("备份表")

    print(f"表名: {table_name}")

    confirm = input("\n确认备份? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("已取消")
        return

    try:
        backup_path = migrator.backup_table(table_name)
        print_success(f"备份完成: {backup_path}")
    except Exception as e:
        print_error(f"备份失败: {str(e)}")


def interactive_mode():
    """交互式模式"""
    migrator = SafeSchemaMigration()

    print_header("数据库迁移工具 - 交互式模式")

    while True:
        print("\n" + "-" * 40)
        print("1. 列出所有表")
        print("2. 查看表结构")
        print("3. 添加字段")
        print("4. 删除字段")
        print("5. 修改字段")
        print("6. 执行迁移文件")
        print("7. 回滚迁移")
        print("8. 查看迁移历史")
        print("9. 备份表")
        print("0. 退出")
        print("-" * 40)

        choice = input("\n选择操作 (0-9): ").strip()

        if choice == '1':
            cmd_list_tables(migrator)

        elif choice == '2':
            table = input("输入表名: ").strip()
            if table:
                cmd_show_table(migrator, table)

        elif choice == '3':
            table = input("表名: ").strip()
            field = input("字段名: ").strip()
            ftype = input("类型 (如 VARCHAR(50)): ").strip()
            nullable = input("可空 (yes/no, 默认yes): ").strip().lower() != 'no'
            default = input("默认值 (直接回车跳过): ").strip()
            after = input("在哪个字段后 (直接回车追加): ").strip()
            cmd_add_column(migrator, table, field, ftype,
                          default_value=default if default else None,
                          nullable=nullable,
                          after=after if after else None)

        elif choice == '4':
            table = input("表名: ").strip()
            field = input("字段名: ").strip()
            if table and field:
                cmd_drop_column(migrator, table, field)

        elif choice == '5':
            table = input("表名: ").strip()
            field = input("字段名: ").strip()
            new_type = input("新类型: ").strip()
            nullable = input("可空 (yes/no, 默认yes): ").strip().lower() != 'no'
            default = input("新默认值 (直接回车跳过): ").strip()
            cmd_modify_column(migrator, table, field, new_type,
                             new_default=default if default else None,
                             new_nullable=nullable)

        elif choice == '6':
            config_file = input("配置文件路径: ").strip()
            if config_file:
                cmd_execute_file(migrator, config_file)

        elif choice == '7':
            migration_id = input("迁移ID (直接回车显示列表): ").strip()
            cmd_rollback(migrator, migration_id if migration_id else None)

        elif choice == '8':
            limit_str = input("显示条数 (默认20): ").strip()
            limit = int(limit_str) if limit_str.isdigit() else 20
            cmd_history(migrator, limit)

        elif choice == '9':
            table = input("表名: ").strip()
            if table:
                cmd_backup_table(migrator, table)

        elif choice == '0':
            print("\n再见!")
            break

        else:
            print_warning("无效选择")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="数据库迁移工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python migrate_tool.py --list-tables
  python migrate_tool.py --show-table products
  python migrate_tool.py --add-column products barcode VARCHAR(50)
  python migrate_tool.py --drop-column products old_field --dry-run
  python migrate_tool.py --interactive
        """
    )

    parser.add_argument('--list-tables', action='store_true',
                       help='列出所有表')
    parser.add_argument('--show-table', metavar='TABLE',
                       help='显示表结构')
    parser.add_argument('--add-column', nargs=3, metavar=('TABLE', 'FIELD', 'TYPE'),
                       help='添加字段')
    parser.add_argument('--drop-column', nargs=2, metavar=('TABLE', 'FIELD'),
                       help='删除字段')
    parser.add_argument('--modify-column', nargs=3, metavar=('TABLE', 'FIELD', 'NEW_TYPE'),
                       help='修改字段')
    parser.add_argument('--execute-file', metavar='CONFIG_FILE',
                       help='执行迁移配置文件')
    parser.add_argument('--rollback', metavar='MIGRATION_ID',
                       help='回滚指定迁移')
    parser.add_argument('--history', action='store_true',
                       help='查看迁移历史')
    parser.add_argument('--backup-table', metavar='TABLE',
                       help='备份表')
    parser.add_argument('--dry-run', action='store_true',
                       help='预演模式，不实际执行')
    parser.add_argument('--interactive', action='store_true',
                       help='交互式模式')
    parser.add_argument('--nullable', action='store_true', default=True,
                       help='字段可空 (默认)')
    parser.add_argument('--not-null', dest='nullable', action='store_false',
                       help='字段不可空')
    parser.add_argument('--default', metavar='VALUE',
                       help='字段默认值')
    parser.add_argument('--after', metavar='FIELD',
                       help='字段放置位置')

    args = parser.parse_args()

    migrator = SafeSchemaMigration()

    if args.interactive:
        interactive_mode()
        return

    if args.list_tables:
        cmd_list_tables(migrator)
        return

    if args.show_table:
        cmd_show_table(migrator, args.show_table)
        return

    if args.add_column:
        table, field, ftype = args.add_column
        cmd_add_column(migrator, table, field, ftype,
                      default_value=args.default,
                      nullable=args.nullable,
                      after=args.after,
                      dry_run=args.dry_run)
        return

    if args.drop_column:
        table, field = args.drop_column
        cmd_drop_column(migrator, table, field, dry_run=args.dry_run)
        return

    if args.modify_column:
        table, field, new_type = args.modify_column
        cmd_modify_column(migrator, table, field, new_type,
                         new_default=args.default,
                         new_nullable=args.nullable,
                         dry_run=args.dry_run)
        return

    if args.execute_file:
        cmd_execute_file(migrator, args.execute_file)
        return

    if args.rollback:
        cmd_rollback(migrator, args.rollback)
        return

    if args.history:
        cmd_history(migrator)
        return

    if args.backup_table:
        cmd_backup_table(migrator, args.backup_table)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
