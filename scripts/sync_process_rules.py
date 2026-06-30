# -*- coding: utf-8 -*-
"""
工序计算规则数据同步脚本
从源数据库同步工序计算规则到目标数据库
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 路径配置
SOURCE_DIR = r"d:\yuan\不锈钢网带跟单3.0"
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from core.logger import get_logger
from core.db import db
from core.config import ensure_dir, get_sqlite_path, is_sqlite

logger = get_logger(__name__)


class ProcessRuleSync:
    """工序规则同步类"""

    def __init__(self):
        self.source_dir = SOURCE_DIR
        self.template_files = [
            "data/工序规则模板.json",
            "data/工序规则模板1.json",
            "data/工序规则模板2.json"
        ]

    def load_source_data(self) -> List[Dict]:
        """从JSON模板文件加载源数据"""
        all_rules = []

        for template_file in self.template_files:
            file_path = os.path.join(self.source_dir, template_file)
            if not os.path.exists(file_path):
                logger.warning(f"源文件不存在: {file_path}")
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                    if isinstance(rules, list):
                        all_rules.extend(rules)
                        logger.info(f"从 {template_file} 加载了 {len(rules)} 条规则")
                    elif isinstance(rules, dict):
                        all_rules.append(rules)
                        logger.info(f"从 {template_file} 加载了 1 条规则")
            except Exception as e:
                logger.error(f"加载文件失败 {file_path}: {e}")

        # 去重（基于process_name）
        unique_rules = {}
        for rule in all_rules:
            process_name = rule.get('process_name', '')
            if process_name:
                if process_name not in unique_rules:
                    unique_rules[process_name] = rule
                else:
                    # 更新规则（保留更新的数据）
                    existing = unique_rules[process_name]
                    for key, value in rule.items():
                        if value and value != existing.get(key):
                            existing[key] = value

        logger.info(f"共加载了 {len(all_rules)} 条规则，去重后 {len(unique_rules)} 条")
        return list(unique_rules.values())

    def create_target_table(self):
        """创建目标数据库表"""
        if is_sqlite():
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS process_calc_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_name TEXT NOT NULL UNIQUE,
                product_types_json TEXT,
                condition_expr TEXT,
                planned_qty_formula TEXT,
                priority INTEGER DEFAULT 5,
                enabled INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                default_worker TEXT DEFAULT '',
                unit TEXT DEFAULT '件'
            )
            """
        else:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS process_calc_rules (
                id INT PRIMARY KEY AUTO_INCREMENT,
                process_name VARCHAR(50) NOT NULL UNIQUE,
                product_types_json TEXT,
                condition_expr TEXT,
                planned_qty_formula TEXT,
                priority INT DEFAULT 5,
                enabled TINYINT(1) DEFAULT 1,
                created_at DATETIME DEFAULT NOW(),
                updated_at DATETIME DEFAULT NOW(),
                default_worker VARCHAR(50) DEFAULT '',
                unit VARCHAR(20) DEFAULT '件'
            )
            """

        try:
            with db.get_cursor() as cursor:
                cursor.execute(create_table_sql)
            logger.info("目标表 process_calc_rules 已创建/存在")
        except Exception as e:
            logger.error(f"创建表失败: {e}")
            raise

    def sync_to_target(self, rules: List[Dict]) -> Dict[str, int]:
        """同步规则到目标数据库"""
        stats = {
            'total': len(rules),
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

        if is_sqlite():
            insert_sql = """
            INSERT INTO process_calc_rules
            (process_name, product_types_json, condition_expr, planned_qty_formula,
             priority, enabled, created_at, updated_at, default_worker, unit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            update_sql = """
            UPDATE process_calc_rules SET
                product_types_json = ?,
                condition_expr = ?,
                planned_qty_formula = ?,
                priority = ?,
                enabled = ?,
                updated_at = ?,
                default_worker = ?,
                unit = ?
            WHERE process_name = ?
            """
        else:
            insert_sql = """
            INSERT INTO process_calc_rules
            (process_name, product_types_json, condition_expr, planned_qty_formula,
             priority, enabled, created_at, updated_at, default_worker, unit)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            update_sql = """
            UPDATE process_calc_rules SET
                product_types_json = %s,
                condition_expr = %s,
                planned_qty_formula = %s,
                priority = %s,
                enabled = %s,
                updated_at = %s,
                default_worker = %s,
                unit = %s
            WHERE process_name = %s
            """

        for rule in rules:
            try:
                process_name = rule.get('process_name', '')
                if not process_name:
                    logger.warning(f"规则缺少process_name，跳过: {rule}")
                    stats['skipped'] += 1
                    continue

                # 检查是否已存在
                existing = self._get_by_process_name(process_name)

                # 准备数据
                product_types = rule.get('product_types_json', '')
                if isinstance(product_types, list):
                    product_types = json.dumps(product_types, ensure_ascii=False)
                condition_expr = rule.get('condition_expr', '所有产品类型')
                planned_qty = rule.get('planned_qty_formula', '')
                priority = int(rule.get('priority', 5))
                enabled = 1 if rule.get('enabled', 1) else 0
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                created_at = rule.get('created_at', now)
                updated_at = rule.get('updated_at', now)
                default_worker = rule.get('default_worker', '')
                unit = rule.get('unit', '件')

                if existing:
                    # 更新
                    params = (
                        product_types, condition_expr, planned_qty,
                        priority, enabled, updated_at, default_worker, unit,
                        process_name
                    )
                    with db.get_cursor() as cursor:
                        cursor.execute(update_sql, params)
                    stats['updated'] += 1
                    logger.debug(f"更新规则: {process_name}")
                else:
                    # 插入
                    params = (
                        process_name, product_types, condition_expr, planned_qty,
                        priority, enabled, created_at, updated_at, default_worker, unit
                    )
                    with db.get_cursor() as cursor:
                        cursor.execute(insert_sql, params)
                    stats['inserted'] += 1
                    logger.debug(f"插入规则: {process_name}")

            except Exception as e:
                logger.error(f"同步规则失败 {rule.get('process_name', 'unknown')}: {e}")
                stats['errors'] += 1

        return stats

    def _get_by_process_name(self, process_name: str) -> Optional[Dict]:
        """根据工序名称查询规则"""
        try:
            with db.get_cursor(commit=False) as cursor:
                if is_sqlite():
                    cursor.execute(
                        "SELECT * FROM process_calc_rules WHERE process_name = ?",
                        (process_name,)
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM process_calc_rules WHERE process_name = %s",
                        (process_name,)
                    )
                result = cursor.fetchone()
                return result if result else None
        except Exception as e:
            logger.error(f"查询规则失败: {e}")
            return None

    def get_target_count(self) -> int:
        """获取目标数据库中的规则数量"""
        try:
            with db.get_cursor(commit=False) as cursor:
                cursor.execute("SELECT COUNT(*) as cnt FROM process_calc_rules")
                result = cursor.fetchone()
                if result:
                    return result['cnt'] if isinstance(result, dict) else result[0]
                return 0
        except Exception as e:
            logger.error(f"获取数量失败: {e}")
            return 0


def main():
    """主函数"""
    print("=" * 60)
    print("工序计算规则数据同步工具")
    print("=" * 60)
    print()

    # 确保目录存在
    db_path = get_sqlite_path()
    ensure_dir(os.path.dirname(db_path))

    sync = ProcessRuleSync()

    # 1. 加载源数据
    print("[1/4] 加载源数据...")
    rules = sync.load_source_data()
    print(f"      加载了 {len(rules)} 条规则")
    print()

    # 2. 创建目标表
    print("[2/4] 创建目标表...")
    sync.create_target_table()
    print("      完成")
    print()

    # 3. 同步数据
    print("[3/4] 同步数据到目标数据库...")
    stats = sync.sync_to_target(rules)
    print(f"      总数: {stats['total']}")
    print(f"      新增: {stats['inserted']}")
    print(f"      更新: {stats['updated']}")
    print(f"      跳过: {stats['skipped']}")
    print(f"      错误: {stats['errors']}")
    print()

    # 4. 验证结果
    print("[4/4] 验证结果...")
    target_count = sync.get_target_count()
    print(f"      目标数据库现有 {target_count} 条规则")
    print()

    print("=" * 60)
    if stats['errors'] == 0:
        print("同步完成！")
    else:
        print(f"同步完成，但有 {stats['errors']} 个错误")
    print("=" * 60)

    return stats


if __name__ == "__main__":
    # 设置SQLite模式（默认使用SQLite）
    os.environ['USE_SQLITE'] = 'true'

    result = main()
    sys.exit(0 if result['errors'] == 0 else 1)
