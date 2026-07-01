# -*- coding: utf-8 -*-
"""
数据库迁移管理工具

支持：
- 创建迁移脚本
- 执行迁移
- 回滚迁移
- 查看迁移状态

使用方式：
    python migrations/run.py status
    python migrations/run.py upgrade
    python migrations/run.py downgrade -v 001
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


MIGRATIONS_DIR = Path(__file__).parent
MIGRATION_TABLE = 'schema_migrations'


def get_connection():
    """获取数据库连接"""
    try:
        from models.database import get_connection
        return get_connection()
    except ImportError:
        from core.db import get_direct_connection
        return get_direct_connection(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DATABASE', 'steel_belt'),
            charset='utf8mb4'
        )


def ensure_migration_table():
    """确保迁移记录表存在"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at DATETIME NOT NULL,
                    description TEXT,
                    checksum VARCHAR(64)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            conn.commit()
    finally:
        conn.close()


def get_applied_migrations() -> List[str]:
    """获取已应用的迁移版本"""
    ensure_migration_table()
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT version FROM {MIGRATION_TABLE} ORDER BY version")
            return [row['version'] for row in cursor.fetchall()]
    finally:
        conn.close()


def get_migration_files() -> List[Dict]:
    """获取所有迁移脚本"""
    migrations = []
    for f in sorted(MIGRATIONS_DIR.glob('*.py')):
        if f.name.startswith('__'):
            continue
        version = f.stem.split('_')[0]
        migrations.append({
            'version': version,
            'path': f,
            'name': f.stem
        })
    return migrations


def get_pending_migrations() -> List[Dict]:
    """获取待执行的迁移"""
    applied = set(get_applied_migrations())
    all_migrations = get_migration_files()
    return [m for m in all_migrations if m['version'] not in applied]


def calculate_checksum(content: str) -> str:
    """计算文件校验和"""
    import hashlib
    return hashlib.sha256(content.encode()).hexdigest()


def apply_migration(migration: Dict) -> bool:
    """应用单个迁移"""
    ensure_migration_table()
    conn = get_connection()
    try:
        with open(migration['path'], 'r', encoding='utf-8') as f:
            content = f.read()

        checksum = calculate_checksum(content)

        with conn.cursor() as cursor:
            cursor.execute(f"SELECT version FROM {MIGRATION_TABLE} WHERE version=%s", (migration['version'],))
            if cursor.fetchone():
                logger.info(f"迁移 {migration['version']} 已应用，跳过")
                return False

            logger.info(f"应用迁移: {migration['name']}")

            namespace = {'conn': conn, 'cursor': None}
            exec(content, namespace)

            cursor.execute(
                f"INSERT INTO {MIGRATION_TABLE} (version, applied_at, checksum) VALUES (%s, %s, %s)",
                (migration['version'], datetime.now(), checksum)
            )
            conn.commit()
            logger.info(f"迁移 {migration['version']} 应用成功")
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"迁移 {migration['version']} 失败: {e}")
        raise
    finally:
        conn.close()


def rollback_migration(version: str) -> bool:
    """回滚指定版本迁移"""
    ensure_migration_table()
    conn = get_connection()
    try:
        migration_files = get_migration_files()
        migration = next((m for m in migration_files if m['version'] == version), None)

        if not migration:
            raise ValueError(f"迁移版本 {version} 不存在")

        logger.info(f"回滚迁移: {migration['name']}")

        with open(migration['path'], 'r', encoding='utf-8') as f:
            content = f.read()

        namespace = {'conn': conn, 'cursor': None, 'ROLLBACK': True}
        exec(content, namespace)

        with conn.cursor() as cursor:
            cursor.execute(f"DELETE FROM {MIGRATION_TABLE} WHERE version=%s", (version,))
            conn.commit()
            logger.info(f"迁移 {version} 回滚成功")
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"回滚 {version} 失败: {e}")
        raise
    finally:
        conn.close()


def status():
    """显示迁移状态"""
    applied = get_applied_migrations()
    pending = get_pending_migrations()

    print("\n" + "=" * 60)
    print("数据库迁移状态")
    print("=" * 60)
    print(f"\n已应用: {len(applied)} 个")
    for v in applied:
        print(f"  ✓ {v}")

    print(f"\n待执行: {len(pending)} 个")
    for m in pending:
        print(f"  ○ {m['version']} - {m['name']}")

    print("\n" + "=" * 60)


def upgrade(target_version: Optional[str] = None):
    """执行迁移升级"""
    pending = get_pending_migrations()

    if target_version:
        pending = [m for m in pending if m['version'] <= target_version]

    if not pending:
        print("没有待执行的迁移")
        return

    print(f"将执行 {len(pending)} 个迁移...")
    for migration in pending:
        apply_migration(migration)


def downgrade(version: str):
    """执行迁移降级"""
    rollback_migration(version)


def create_migration(name: str):
    """创建新的迁移脚本"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    version = timestamp[:12]
    filename = f"{version}_{name}.py"
    path = MIGRATIONS_DIR / filename

    content = f'''# -*- coding: utf-8 -*-
"""
迁移: {name}
版本: {version}
创建时间: {datetime.now().isoformat()}
"""
# 在此添加 SQL 语句
# 如果需要回滚，使用 ROLLBACK 变量检查
if 'ROLLBACK' in dir():
    # 回滚操作
    cursor.execute("ALTER TABLE orders DROP COLUMN IF EXISTS new_field")
else:
    # 升级操作
    cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS new_field VARCHAR(255)")
'''

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"创建迁移脚本: {path}")


if __name__ == '__main__':
    import argparse

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    parser = argparse.ArgumentParser(description='数据库迁移工具')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('status', help='查看迁移状态')
    subparsers.add_parser('upgrade', help='执行所有待定迁移')
    subparsers.add_parser('init', help='初始化迁移表')

    rollback_parser = subparsers.add_parser('downgrade', help='回滚迁移')
    rollback_parser.add_argument('-v', '--version', required=True, help='要回滚的版本')

    create_parser = subparsers.add_parser('create', help='创建新迁移')
    create_parser.add_argument('name', help='迁移名称')

    args = parser.parse_args()

    if args.command == 'status':
        status()
    elif args.command == 'upgrade':
        upgrade()
    elif args.command == 'init':
        ensure_migration_table()
        print("迁移表已初始化")
    elif args.command == 'downgrade':
        downgrade(args.version)
    elif args.command == 'create':
        create_migration(args.name)
    else:
        parser.print_help()
