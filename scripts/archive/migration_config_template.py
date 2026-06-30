# -*- coding: utf-8 -*-
"""
数据库迁移配置模板

使用方法:
1. 复制此文件并重命名为具体的迁移文件，如 migration_v2.py
2. 修改 MIGRATIONS 配置，定义你的变更
3. 运行迁移: python migrate_tool.py --execute-file migration_v2.py

配置说明:
- migration_name: 迁移名称（必填，唯一标识）
- description: 迁移描述（可选）
- migrations: 变更列表

支持的变更类型:
1. add_column - 添加字段
2. drop_column - 删除字段
3. modify_column - 修改字段
"""

MIGRATION_CONFIG = {
    "migration_name": "v2_schema_update",
    "description": "数据库结构V2版本升级",
    "migrations": [
        {
            "action": "add_column",
            "table": "products",
            "field": "barcode",
            "definition": {
                "type": "VARCHAR(50)",
                "nullable": True,
                "default": None,
                "comment": "商品条形码",
                "after": "spec"
            }
        },
        {
            "action": "add_column",
            "table": "products",
            "field": "min_order_qty",
            "definition": {
                "type": "DECIMAL(12,2)",
                "nullable": True,
                "default": 1.0,
                "comment": "最小订购量",
                "after": "price"
            }
        },
        {
            "action": "add_column",
            "table": "inventory",
            "field": "shelf_location",
            "definition": {
                "type": "VARCHAR(50)",
                "nullable": True,
                "default": None,
                "comment": "货架位置",
                "after": "remark"
            }
        },
        {
            "action": "add_column",
            "table": "inventory",
            "field": "last_check_at",
            "definition": {
                "type": "DATETIME",
                "nullable": True,
                "default": None,
                "comment": "最后盘点时间"
            }
        },
    ]
}


def get_migration_config():
    """获取迁移配置"""
    return MIGRATION_CONFIG


def generate_migration_sql():
    """生成迁移SQL语句（用于预览）"""
    from database_migration import SafeSchemaMigration

    migrator = SafeSchemaMigration()
    sql_statements = []
    rollback_statements = []

    for mig in MIGRATION_CONFIG["migrations"]:
        action = mig["action"]
        table = mig["table"]
        field = mig["field"]

        if action == "add_column":
            sql = migrator.generate_add_field_sql(table, field, mig["definition"])
            rollback = migrator.generate_remove_field_sql(table, field)
            sql_statements.append(sql + ";")
            rollback_statements.append(rollback + ";")

        elif action == "drop_column":
            current_schema = migrator.get_current_schema(table)
            current_def = next((f for f in current_schema if f["Field"] == field), None)
            if current_def:
                add_back = f"ALTER TABLE `{table}` ADD COLUMN `{field}` {current_def['Type']}"
                if current_def['Null'] == 'NO':
                    add_back += " NOT NULL"
                if current_def['Default']:
                    add_back += f" DEFAULT '{current_def['Default']}'"
                rollback_statements.append(add_back + ";")

            sql = migrator.generate_remove_field_sql(table, field)
            sql_statements.append(sql + ";")

        elif action == "modify_column":
            sql = migrator.generate_modify_field_sql(table, field, mig["definition"])
            sql_statements.append(sql + ";")

    return {
        "migration_name": MIGRATION_CONFIG["migration_name"],
        "description": MIGRATION_CONFIG.get("description", ""),
        "sql": sql_statements,
        "rollback": rollback_statements
    }


def print_migration_preview():
    """打印迁移预览"""
    result = generate_migration_sql()

    print("=" * 60)
    print(f"迁移名称: {result['migration_name']}")
    print(f"描述: {result['description']}")
    print("=" * 60)

    print("\n📗 将执行的SQL:")
    for i, sql in enumerate(result["sql"], 1):
        print(f"  {i}. {sql}")

    if result["rollback"]:
        print("\n📙 回滚SQL (如果需要回滚):")
        for i, sql in enumerate(result["rollback"], 1):
            print(f"  {i}. {sql}")

    return result


if __name__ == "__main__":
    print_migration_preview()
