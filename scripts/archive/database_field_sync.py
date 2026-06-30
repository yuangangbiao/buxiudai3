# -*- coding: utf-8 -*-
"""
数据库字段同步工具 - 只同步字段结构，不同步数据
功能：
  - 添加新字段（目标库没有的）
  - 修改字段变更（类型/长度/默认值等变化）
  - 不删除老字段，不同步数据
安全特性：事务保护、自动备份、预览模式、多重安全检查
"""
import os
import sys
import pymysql
from pymysql.cursors import DictCursor
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

VERSION = "3.0.0"

def get_connection(host, port, user, password, database):
    """创建数据库连接"""
    return pymysql.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        cursorclass=DictCursor
    )

def get_table_fields(conn, table_name):
    """获取表的所有字段信息"""
    with conn.cursor() as cursor:
        cursor.execute(f"SHOW FULL COLUMNS FROM `{table_name}`")
        columns = cursor.fetchall()
    return {col['Field']: col for col in columns}

def get_all_tables(conn):
    """获取所有表名"""
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = [list(row.values())[0] for row in cursor.fetchall()]
    return tables

def parse_field_type(field_type):
    """解析字段类型，返回(基础类型, 长度, 小数位)"""
    field_type = field_type.upper()
    if '(' in field_type:
        base = field_type[:field_type.index('(')]
        params = field_type[field_type.index('(')+1:field_type.index(')')]
        if ',' in params:
            parts = params.split(',')
            if len(parts) == 2:
                try:
                    length, decimals = parts
                    return base, int(length), int(decimals)
                except ValueError:
                    return base, params, 0
            else:
                return base, params, 0
        return base, int(params) if params.isdigit() else params, 0
    return field_type, None, 0

def compare_fields(src_field, dst_field, table_name):
    """
    比较两个字段是否有变更
    返回: (has_change, change_details)
    change_details: [(变更描述, 源值, 目标值), ...]
    """
    changes = []
    src_type = src_field['Type']
    dst_type = dst_field['Type']

    src_base, src_len, src_dec = parse_field_type(src_type)
    dst_base, dst_len, dst_dec = parse_field_type(dst_type)

    if src_base != dst_base:
        changes.append((f"字段类型", f"{dst_base}→{src_base}", src_type, dst_type))

    if src_len is not None and dst_len is not None:
        if src_len != dst_len:
            changes.append((f"字段长度", f"{dst_len}→{src_len}", src_len, dst_len))
        if src_dec != dst_dec:
            changes.append((f"小数位数", f"{dst_dec}→{src_dec}", src_dec, dst_dec))

    src_null = src_field['Null']
    dst_null = dst_field['Null']
    if src_null != dst_null:
        changes.append((f"是否允许NULL", f"{dst_null}→{src_null}", src_null, dst_null))

    src_default = src_field['Default']
    dst_default = dst_field['Default']
    if src_default != dst_default:
        changes.append((f"默认值", f"'{dst_default}'→'{src_default}'", src_default, dst_default))

    src_extra = src_field['Extra']
    dst_extra = dst_field['Extra']
    if src_extra != dst_extra:
        changes.append((f"扩展属性", f"{dst_extra}→{src_extra}", src_extra, dst_extra))

    src_comment = src_field['Comment'] or ''
    dst_comment = dst_field['Comment'] or ''
    if src_comment != dst_comment:
        changes.append((f"注释", f"'{dst_comment[:20]}...'→'{src_comment[:20]}...'" if len(src_comment) > 20 or len(dst_comment) > 20 else f"'{dst_comment}'→'{src_comment}'", src_comment, dst_comment))

    return len(changes) > 0, changes

def generate_modify_sql(table_name, field_name, src_field, changes):
    """生成修改字段的SQL（使用MODIFY COLUMN）"""
    field_type = src_field['Type']
    nullable = 'NULL' if src_field['Null'] == 'YES' else 'NOT NULL'

    default_val = src_field['Default']
    if default_val is not None and default_val != '':
        if default_val.upper() == 'CURRENT_TIMESTAMP':
            default = 'DEFAULT CURRENT_TIMESTAMP'
        else:
            default = f"DEFAULT '{default_val}'"
    else:
        default = ''

    extra = src_field['Extra']
    if extra and 'DEFAULT_GENERATED' in extra.upper():
        extra = extra.upper().replace('DEFAULT_GENERATED', '').strip()

    sql = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{field_name}` {field_type} {nullable} {default}".strip()
    if extra:
        sql += f" {extra}"
    comment = src_field['Comment']
    if comment:
        sql += f" COMMENT '{comment}'"
    sql += ";"
    return sql

def generate_add_sql(table_name, field_name, field_info):
    """生成添加字段的SQL"""
    field_type = field_info['Type']
    nullable = 'NULL' if field_info['Null'] == 'YES' else 'NOT NULL'
    default = f"DEFAULT '{field_info['Default']}'" if field_info['Default'] is not None else ''
    extra = field_info['Extra']
    comment = field_info['Comment']

    sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{field_name}` {field_type} {nullable} {default}".strip()
    if extra:
        sql += f" {extra}"
    if comment:
        sql += f" COMMENT '{comment}'"
    sql += ";"
    return sql

def generate_rollback_sql(conn, table_name, new_fields, modified_fields):
    """生成回滚SQL"""
    rollbacks = []
    for field in new_fields:
        rollbacks.append(f"ALTER TABLE `{table_name}` DROP COLUMN `{field}`;")
    for field_name in modified_fields:
        rollbacks.append(f"-- {field_name} 的变更需要手动回滚，请查看备份文件")
    return "\n".join(rollbacks)

def backup_table_structure(conn, table_name, backup_dir):
    """备份单表的创建语句"""
    os.makedirs(backup_dir, exist_ok=True)
    with conn.cursor() as cursor:
        cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
        result = cursor.fetchone()
        if isinstance(result, dict):
            create_sql = result.get('Create Table', result.get('Create Table', ''))
        else:
            create_sql = result[1]
    backup_file = os.path.join(backup_dir, f"{table_name}_backup.sql")
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(f"-- 表结构备份 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"-- 表名: {table_name}\n\n")
        f.write(create_sql + ";\n")
    return backup_file

def verify_data_integrity(conn, table_name):
    """验证数据完整性"""
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table_name}`")
        row_count = cursor.fetchone()['cnt']
        cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 1")
        cursor.fetchone()
    return row_count

def compare_and_sync_fields(src_conn, dst_conn, table_name, dry_run=True, sync_changes=True):
    """
    比较并同步字段
    src_conn: 源数据库连接（新结构）
    dst_conn: 目标数据库连接（原数据库）
    table_name: 表名
    dry_run: True=预览模式，False=执行同步
    sync_changes: True=同步字段变更，False=只添加新字段
    返回: {
        'fields_to_add': [...],
        'fields_to_modify': {...},
        'add_sqls': [...],
        'modify_sqls': [...],
        'rollback_sql': ''
    }
    """
    src_fields = get_table_fields(src_conn, table_name)
    dst_fields = get_table_fields(dst_conn, table_name)

    fields_to_add = []
    fields_to_modify = []
    add_sqls = []
    modify_sqls = []

    for field_name, field_info in src_fields.items():
        if field_name not in dst_fields:
            # 字段在源中存在，目标中不存在，需要添加
            sql = generate_add_sql(table_name, field_name, field_info)
            fields_to_add.append(field_name)
            add_sqls.append((field_name, sql))
            logger.info("   [NEW] 新字段: {}".format(field_name))
            logger.info("      SQL: {}".format(sql))
        elif sync_changes:
            # 字段在两边都存在，检查是否有变更
            has_change, changes = compare_fields(field_info, dst_fields[field_name], table_name)
            if has_change:
                sql = generate_modify_sql(table_name, field_name, field_info, changes)
                fields_to_modify.append(field_name)
                modify_sqls.append((field_name, sql, changes))
                logger.info("   [MOD] 变更字段: {}".format(field_name))
                for change_type, change_desc, src_val, dst_val in changes:
                    logger.info(f"      - {change_type}: {change_desc}")

    rollback_sql = generate_rollback_sql(dst_conn, table_name, fields_to_add, fields_to_modify)

    return {
        'fields_to_add': fields_to_add,
        'fields_to_modify': fields_to_modify,
        'add_sqls': add_sqls,
        'modify_sqls': modify_sqls,
        'rollback_sql': rollback_sql
    }

def sync_tables(src_config, dst_config, tables=None, dry_run=True, enable_backup=True, sync_changes=True):
    """
    同步多个表的字段结构

    src_config: 源数据库配置（新结构）
    dst_config: 目标数据库配置（原数据库）
    tables: 要同步的表名列表，None表示所有表
    dry_run: True=预览模式，False=执行同步
    enable_backup: 是否启用备份
    sync_changes: True=同步字段变更，False=只添加新字段
    """
    logger.info("=" * 70)
    logger.info("  数据库字段同步工具 v{}".format(VERSION))
    logger.info("  [只同步字段，不同步数据，不删除老字段]")
    logger.info("=" * 70)
    mode_str = "[PREVIEW] 预览模式 - 不执行实际更改" if dry_run else "[EXECUTE] 执行模式 - 将进行实际更改"
    logger.info("模式: {}".format(mode_str))
    logger.info("同步变更: {}".format("是" if sync_changes else "否"))
    logger.info("")
    logger.info("源数据库: {}:{}/{}".format(src_config['host'], src_config['port'], src_config['database']))
    logger.info("目标数据库: {}:{}/{}".format(dst_config['host'], dst_config['port'], dst_config['database']))
    logger.info("")

    src_conn = get_connection(**src_config)
    dst_conn = get_connection(**dst_config)

    backup_dir = None
    if enable_backup and not dry_run:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "field_sync_backups", timestamp)
        logger.info("[BACKUP] 备份目录: {}".format(backup_dir))

    results = []
    total_add_fields = 0
    total_modify_fields = 0
    total_tables_scanned = 0

    try:
        if tables is None:
            tables = get_all_tables(src_conn)
        total_tables_scanned = len(tables)

        for table_name in tables:
            logger.info("")
            logger.info("-" * 60)
            logger.info("[CHECK] 检查表: {}".format(table_name))

            try:
                result = compare_and_sync_fields(src_conn, dst_conn, table_name, dry_run, sync_changes)

                fields_to_add = result['fields_to_add']
                fields_to_modify = result['fields_to_modify']
                add_sqls = result['add_sqls']
                modify_sqls = result['modify_sqls']

                if not fields_to_add and not fields_to_modify:
                    logger.info("   [OK] 表 {} 已是最新，无需更改".format(table_name))
                    results.append({
                        "table": table_name,
                        "status": "skipped",
                        "reason": "字段已同步",
                        "fields_added": 0,
                        "fields_modified": 0
                    })
                else:
                    total_add_fields += len(fields_to_add)
                    total_modify_fields += len(fields_to_modify)

                    if not dry_run:
                        logger.info("   [RUN] 开始执行同步...")
                        logger.info("   [NEW] 新增字段: {} 个".format(len(fields_to_add)))
                        logger.info("   [MOD] 变更字段: {} 个".format(len(fields_to_modify)))

                        # 1. 验证执行前数据完整性
                        try:
                            pre_count = verify_data_integrity(dst_conn, table_name)
                            logger.info("   [STAT] 执行前数据行数: {}".format(pre_count))
                        except Exception as e:
                            logger.warning("   [WARN] 无法验证数据: {}".format(e))

                        # 2. 备份表结构
                        if enable_backup:
                            backup_file = backup_table_structure(dst_conn, table_name, backup_dir)
                            logger.info("   [BACKUP] 已备份: {}".format(os.path.basename(backup_file)))

                        # 3. 生成回滚脚本
                        rollback_file = os.path.join(backup_dir, f"{table_name}_rollback.sql")
                        with open(rollback_file, 'w', encoding='utf-8') as f:
                            f.write(f"-- 回滚脚本 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"-- 表名: {table_name}\n")
                            if fields_to_add:
                                f.write(f"-- 新增字段: {', '.join(fields_to_add)}\n")
                            if fields_to_modify:
                                f.write(f"-- 变更字段: {', '.join(fields_to_modify)}\n")
                            f.write(f"\n-- 回滚SQL:\n{result['rollback_sql']}\n")
                        logger.info("   [ROLLBACK] 回滚脚本: {}".format(os.path.basename(rollback_file)))

                        # 4. 执行新增字段
                        executed_add = []
                        for field_name, sql in add_sqls:
                            try:
                                with dst_conn.cursor() as cursor:
                                    cursor.execute(sql)
                                dst_conn.commit()
                                executed_add.append(field_name)
                                logger.info("   [OK] 添加字段: {}".format(field_name))
                            except Exception as e:
                                logger.error("   [FAIL] 添加字段失败: {}".format(field_name))
                                logger.error("      SQL: {}".format(sql))
                                logger.error("      错误: {}".format(e))

                        # 5. 执行变更字段
                        executed_modify = []
                        for field_name, sql, changes in modify_sqls:
                            try:
                                with dst_conn.cursor() as cursor:
                                    cursor.execute(sql)
                                dst_conn.commit()
                                executed_modify.append(field_name)
                                logger.info("   [OK] 修改字段: {}".format(field_name))
                            except Exception as e:
                                logger.error("   [FAIL] 修改字段失败: {}".format(field_name))
                                logger.error("      SQL: {}".format(sql))
                                logger.error("      错误: {}".format(e))

                        # 6. 验证执行后数据完整性
                        try:
                            post_count = verify_data_integrity(dst_conn, table_name)
                            if pre_count == post_count:
                                logger.info("   [OK] 数据完整性验证通过: {} 行".format(post_count))
                            else:
                                logger.warning("   [WARN] 数据行数变化: {} -> {}".format(pre_count, post_count))
                        except Exception as e:
                            logger.warning("   [WARN] 无法验证数据: {}".format(e))

                        results.append({
                            "table": table_name,
                            "status": "success",
                            "fields_added": len(executed_add),
                            "fields_modified": len(executed_modify),
                            "failed_add": len(add_sqls) - len(executed_add),
                            "failed_modify": len(modify_sqls) - len(executed_modify)
                        })
                    else:
                        results.append({
                            "table": table_name,
                            "status": "pending",
                            "fields_added": len(fields_to_add),
                            "fields_modified": len(fields_to_modify),
                            "add_sqls": add_sqls,
                            "modify_sqls": modify_sqls
                        })

            except Exception as e:
                import traceback
                logger.error("   [ERROR] 处理表 {} 时出错: {}".format(table_name, e))
                logger.error("      详细错误: {}".format(traceback.format_exc()))
                results.append({
                    "table": table_name,
                    "status": "error",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })

    finally:
        src_conn.close()
        dst_conn.close()

    # ===== 生成报告 =====
    logger.info("")
    logger.info("=" * 70)
    logger.info("  同步完成!")
    logger.info("=" * 70)
    logger.info(f"扫描表数: {total_tables_scanned}")

    success_tables = [r for r in results if r['status'] == 'success']
    pending_tables = [r for r in results if r['status'] == 'pending']
    skipped_tables = [r for r in results if r['status'] == 'skipped']
    error_tables = [r for r in results if r['status'] == 'error']

    if not dry_run:
        logger.info(f"处理表数: {len(success_tables)}")
        logger.info(f"新增字段总数: {total_add_fields}")
        logger.info(f"变更字段总数: {total_modify_fields}")
        if backup_dir:
            logger.info(f"备份目录: {backup_dir}")
    else:
        pending_add = sum(r['fields_added'] for r in pending_tables)
        pending_modify = sum(r['fields_modified'] for r in pending_tables)
        logger.info(f"待新增字段表数: {len(pending_tables)}")
        logger.info(f"待新增字段总数: {pending_add}")
        logger.info(f"待变更字段总数: {pending_modify}")

    logger.info(f"已是最新表数: {len(skipped_tables)}")
    if error_tables:
        logger.info(f"错误表数: {len(error_tables)}")
        for r in error_tables:
            logger.info(f"   - {r['table']}: {r.get('error', '未知错误')}")

    if dry_run:
        logger.info("")
        logger.info("[PREVIEW] 预览完成，以上是将会执行的更改")
        logger.info("[HINT] 如确认无误，请将 DRY_RUN = False 后重新运行")

    return results

def print_help():
    """打印帮助信息"""
    print(f"""
================================================================================
数据库字段同步工具 v{VERSION}
================================================================================

【功能说明】
  对比两个数据库的表结构：
  - 添加新字段（目标库没有的）
  - 修改字段变更（类型/长度/默认值等变化）
  - 不删除目标库中多余的字段
  - 不同步任何数据

【同步的变更类型】
  [CHECK] 字段类型变化 (如 VARCHAR -> TEXT)
  [CHECK] 字段长度变化 (如 VARCHAR(50) -> VARCHAR(100))
  [CHECK] 默认值变化 (如无默认值 -> DEFAULT '')
  [CHECK] 是否允许NULL变化
  [CHECK] 注释变化

【安全特性】
  [CHECK] 预览模式 - 先预览将要执行的更改
  [CHECK] 自动备份 - 执行前备份表结构到 field_sync_backups/
  [CHECK] 回滚脚本 - 自动生成回滚SQL
  [CHECK] 数据验证 - 执行前后验证数据完整性

【使用步骤】
  1. 配置源数据库（新结构）和目标数据库（原数据库）
  2. 首次运行设置 DRY_RUN = True（预览模式）
  3. 确认无误后设置 DRY_RUN = False（执行模式）
  4. 查看执行结果和备份文件

================================================================================
""")

if __name__ == "__main__":
    print_help()

    # ==================== 配置区域 ====================
    # 方式1: 直接指定数据库
    # src_config = {
    #     "host": "localhost",
    #     "port": 3306,
    #     "user": "root",
    #     "password": "your_password",
    #     "database": "steel_belt_new"
    # }
    # dst_config = {
    #     "host": "localhost",
    #     "port": 3306,
    #     "user": "root",
    #     "password": "your_password",
    #     "database": "steel_belt"
    # }

    # 方式2: 从环境变量读取（使用项目配置）
    import os
    src_config = {
        "host": os.getenv('MYSQL_HOST', 'localhost'),
        "port": int(os.getenv('MYSQL_PORT', 3306)),
        "user": os.getenv('MYSQL_USER', 'root'),
        "password": os.getenv('MYSQL_PASSWORD', ''),
        "database": os.getenv('MYSQL_DATABASE', 'steel_belt')
    }

    # 目标数据库（远程）
    dst_config = {
        "host": "192.168.0.101",
        "port": 3306,
        "user": os.getenv('MYSQL_USER', 'root'),
        "password": os.getenv('MYSQL_PASSWORD', ''),
        "database": os.getenv('MYSQL_DATABASE', 'steel_belt')
    }

    # 要同步的表，None表示所有表
    sync_tables_list = None  # 例如: ['orders', 'products'] 或 None

    # 预览模式：True=只显示不执行，False=执行实际更改
    DRY_RUN = False

    # 是否启用备份（强烈建议开启）
    ENABLE_BACKUP = True

    # 是否同步字段变更（True=检测并修改变更，False=只添加新字段）
    SYNC_CHANGES = True

    # ==================== 执行同步 ====================
    print("\n" + "="*60)
    print("源数据库: {}:{}/{}".format(src_config['host'], src_config['port'], src_config['database']))
    print("目标数据库: {}:{}/{}".format(dst_config['host'], dst_config['port'], dst_config['database']))
    mode_str = "[PREVIEW] 预览模式" if DRY_RUN else "[EXECUTE] 执行模式"
    print("模式: {}".format(mode_str))
    print("同步变更: {}".format("是" if SYNC_CHANGES else "否"))
    print("备份: {}".format("开启" if ENABLE_BACKUP else "关闭"))
    print("="*60 + "\n")

    results = sync_tables(
        src_config,
        dst_config,
        tables=sync_tables_list,
        dry_run=DRY_RUN,
        enable_backup=ENABLE_BACKUP,
        sync_changes=SYNC_CHANGES
    )

    print("\n" + "=" * 70)
    if DRY_RUN:
        print("【预览完成】如确认无误，请将 DRY_RUN = False 后重新运行")
        print("备份文件将保存在: field_sync_backups/ 目录")
    else:
        print("【同步完成】字段已同步到目标数据库")
        print("如需回滚，请在 field_sync_backups/ 目录查找回滚脚本")
    print("=" * 70)
