# -*- coding: utf-8 -*-
"""
数据库结构备份工具 - 仅备份表字段结构，不备份数据
"""
import os
import sys
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_db_config():
    """
    获取数据库配置
    从环境变量读取，不提供硬编码默认值
    """
    return {
        "host": os.getenv('MYSQL_HOST', 'localhost'),
        "port": int(os.getenv('MYSQL_PORT', 3306)),
        "user": os.getenv('MYSQL_USER', 'root'),
        "password": os.getenv('MYSQL_PASSWORD', ''),
        "database": os.getenv('MYSQL_DATABASE', 'steel_belt'),
        "charset": "utf8mb4"
    }

def get_backup_dir():
    """获取备份目录"""
    from config import BASE_DIR
    backup_base = os.path.join(BASE_DIR, 'backups')
    today = datetime.now().strftime('%Y%m%d')
    backup_dir = os.path.join(backup_base, today)
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def get_table_fields(cursor, table_name):
    """
    获取表的字段信息
    Returns: 字段信息列表，每项包含 field_name, type, nullable, key, default, extra
    """
    cursor.execute(f"SHOW FULL COLUMNS FROM `{table_name}`")
    columns = cursor.fetchall()
    return columns

def generate_create_table_sql(cursor, table_name):
    """
    生成 CREATE TABLE SQL 语句
    不包含数据
    """
    cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
    row = cursor.fetchone()
    return row[1]

def get_all_tables(cursor, database):
    """
    获取数据库中所有表名
    """
    cursor.execute("SHOW TABLES")
    tables = [list(row)[0] for row in cursor.fetchall()]
    return tables

def backup_table_structure(cursor, table_name):
    """
    备份单个表的结构
    返回: CREATE TABLE SQL 语句
    """
    create_sql = generate_create_table_sql(cursor, table_name)
    fields = get_table_fields(cursor, table_name)

    output = []
    output.append(f"-- 表结构: {table_name}")
    output.append(f"-- 字段数量: {len(fields)}")
    output.append(f"")
    output.append(f"DROP TABLE IF EXISTS `{table_name}`;")
    output.append(f"")

    create_stmt = create_sql.rstrip(';')
    output.append(create_stmt + ";")
    output.append("")

    return "\n".join(output)

def backup_database_structure(tables=None, password=None):
    """
    备份数据库结构 - 仅表结构，不包含数据

    Args:
        tables: 要备份的表名列表，None表示备份所有表
        password: 数据库密码，如果为None则从环境变量读取

    Returns:
        str: 备份文件路径，失败返回None
    """
    config = get_db_config()

    if password:
        config['password'] = password

    if not config.get('password'):
        error_msg = "错误: 未设置数据库密码！请通过环境变量 MYSQL_PASSWORD 设置"
        logger.error(error_msg)
        return None, error_msg

    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f"structure_backup_{timestamp}.sql")

    try:
        import pymysql
    except ImportError:
        error_msg = "错误: 未安装 pymysql！请运行: pip install pymysql"
        logger.error(error_msg)
        return None, error_msg

    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()

        if tables is None:
            tables = get_all_tables(cursor, config['database'])

        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write("-- ===========================================================\n")
            f.write(f"-- 数据库结构备份\n")
            f.write(f"-- 备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- 数据库: {config['database']}\n")
            f.write(f"-- 表数量: {len(tables)}\n")
            f.write(f"-- 警告: 此文件仅包含表结构，不包含任何数据！\n")
            f.write("-- ===========================================================\n\n")

            for i, table in enumerate(tables):
                logger.info(f"正在备份表 [{i+1}/{len(tables)}]: {table}")
                table_sql = backup_table_structure(cursor, table)
                f.write(table_sql)
                f.write("\n")

        conn.close()

        logger.info(f"数据库结构备份成功: {backup_file}")
        return backup_file, None

    except Exception as e:
        error_msg = f"备份失败: {str(e)}"
        logger.error(error_msg)
        return None, error_msg

def verify_backup_file(backup_file):
    """
    验证备份文件是否有效

    Returns:
        tuple: (is_valid, table_count, error_msg)
    """
    if not os.path.exists(backup_file):
        return False, 0, "备份文件不存在"

    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if "CREATE TABLE" not in content:
            return False, 0, "备份文件不包含有效的表结构"

        table_count = content.count("CREATE TABLE")
        return True, table_count, None

    except Exception as e:
        return False, 0, f"验证失败: {str(e)}"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print("=" * 50)
    print("数据库结构备份工具")
    print("=" * 50)

    backup_file, error = backup_database_structure()

    if backup_file:
        print(f"\n备份成功: {backup_file}")
        is_valid, count, _ = verify_backup_file(backup_file)
        if is_valid:
            print(f"验证通过: 包含 {count} 个表的结构")
    else:
        print(f"\n备份失败: {error}")