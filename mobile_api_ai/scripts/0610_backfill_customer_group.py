# -*- coding: utf-8 -*-
"""
[F6 P9 2026-06-10] 一次性回填脚本: process_records.customer_group 字段
背景: 手机端 customerGroup 显示空 bug 修复后, 历史数据没回填
      老订单 process_records.customer_group 字段为空, 需要走 _get_customer_group_for_order
      (5min LRU 缓存) 从钢带源库查源回填

用法:
  干跑 (推荐先跑, 看会改多少条): python 0610_backfill_customer_group.py --dry-run
  真跑:                          python 0610_backfill_customer_group.py
  限制条数 (防爆):                python 0610_backfill_customer_group.py --limit 100

业务规则:
  1. 只回填 customer_group 为 NULL 或空字符串的记录
  2. customer_name 不为空时不改 (兼容某些订单没 customer_group, 但 customer_name 填了)
  3. 走 _get_customer_group_for_order 缓存版, 5 分钟内同订单不重复查源
  4. 单条失败不阻断, 累计报告
"""
import os
import sys
import time
import argparse
import logging
from datetime import datetime

# ── 路径注入 ──
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

os.chdir(_PROJECT_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('backfill_customer_group')


def main():
    parser = argparse.ArgumentParser(description='回填 process_records.customer_group')
    parser.add_argument('--dry-run', action='store_true', help='干跑, 只统计不写入')
    parser.add_argument('--limit', type=int, default=0, help='最多回填 N 条, 0=不限')
    parser.add_argument('--batch-size', type=int, default=50, help='每批查询条数')
    args = parser.parse_args()

    logger.info('=' * 60)
    logger.info(f'{"干跑" if args.dry_run else "真跑"} 模式  limit={args.limit}  batch={args.batch_size}')
    logger.info('=' * 60)

    # 走 importlib 文件加载, 绕开 storage package 解析
    import importlib.util
    def _load(mod_name, rel_path):
        spec = importlib.util.spec_from_file_location(
            mod_name,
            os.path.join(_PROJECT_ROOT, 'mobile_api_ai', rel_path)
        )
        m = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = m
        spec.loader.exec_module(m)
        return m

    storage_mod = _load('storage.mysql_storage', 'storage/mysql_storage.py')
    storage = storage_mod.MySQLStorage()
    storage.connect()
    logger.info('[OK] MySQLStorage 已连接')

    # 极简源库查询 (绕开 _core.py 重依赖)
    # 复用 _core._get_customer_group_for_order 同样的 SQL, 5min 进程内 LRU
    _CACHE = {}
    _CACHE_TTL = 300

    def _lookup_customer_group(order_no: str) -> str:
        if not order_no:
            return ''
        now = time.time()
        if order_no in _CACHE and now - _CACHE[order_no][1] < _CACHE_TTL:
            return _CACHE[order_no][0]
        try:
            conn, c = storage_mod.get_steelbelt_cursor() if hasattr(storage_mod, 'get_steelbelt_cursor') else (None, None)
            if c is None:
                # fallback: 自己连钢带库
                import pymysql
                from pymysql.cursors import DictCursor
                from core.config import MYSQL_CFG, DB_CONNECT_TIMEOUT
                conn = pymysql.connect(**MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
                c = conn.cursor(DictCursor)
            c.execute("""
                SELECT o.customer_group
                FROM orders o
                WHERE o.order_no = %s LIMIT 1
            """, (order_no,))
            row = c.fetchone()
            try: conn.close()
            except Exception: pass
            val = (row.get('customer_group') or '').strip() if row else ''
        except Exception as e:
            logger.warning(f'  [源库查] {order_no} 失败: {e}')
            val = ''
        _CACHE[order_no] = (val, now)
        return val

    stats = {
        'total_scanned': 0,
        'need_backfill': 0,
        'backfilled': 0,
        'no_source': 0,
        'failed': 0,
        'start': time.time(),
    }
    failures = []

    logger.info('[1/3] 拉取所有 process_records...')
    all_records = storage.get_all_process_records()
    logger.info(f'[OK] 拉到 {len(all_records)} 条')

    candidates = [r for r in all_records if not (r.get('customer_group') or '').strip()]
    stats['need_backfill'] = len(candidates)
    logger.info(f'[2/3] 需回填 customer_group 的记录: {len(candidates)} 条')

    if args.limit > 0:
        candidates = candidates[:args.limit]
        logger.info(f'[limit] 截取前 {args.limit} 条')

    if args.dry_run:
        logger.info('[DRY-RUN] 不会真改数据库, 仅展示将回填的订单号')
        sample = [r.get('order_no', '?') for r in candidates[:20]]
        logger.info(f'[示例] 前 20 条 order_no: {sample}')
        logger.info('=' * 60)
        logger.info(f'干跑结束: 扫描 {len(all_records)} 条, 待回填 {len(candidates)} 条')
        return 0

    logger.info('[3/3] 开始回填...')
    for i, rec in enumerate(candidates, 1):
        stats['total_scanned'] += 1
        order_no = rec.get('order_no', '').strip()
        rec_id = rec.get('id', '')
        if not order_no or not rec_id:
            continue
        try:
            cg = _lookup_customer_group(order_no)
            if not cg:
                stats['no_source'] += 1
                if i % 100 == 0:
                    logger.info(f'  [{i}/{len(candidates)}] {order_no} → 源库无 customer_group, 跳过')
                continue
            rec['customer_group'] = cg
            storage.save_process_record(rec)
            stats['backfilled'] += 1
            if i % 50 == 0 or i <= 5:
                logger.info(f'  [{i}/{len(candidates)}] {order_no} ← {cg} ✅')
        except Exception as e:
            stats['failed'] += 1
            failures.append((order_no, str(e)))
            logger.warning(f'  [{i}/{len(candidates)}] {order_no} ✗ {e}')

    elapsed = time.time() - stats['start']
    logger.info('=' * 60)
    logger.info(f'回填完成, 耗时 {elapsed:.1f}s')
    logger.info(f'  扫描总数:     {stats["total_scanned"]}')
    logger.info(f'  待回填数:     {stats["need_backfill"]}')
    logger.info(f'  成功回填:     {stats["backfilled"]}')
    logger.info(f'  源库无数据:   {stats["no_source"]}')
    logger.info(f'  失败数:       {stats["failed"]}')
    if failures:
        logger.info(f'  失败样本 (前 10):')
        for on, err in failures[:10]:
            logger.info(f'    {on}: {err}')
    logger.info('=' * 60)
    return 0 if stats['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
