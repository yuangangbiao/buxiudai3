# -*- coding: utf-8 -*-
"""
数据库升级包生成与执行工具
用于生成和应用数据库结构升级脚本
"""
import os
import sys
import json
import hashlib
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

UPGRADE_DIR = os.path.join(os.path.dirname(__file__), "db_upgrades")
UPGRADE_META_FILE = os.path.join(UPGRADE_DIR, "upgrade_meta.json")


def ensure_upgrade_dir():
    """确保升级目录存在"""
    if not os.path.exists(UPGRADE_DIR):
        os.makedirs(UPGRADE_DIR)
        logger.info(f"创建升级目录: {UPGRADE_DIR}")


def get_current_db_version():
    """获取当前数据库版本"""
    try:
        from models.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS db_version (
                id INT AUTO_INCREMENT PRIMARY KEY,
                version VARCHAR(32) NOT NULL UNIQUE,
                applied_at DATETIME NOT NULL,
                description TEXT,
                checksum VARCHAR(64)
            )
        """)
        conn.commit()

        cursor.execute("SELECT version FROM db_version ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            return result[0] if isinstance(result, tuple) else result.get('version')
        return "0.0.0"
    except Exception as e:
        logger.warning(f"获取数据库版本失败: {e}")
        return "0.0.0"


def save_upgrade_record(version, description, checksum):
    """保存升级记录"""
    try:
        from models.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO db_version (version, applied_at, description, checksum)
            VALUES (%s, %s, %s, %s)
        """, (version, datetime.now(), description, checksum))

        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"升级记录已保存: v{version}")
    except Exception as e:
        logger.error(f"保存升级记录失败: {e}")


def generate_upgrade_script(version, description, sql_content):
    """
    生成数据库升级脚本

    Args:
        version: 版本号 (如 "1.0.1")
        description: 升级描述
        sql_content: SQL语句内容
    """
    ensure_upgrade_dir()

    checksum = hashlib.sha256(sql_content.encode('utf-8')).hexdigest()

    version_dir = os.path.join(UPGRADE_DIR, f"v{version}")
    if not os.path.exists(version_dir):
        os.makedirs(version_dir)

    sql_file = os.path.join(version_dir, "upgrade.sql")
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write("-- 数据库升级脚本\n")
        f.write(f"-- 版本: {version}\n")
        f.write(f"-- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"-- 描述: {description}\n")
        f.write("--" + "=" * 70 + "\n\n")
        f.write(sql_content)

    meta = {
        "version": version,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "checksum": checksum,
        "sql_file": "upgrade.sql",
        "status": "generated"
    }

    meta_file = os.path.join(version_dir, "meta.json")
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    all_meta = load_all_upgrade_meta()
    all_meta[version] = meta
    with open(UPGRADE_META_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_meta, f, ensure_ascii=False, indent=2)

    logger.info(f"升级脚本已生成: v{version}")
    logger.info(f"  描述: {description}")
    logger.info(f"  文件: {sql_file}")

    return version_dir


def load_all_upgrade_meta():
    """加载所有升级元数据"""
    if os.path.exists(UPGRADE_META_FILE):
        with open(UPGRADE_META_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def check_column_exists(cursor, table, column):
    """检查列是否存在"""
    cursor.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """, (table, column))
    return cursor.fetchone()[0] > 0


def check_index_exists(cursor, table, index_name):
    """检查索引是否存在"""
    cursor.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s
    """, (table, index_name))
    return cursor.fetchone()[0] > 0


def apply_upgrade(version):
    """应用指定版本的升级脚本"""
    version_dir = os.path.join(UPGRADE_DIR, f"v{version}")
    sql_file = os.path.join(version_dir, "upgrade.sql")
    meta_file = os.path.join(version_dir, "meta.json")

    if not os.path.exists(sql_file):
        logger.error(f"升级脚本不存在: v{version}")
        return False

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    checksum = hashlib.sha256(sql_content.encode('utf-8')).hexdigest()
    if checksum != meta['checksum']:
        logger.warning(f"校验和不一致，继续执行 (文件可能已被人为修改)")
        # return False

    try:
        from models.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        lines = sql_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('--') or line.startswith('#'):
                continue

            if line.endswith(';'):
                stmt = line[:-1].strip()
                if not stmt:
                    continue

                if stmt.startswith('ALTER TABLE'):
                    import re
                    match = re.search(r"ADD COLUMN (\w+)", stmt)
                    if match:
                        col_name = match.group(1)
                        table_match = re.search(r"ALTER TABLE (\w+)", stmt)
                        table_name = table_match.group(1) if table_match else 'orders'
                        if check_column_exists(cursor, table_name, col_name):
                            logger.info(f"列 {col_name} 已存在，跳过")
                            continue

                elif stmt.startswith('CREATE INDEX'):
                    import re
                    match = re.search(r"CREATE INDEX (\w+)", stmt)
                    if match:
                        idx_name = match.group(1)
                        if check_index_exists(cursor, 'orders', idx_name):
                            logger.info(f"索引 {idx_name} 已存在，跳过")
                            continue

                try:
                    cursor.execute(stmt)
                    logger.info(f"执行: {stmt[:60]}...")
                except Exception as e:
                    if 'already exists' not in str(e).lower() and 'Duplicate' not in str(e):
                        logger.warning(f"SQL执行警告: {e}")

        conn.commit()
        cursor.close()
        conn.close()

        save_upgrade_record(version, meta['description'], checksum)

        meta['status'] = 'applied'
        meta['applied_at'] = datetime.now().isoformat()
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        all_meta = load_all_upgrade_meta()
        if version in all_meta:
            all_meta[version]['status'] = 'applied'
            all_meta[version]['applied_at'] = datetime.now().isoformat()
        with open(UPGRADE_META_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_meta, f, ensure_ascii=False, indent=2)

        logger.info(f"升级成功: v{version}")
        return True

    except Exception as e:
        logger.error(f"升级失败: v{version}, 错误: {e}")
        return False


def list_upgrades():
    """列出所有升级脚本"""
    ensure_upgrade_dir()

    all_meta = load_all_upgrade_meta()
    current_version = get_current_db_version()

    print("\n" + "=" * 70)
    print("数据库升级包列表")
    print("=" * 70)
    print(f"当前数据库版本: {current_version}")
    print()

    if not all_meta:
        print("暂无升级脚本")
        return

    for version in sorted(all_meta.keys()):
        meta = all_meta[version]
        status = meta.get('status', 'unknown')
        desc = meta.get('description', '')
        applied_at = meta.get('applied_at', '')

        status_icon = "✓" if status == "applied" else "○"
        print(f"  [{status_icon}] v{version}: {desc}")
        if applied_at:
            print(f"      应用时间: {applied_at}")
        print()

    print("=" * 70)


def create_archive_fields_upgrade():
    """创建归档字段升级包"""
    ensure_upgrade_dir()

    sql_content = """ALTER TABLE orders ADD COLUMN is_archived TINYINT(1) DEFAULT 0 COMMENT '是否已归档' AFTER version;

ALTER TABLE orders ADD COLUMN archived_at DATETIME DEFAULT NULL COMMENT '归档时间' AFTER is_archived;

ALTER TABLE orders ADD COLUMN archived_by VARCHAR(50) DEFAULT NULL COMMENT '归档操作人' AFTER archived_at;

ALTER TABLE orders ADD COLUMN original_status VARCHAR(32) DEFAULT NULL COMMENT '归档前的原始状态' AFTER archived_by;

CREATE INDEX idx_orders_is_archived ON orders(is_archived);

CREATE INDEX idx_orders_archived_at ON orders(archived_at);
"""

    return generate_upgrade_script(
        version="1.0.0",
        description="添加订单归档功能字段（is_archived, archived_at, archived_by, original_status）",
        sql_content=sql_content.strip()
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='数据库升级包工具')
    parser.add_argument('--list', action='store_true', help='列出所有升级包')
    parser.add_argument('--apply', metavar='VERSION', help='应用指定版本的升级')
    parser.add_argument('--create-archive-upgrade', action='store_true', help='创建归档字段升级包')

    args = parser.parse_args()

    if args.list:
        list_upgrades()
    elif args.apply:
        apply_upgrade(args.apply)
    elif args.create_archive_upgrade:
        create_archive_fields_upgrade()
    else:
        parser.print_help()
        print("\n示例:")
        print("  python db_upgrade_tool.py --list                    # 列出所有升级包")
        print("  python db_upgrade_tool.py --apply 1.0.0            # 应用v1.0.0升级")
        print("  python db_upgrade_tool.py --create-archive-upgrade  # 创建归档字段升级包")
