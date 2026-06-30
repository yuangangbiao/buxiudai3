# -*- coding: utf-8 -*-
"""
远程数据库结构备份工具 - 从远程MySQL服务器备份所有数据库的结构
"""
import os
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_remote_db_config():
    """
    获取远程数据库配置
    从环境变量读取，不提供硬编码默认值
    """
    return {
        "host": os.getenv('REMOTE_MYSQL_HOST', '192.168.0.101'),
        "port": int(os.getenv('REMOTE_MYSQL_PORT', 3306)),
        "user": os.getenv('REMOTE_MYSQL_USER', 'root'),
        "password": os.getenv('REMOTE_MYSQL_PASSWORD', ''),
        "charset": "utf8mb4"
    }

def get_local_backup_dir():
    """获取本地备份目录"""
    from config import BASE_DIR
    backup_base = os.path.join(BASE_DIR, 'remote_backups')
    today = datetime.now().strftime('%Y%m%d')
    backup_dir = os.path.join(backup_base, today)
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def get_all_databases(cursor):
    """
    获取所有数据库列表
    """
    cursor.execute("SHOW DATABASES")
    databases = [list(row)[0] for row in cursor.fetchall()]
    return [db for db in databases if db not in ('information_schema', 'mysql', 'performance_schema', 'sys')]

def get_all_tables(cursor, database):
    """
    获取数据库中所有表
    """
    cursor.execute(f"USE `{database}`")
    cursor.execute("SHOW TABLES")
    tables = [list(row)[0] for row in cursor.fetchall()]
    return tables

def generate_create_table_sql(cursor, database, table_name):
    """
    生成 CREATE TABLE SQL 语句
    """
    cursor.execute(f"USE `{database}`")
    cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
    row = cursor.fetchone()
    return row[1]

def get_table_fields(cursor, database, table_name):
    """
    获取表的字段信息
    """
    cursor.execute(f"USE `{database}`")
    cursor.execute(f"SHOW FULL COLUMNS FROM `{table_name}`")
    return cursor.fetchall()

def backup_table_structure(cursor, database, table_name):
    """
    备份单个表的结构
    """
    create_sql = generate_create_table_sql(cursor, database, table_name)
    fields = get_table_fields(cursor, database, table_name)

    output = []
    output.append(f"-- 表结构: {database}.{table_name}")
    output.append(f"-- 字段数量: {len(fields)}")
    output.append("")
    output.append(f"DROP TABLE IF EXISTS `{table_name}`;")
    output.append(create_sql.rstrip(';') + ";")
    output.append("")

    return "\n".join(output)

def backup_single_database(cursor, database):
    """
    备份单个数据库的所有表结构
    返回: SQL语句列表
    """
    tables = get_all_tables(cursor, database)
    sql_statements = []

    for table in tables:
        sql = backup_table_structure(cursor, database, table)
        sql_statements.append(sql)

    return sql_statements

def backup_remote_all_databases(password=None):
    """
    备份远程服务器上所有数据库的结构

    Args:
        password: 远程数据库密码，如果为None则从环境变量读取

    Returns:
        tuple: (备份文件路径列表, 错误信息)
    """
    config = get_remote_db_config()

    if password:
        config['password'] = password

    if not config.get('password'):
        error_msg = "错误: 未设置远程数据库密码！请通过环境变量 REMOTE_MYSQL_PASSWORD 设置"
        logger.error(error_msg)
        return [], error_msg

    backup_dir = get_local_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    try:
        import pymysql
    except ImportError:
        error_msg = "错误: 未安装 pymysql！请运行: pip install pymysql"
        logger.error(error_msg)
        return [], error_msg

    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()

        databases = get_all_databases(cursor)
        logger.info(f"发现 {len(databases)} 个数据库: {', '.join(databases)}")

        backup_files = []

        for db_name in databases:
            logger.info(f"正在备份数据库: {db_name}")

            try:
                sql_statements = backup_single_database(cursor, db_name)

                if not sql_statements:
                    logger.warning(f"  数据库 {db_name} 没有表，跳过")
                    continue

                backup_file = os.path.join(backup_dir, f"{db_name}_structure_{timestamp}.sql")

                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write("-- ===========================================================\n")
                    f.write(f"-- 数据库结构备份\n")
                    f.write(f"-- 备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"-- 远程服务器: {config['host']}:{config['port']}\n")
                    f.write(f"-- 数据库: {db_name}\n")
                    f.write(f"-- 表数量: {len(sql_statements)}\n")
                    f.write(f"-- 警告: 此文件仅包含表结构，不包含任何数据！\n")
                    f.write("-- ===========================================================\n\n")
                    f.write("\n\n".join(sql_statements))

                backup_files.append(backup_file)
                logger.info(f"  ✓ 已备份 {len(sql_statements)} 个表 -> {backup_file}")

            except Exception as e:
                logger.error(f"  ✗ 备份数据库 {db_name} 失败: {e}")
                continue

        conn.close()

        logger.info("=" * 50)
        logger.info(f"备份完成！共成功备份 {len(backup_files)} 个数据库")
        logger.info(f"备份文件保存在: {backup_dir}")
        logger.info("=" * 50)

        return backup_files, None

    except Exception as e:
        error_msg = f"连接远程数据库失败: {str(e)}"
        logger.error(error_msg)
        return [], error_msg

def verify_backup_files(backup_files):
    """
    验证备份文件
    """
    for backup_file in backup_files:
        if not os.path.exists(backup_file):
            logger.warning(f"备份文件不存在: {backup_file}")
            continue

        with open(backup_file, 'r', encoding='utf-8') as f:
            content = f.read()

        table_count = content.count("CREATE TABLE")
        db_name = os.path.basename(backup_file).split('_structure_')[0]
        logger.info(f"  验证 {db_name}: 包含 {table_count} 个表")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='远程数据库结构备份工具')
    parser.add_argument('--host', default='192.168.0.101', help='远程MySQL主机地址')
    parser.add_argument('--port', type=int, default=3306, help='远程MySQL端口')
    parser.add_argument('--user', default='root', help='数据库用户名')
    parser.add_argument('--password', default='', help='数据库密码')
    args = parser.parse_args()

    config = get_remote_db_config()
    config['host'] = args.host
    config['port'] = args.port
    config['user'] = args.user

    if args.password:
        config['password'] = args.password
    elif not config.get('password'):
        config['password'] = os.getenv('MYSQL_PASSWORD', '')
        if not config['password']:
            print("错误: 请设置 MYSQL_PASSWORD 环境变量或使用 --password 参数")
            return

    print("=" * 60)
    print("远程数据库结构备份工具")
    print(f"目标服务器: {config['host']}:{config['port']}")
    print("=" * 60)
    print()

    backup_files, error = backup_remote_all_databases_with_config(config)

    if error:
        print(f"\n错误: {error}")
    else:
        print(f"\n成功备份 {len(backup_files)} 个数据库")
        if backup_files:
            print("\n备份文件列表:")
            verify_backup_files(backup_files)

def backup_remote_all_databases_with_config(config):
    """使用指定配置备份所有数据库"""
    backup_dir = get_local_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    try:
        import pymysql
    except ImportError:
        error_msg = "错误: 未安装 pymysql！请运行: pip install pymysql"
        logger.error(error_msg)
        return [], error_msg

    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()

        databases = get_all_databases(cursor)
        logger.info(f"发现 {len(databases)} 个数据库: {', '.join(databases)}")

        backup_files = []

        for db_name in databases:
            logger.info(f"正在备份数据库: {db_name}")

            try:
                sql_statements = backup_single_database(cursor, db_name)

                if not sql_statements:
                    logger.warning(f"  数据库 {db_name} 没有表，跳过")
                    continue

                backup_file = os.path.join(backup_dir, f"{db_name}_structure_{timestamp}.sql")

                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write("-- ===========================================================\n")
                    f.write(f"-- 数据库结构备份\n")
                    f.write(f"-- 备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"-- 远程服务器: {config['host']}:{config['port']}\n")
                    f.write(f"-- 数据库: {db_name}\n")
                    f.write(f"-- 表数量: {len(sql_statements)}\n")
                    f.write(f"-- 警告: 此文件仅包含表结构，不包含任何数据！\n")
                    f.write("-- ===========================================================\n\n")
                    f.write("\n\n".join(sql_statements))

                backup_files.append(backup_file)
                logger.info(f"  ✓ 已备份 {len(sql_statements)} 个表 -> {backup_file}")

            except Exception as e:
                logger.error(f"  ✗ 备份数据库 {db_name} 失败: {e}")
                continue

        conn.close()

        logger.info("=" * 50)
        logger.info(f"备份完成！共成功备份 {len(backup_files)} 个数据库")
        logger.info(f"备份文件保存在: {backup_dir}")
        logger.info("=" * 50)

        return backup_files, None

    except Exception as e:
        error_msg = f"连接远程数据库失败: {str(e)}"
        logger.error(error_msg)
        return [], error_msg

if __name__ == "__main__":
    main()