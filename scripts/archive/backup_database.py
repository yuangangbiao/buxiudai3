# -*- coding: utf-8 -*-
"""
数据库备份工具 - 纯Python实现
使用 pymysql 连接数据库并导出数据
"""
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_db_config():
    """获取数据库配置"""
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
    backup_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
    today = datetime.now().strftime('%Y%m%d')
    backup_dir = os.path.join(backup_base, today)
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def generate_create_table_sql(cursor, table_name):
    """生成 CREATE TABLE 语句"""
    cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
    row = cursor.fetchone()
    return row[1] + ";\n"

def generate_insert_statements(cursor, table_name, batch_size=1000):
    """生成 INSERT 语句"""
    cursor.execute(f"SELECT * FROM `{table_name}`")
    columns = [desc[0] for desc in cursor.description]

    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break

        for row in rows:
            values = []
            for val in row:
                if val is None:
                    values.append("NULL")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                else:
                    val_str = str(val).replace('\\', '\\\\').replace("'", "\\'").replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t')
                    values.append(f"'{val_str}'")
            col_names = ", ".join([f"`{c}`" for c in columns])
            val_str = ", ".join(values)
            yield f"INSERT INTO `{table_name}` ({col_names}) VALUES ({val_str});\n"

def backup_database(password=None):
    """
    备份数据库 - 使用纯 Python + pymysql

    Returns:
        str: 备份文件路径，失败返回None
    """
    config = get_db_config()

    if password:
        config['password'] = password
    else:
        password = config.get('password', '')

    if not password:
        print("错误: 未设置数据库密码！")
        return None

    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f"{config['database']}_{timestamp}.sql")

    print(f"=" * 50)
    print(f"数据库备份工具 (Python版)")
    print(f"=" * 50)
    print(f"数据库: {config['database']}")
    print(f"主机: {config['host']}:{config['port']}")
    print(f"用户: {config['user']}")
    print(f"备份目录: {backup_dir}")
    print(f"备份文件: {os.path.basename(backup_file)}")
    print(f"=" * 50)

    try:
        import pymysql
    except ImportError:
        print("错误: 未安装 pymysql！")
        print("请运行: pip install pymysql")
        return None

    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()

        cursor.execute(f"USE `{config['database']}`")
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"\n找到 {len(tables)} 个数据表")
        print("正在备份...")

        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write("-- " + "=" * 60 + "\n")
            f.write(f"-- 数据库备份文件\n")
            f.write(f"-- 数据库: {config['database']}\n")
            f.write(f"-- 备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- " + "=" * 60 + "\n\n")
            f.write(f"SET NAMES utf8mb4;\n")
            f.write(f"SET FOREIGN_KEY_CHECKS = 0;\n\n")

            table_count = 0
            for table in tables:
                print(f"  备份表: {table}...", end=" ", flush=True)

                try:
                    create_sql = generate_create_table_sql(cursor, table)
                    f.write(f"\n-- ----------------------------\n")
                    f.write(f"-- Table: {table}\n")
                    f.write(f"-- ----------------------------\n")
                    f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                    f.write(create_sql)

                    row_count = 0
                    for insert_sql in generate_insert_statements(cursor, table):
                        f.write(insert_sql)
                        row_count += 1

                    f.write("\n")
                    print(f"✓ {row_count} 行")
                    table_count += 1

                except Exception as e:
                    print(f"✗ 错误: {str(e)}")
                    logger.error(f"备份表 {table} 失败: {e}")

            f.write(f"\nSET FOREIGN_KEY_CHECKS = 1;\n")

            cursor.close()
            conn.close()

            file_size = os.path.getsize(backup_file)
            print(f"")
            print(f"=" * 50)
            print(f"✅ 备份成功！")
            print(f"   文件: {backup_file}")
            print(f"   大小: {file_size / 1024:.2f} KB ({table_count} 个表)")
            print(f"=" * 50)

            logger.info(f"数据库备份成功: {backup_file}")
            return backup_file

    except ImportError:
        print("错误: 未安装 pymysql！")
        print("请运行: pip install pymysql")
        return None
    except Exception as e:
        print(f"")
        print(f"❌ 备份失败！")
        print(f"   错误: {str(e)}")
        logger.exception("数据库备份异常")
        return None

def list_backups():
    """列出所有备份文件"""
    backup_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')

    if not os.path.exists(backup_base):
        print("暂无备份文件")
        return []

    backups = []
    for date_dir in os.listdir(backup_base):
        date_path = os.path.join(backup_base, date_dir)
        if os.path.isdir(date_path):
            for f in os.listdir(date_path):
                if f.endswith('.sql'):
                    full_path = os.path.join(date_path, f)
                    size = os.path.getsize(full_path)
                    mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
                    backups.append({
                        'date': date_dir,
                        'file': f,
                        'path': full_path,
                        'size': size,
                        'mtime': mtime
                    })

    backups.sort(key=lambda x: x['mtime'], reverse=True)

    print(f"\n{'日期':<12} {'时间':<20} {'大小':<12} {'文件'}")
    print("-" * 70)
    for b in backups:
        time_str = b['mtime'].strftime('%Y-%m-%d %H:%M:%S')
        size_str = f"{b['size'] / 1024:.2f} KB"
        print(f"{b['date']:<12} {time_str:<20} {size_str:<12} {b['file']}")

    return backups

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--list':
        list_backups()
    else:
        backup_database()
