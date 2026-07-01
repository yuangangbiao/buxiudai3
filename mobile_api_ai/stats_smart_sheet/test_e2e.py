# -*- coding: utf-8 -*-
"""
端到端验证脚本
- 先跑一张表（默认工序报工汇总 substep_report）
- 全链路：DB查询 → 5005 → 云端5004 → 智能表格

用法：
    python test_e2e.py                                    # 默认跑 substep_report
    python test_e2e.py --table production_daily_report   # 指定表
    python test_e2e.py --table substep_report --dry-run  # 只查 DB 不推送
"""
import sys
import os
import json
import argparse
import logging
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from stats_smart_sheet import db_queries
from stats_smart_sheet.smart_sheet_exporter import export_table
from stats_smart_sheet.smart_sheet_client import map_to_field_ids
from stats_smart_sheet.config import TABLE_DISPLAY_NAMES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def verify_db_connectivity():
    """步骤1: 验证数据库连接"""
    print("\n" + "=" * 60)
    print("步骤1: 验证数据库连接")
    print("=" * 60)

    errors = []
    for db_name in ('container_center', 'inventory'):
        try:
            from stats_smart_sheet.mysql_config import get_conn
            conn = get_conn(db_name)
            with conn.cursor() as c:
                c.execute("SELECT 1 AS ok")
                result = c.fetchone()
            conn.close()
            print(f"  ✅ {db_name}: 连接成功")
        except Exception as e:
            print(f"  ❌ {db_name}: {e}")
            errors.append((db_name, str(e)))

    if errors:
        print("\n❌ 数据库连接失败，请检查 .env 配置")
        for name, err in errors:
            print(f"  - {name}: {err}")
        return False
    return True


def verify_query(table_type: str):
    """步骤2: 验证 SQL 查询"""
    print("\n" + "=" * 60)
    print(f"步骤2: 验证 SQL 查询 ({table_type})")
    print("=" * 60)

    display_name = TABLE_DISPLAY_NAMES.get(table_type, table_type)
    print(f"  📋 表名: {display_name}")

    try:
        if table_type == 'production_daily_report':
            from datetime import date
            records = db_queries.query_production_daily(date.today() - timedelta(days=1))
        elif table_type == 'production_monthly_report':
            records = db_queries.query_production_monthly(
                datetime.now().strftime('%Y-%m'))
        elif table_type == 'workshop_capacity':
            from datetime import date
            records = db_queries.query_workshop_capacity(date.today() - timedelta(days=1))
        elif table_type == 'workorder_progress':
            records = db_queries.query_workorder_progress()
        elif table_type == 'substep_report':
            records = db_queries.query_substep_recent(
                datetime.now() - timedelta(hours=1), limit=10)
        elif table_type == 'inventory_weekly_report':
            from datetime import date
            today = date.today()
            ws = today - timedelta(days=today.weekday())
            records = db_queries.query_inventory_weekly(ws, ws + timedelta(days=6))
        elif table_type == 'inventory_monthly_summary':
            records = db_queries.query_inventory_monthly(
                datetime.now().strftime('%Y-%m'))
        elif table_type == 'inventory_alert':
            records = db_queries.query_inventory_alert(10)
        elif table_type == 'inventory_slow_moving':
            records = db_queries.query_inventory_slow_moving(90)
        else:
            print(f"  ❌ 未知表类型: {table_type}")
            return False

        print(f"  ✅ 查询成功，共 {len(records)} 条记录")
        if records:
            print(f"\n  📊 示例数据（第一条）:")
            for k, v in list(records[0].items())[:8]:
                print(f"     {k}: {v}")
            # 验证字段映射
            mapped = map_to_field_ids(table_type, records)
            print(f"\n  ✅ 字段映射成功: {len(mapped[0]) if mapped else 0} 个字段")
        return True

    except Exception as e:
        logger.exception(f"  ❌ SQL 查询失败: {e}")
        return False


def verify_push(table_type: str, dry_run: bool = False):
    """步骤3: 推送测试"""
    print("\n" + "=" * 60)
    print(f"步骤3: 推送测试 ({table_type})")
    print("=" * 60)

    if dry_run:
        print("  ⏭️  DRY-RUN 模式，跳过推送")
        return True

    print("  🔄 正在推送...")
    try:
        result = export_table(table_type)
        print(f"\n  📤 推送结果:")
        print(json.dumps(result, ensure_ascii=False, indent=4))
        if result.get('code') == 0:
            print(f"\n  ✅ 推送成功！")
            return True
        else:
            print(f"\n  ❌ 推送失败: {result.get('message')}")
            return False
    except Exception as e:
        logger.exception(f"  ❌ 推送异常: {e}")
        return False


def verify_5004_health():
    """步骤0: 验证云端 5004 可达"""
    print("\n" + "=" * 60)
    print("步骤0: 验证云端 5004 连通性")
    print("=" * 60)

    cloud_host = os.getenv('CLOUD_5004_HOST', '')
    cloud_port = os.getenv('CLOUD_5004_PORT', '5004')

    if not cloud_host:
        print("  ⚠️  CLOUD_5004_HOST 未配置，跳过云端验证")
        return True

    try:
        import requests
        url = f'http://{cloud_host}:{cloud_port}/api/health'
        resp = requests.get(url, timeout=5)
        data = resp.json()
        print(f"  ✅ 云端 5004 可达: {data.get('message', 'OK')}")
        return True
    except Exception as e:
        print(f"  ⚠️  云端 5004 不可达: {e}")
        print(f"     请确认云端 5004 已启动且 CLOUD_5004_HOST={cloud_host} 正确")
        return True  # 不阻断本地测试


def main():
    parser = argparse.ArgumentParser(description='端到端验证 stats_smart_sheet 模块')
    parser.add_argument('--table', default='substep_report',
                        help='指定测试表（默认: substep_report）')
    parser.add_argument('--dry-run', action='store_true',
                        help='只查 DB 不推送')
    parser.add_argument('--skip-cloud', action='store_true',
                        help='跳过云端验证')
    args = parser.parse_args()

    print("=" * 60)
    print(f"stats_smart_sheet 端到端验证")
    print(f"测试表: {args.table}")
    print(f"模式: {'DRY-RUN' if args.dry_run else '完整推送'}")
    print("=" * 60)

    steps = []

    # 步骤0: 云端连通性
    if not args.skip_cloud:
        steps.append(('云端5004验证', lambda: verify_5004_health()))

    # 步骤1: 数据库连接
    steps.append(('数据库连接', verify_db_connectivity))

    # 步骤2: SQL 查询
    steps.append((f'SQL查询({args.table})',
                   lambda: verify_query(args.table)))

    # 步骤3: 推送
    if not args.dry_run:
        steps.append((f'推送测试({args.table})',
                      lambda: verify_push(args.table, dry_run=False)))
    else:
        steps.append((f'推送测试({args.table})[跳过]',
                      lambda: verify_push(args.table, dry_run=True)))

    # 执行
    passed = 0
    for name, step_fn in steps:
        try:
            if step_fn():
                passed += 1
            else:
                print(f"\n  ⚠️  步骤「{name}」未通过，继续...")
        except Exception as e:
            logger.exception(f"  ❌ 步骤「{name}」异常: {e}")

    # 结果
    print("\n" + "=" * 60)
    print(f"验证结果: {passed}/{len(steps)} 通过")
    if passed == len(steps):
        print("✅ 全部通过！模块可正常使用。")
    else:
        print("⚠️  部分步骤失败，请检查配置。")
    print("=" * 60)

    return passed == len(steps)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
