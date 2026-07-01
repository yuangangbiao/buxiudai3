# -*- coding: utf-8 -*-
"""
[F6 P9 2026-06-10] 一次性去重脚本: process_records 同 order_no 多余副本
背景: 客户群回填脚本发现 ORD-202604210004 有 13 条 process_records 重复
      12 条 status=created 是重复派工 bug 残留 (created_at 23:06:07~23:07:02 同分钟内)
      1 条 status=in_production 是真实业务记录 (created_at 22:46:59)

保留规则 (每组 order_no):
  1. 优先保留 status != 'created' 的 (真实业务记录)
  2. 多个真实业务记录 → 保留 created_at 最大的 (最新)
  3. 全是 created → 保留 created_at 最大的 (最新)
  其他全部 DELETE

用法:
  干跑: python 0610_dedup_process_records.py --dry-run
  真跑: python 0610_dedup_process_records.py
"""
import os
import sys
import time
import argparse
import logging
import importlib.util
from collections import defaultdict

_PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
sys.path.insert(0, _PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('dedup_process_records')


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_PROJECT_ROOT, 'mobile_api_ai', rel)
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def main():
    parser = argparse.ArgumentParser(description='process_records 去重')
    parser.add_argument('--dry-run', action='store_true', help='干跑, 只统计不写')
    args = parser.parse_args()

    logger.info('=' * 60)
    logger.info(f'{"干跑" if args.dry_run else "真跑"} 模式')
    logger.info('=' * 60)

    mod = _load('storage.mysql_storage', 'storage/mysql_storage.py')
    storage = mod.MySQLStorage()
    storage.connect()
    logger.info('[OK] MySQLStorage 已连接')

    records = storage.get_all_process_records()
    logger.info(f'[1/3] 拉取 {len(records)} 条 process_records')

    groups = defaultdict(list)
    for r in records:
        groups[r.get('order_no', '')].append(r)

    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
    logger.info(f'[2/3] 发现 {len(dup_groups)} 个 order_no 有重复 (共 {sum(len(v) for v in dup_groups.values())} 条)')

    if not dup_groups:
        logger.info('无需去重, 退出')
        return 0

    to_delete = []
    for order_no, recs in dup_groups.items():
        # 排序: 业务状态优先 (非 created), 然后 created_at 最大
        def sort_key(r):
            is_business = 0 if r.get('status') != 'created' else 1
            created_at = r.get('created_at') or ''
            return (is_business, -ord(created_at[0]) if created_at else 0, created_at)
        recs_sorted = sorted(recs, key=sort_key)
        keep = recs_sorted[0]
        drop = recs_sorted[1:]
        logger.info(f'  {order_no} ({len(recs)} 条) → 保留 id={keep.get("id")} status={keep.get("status")} created_at={keep.get("created_at")}')
        for d in drop:
            logger.info(f'    删除 id={d.get("id")} status={d.get("status")} created_at={d.get("created_at")}')
            to_delete.append(d.get('id'))

    logger.info(f'[3/3] 将删除 {len(to_delete)} 条')

    if args.dry_run:
        logger.info('[DRY-RUN] 不会真改数据库')
        return 0

    deleted = 0
    failed = 0
    for rid in to_delete:
        if not rid:
            continue
        try:
            n = storage.execute('DELETE FROM process_records WHERE id = %s', (str(rid),))
            if n > 0:
                deleted += 1
        except Exception as e:
            failed += 1
            logger.warning(f'  删除 id={rid} 失败: {e}')

    logger.info('=' * 60)
    logger.info(f'去重完成: 删除 {deleted} 条, 失败 {failed} 条')
    logger.info('=' * 60)
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
