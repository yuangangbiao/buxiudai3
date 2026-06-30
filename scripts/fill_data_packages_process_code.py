# -*- coding: utf-8 -*-
"""
R12 ETL: 回填 data_packages.process_code 老数据

源数据:
  - data_packages.content JSON (含 process_name / process_code)
  - data_packages.related_process 字符串
  - data_packages.data_type 字段

SSOT:
  - core._config_domain.PROCESS_CODES (20 项 + 自定义)
  - core.config.get_process_code(name) 动态 P17+ 分配

回填规则:
  1. data_packages.content.process_code 优先(若已存, 不动)
  2. 否则用 data_packages.content.process_name → get_process_code()
  3. 否则用 data_packages.related_process → get_process_code()
  4. 都不匹配 → 留空(后续写新数据时再补)
  5. 批量 UPDATE 500 行/批,带 audit log

回填范围:
  - WHERE process_code IS NULL OR process_code = ''
  - 排除 ATTEND_ / ORD-SCAN- 测试工单

Usage:
    python scripts/fill_data_packages_process_code.py            # 默认回填
    python scripts/fill_data_packages_process_code.py --dry-run # 只统计, 不写
    python scripts/fill_data_packages_process_code.py --batch 200
"""
from __future__ import annotations
import os
import sys
import json
import time
import argparse
import logging
from typing import Dict, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# 自动加载 .env (项目根, 强制覆盖避免外部空值污染)
_env_path = os.path.join(ROOT, '.env')
if os.path.exists(_env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path, override=True)
    except ImportError:
        # 无 dotenv 时手解 KV
        with open(_env_path, 'r', encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith('#') or '=' not in _line:
                    continue
                _k, _v = _line.split('=', 1)
                _k = _k.strip()
                _v = _v.strip().strip('"').strip("'")
                os.environ[_k] = _v

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('r12_etl')


def _parse_content(content) -> dict:
    """安全解析 content (json str / dict / None)"""
    if not content:
        return {}
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _resolve_process_code(row: dict) -> str:
    """从 data_package row 反推 process_code

    Returns
    -------
    str
        编码如 "P01"/"M01"/"Q01"/"X01"/"P_CS" 或动态 "P17"; 找不到返回 ''。
    """
    try:
        from core.config import get_process_code
    except Exception:
        return ''

    content = _parse_content(row.get('content'))
    # 1. content 里有 process_code → 直接用
    pc = (content.get('process_code') or '').strip()
    if pc:
        return pc

    # 2. content.process_name → get_process_code
    pn = (content.get('process_name') or '').strip()
    if pn:
        code = get_process_code(pn)
        if code and not code.startswith('PX'):  # 排除 hash4 fallback
            return code

    # 3. related_process → get_process_code
    rp = (row.get('related_process') or '').strip()
    if rp:
        code = get_process_code(rp)
        if code and not code.startswith('PX'):
            return code

    return ''


def _is_test_order(order_no: str) -> bool:
    """排除测试工单 (ATTEND_ / ORD-SCAN-)"""
    if not order_no:
        return False
    return order_no.startswith('ATTEND_') or order_no.startswith('ORD-SCAN-')


def main():
    parser = argparse.ArgumentParser(description='R12 ETL: 回填 data_packages.process_code')
    parser.add_argument('--dry-run', action='store_true', help='只统计, 不写库')
    parser.add_argument('--batch', type=int, default=500, help='每批行数 (默认 500)')
    parser.add_argument('--limit', type=int, default=0, help='最多处理多少行 (0=无限)')
    args = parser.parse_args()

    # 1. 连接 MySQL (container_center 库, 跟 data_packages 同库)
    try:
        import pymysql
    except ImportError:
        logger.error('pymysql 未安装,请先 pip install pymysql')
        sys.exit(1)

    mysql_cfg = {
        'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('CONTAINER_MYSQL_DATABASE') or os.getenv('INVENTORY_DB_NAME', 'container_center'),
        'charset': 'utf8mb4',
    }
    logger.info('连接 MySQL %s:%s/%s (user=%s, pw_len=%d)',
                mysql_cfg['host'], mysql_cfg['port'], mysql_cfg['database'],
                mysql_cfg['user'], len(mysql_cfg['password']))

    conn = pymysql.connect(**mysql_cfg, autocommit=False, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            # 2. 统计待回填数
            cur.execute("""
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN related_order LIKE 'ATTEND\\_%' OR related_order LIKE 'ORD-SCAN-%' THEN 1 ELSE 0 END) AS test_orders,
                       SUM(CASE WHEN related_order IS NULL OR related_order = '' THEN 1 ELSE 0 END) AS no_order
                FROM data_packages
                WHERE process_code IS NULL OR process_code = ''
            """)
            stats = cur.fetchone()
            logger.info('待回填统计: total=%d  测试工单=%d  无订单=%d',
                        stats['total'] or 0, stats['test_orders'] or 0, stats['no_order'] or 0)

            if (stats['total'] or 0) == 0:
                logger.info('没有需要回填的数据, 退出')
                return

            if args.dry_run:
                logger.info('--dry-run 模式, 不写库, 退出')
                return

            # 3. 分批拉取待回填行 (LIMIT 控制)
            offset = 0
            total_updated = 0
            total_skipped = 0
            total_no_match = 0
            batch_size = args.batch
            limit = args.limit if args.limit > 0 else 10**9
            t0 = time.time()

            while total_updated + total_skipped < limit:
                cur.execute("""
                    SELECT id, data_type, content, related_process, related_order
                    FROM data_packages
                    WHERE process_code IS NULL OR process_code = ''
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (batch_size, offset))
                rows = cur.fetchall()
                if not rows:
                    break
                offset += batch_size

                # 当前批处理
                updates: list = []
                for row in rows:
                    rid = row['id']
                    order_no = row.get('related_order') or ''

                    # 跳过测试工单
                    if _is_test_order(order_no):
                        total_skipped += 1
                        continue

                    code = _resolve_process_code(row)
                    if not code:
                        total_no_match += 1
                        continue

                    updates.append((code, rid))

                # 批量 UPDATE (executemany)
                if updates:
                    cur.executemany(
                        "UPDATE data_packages SET process_code=%s WHERE id=%s",
                        updates
                    )
                    conn.commit()
                    total_updated += len(updates)
                    logger.info('  批次 %d-%d: 更新 %d 行 (累计 %d)',
                                offset - batch_size + 1, offset, len(updates), total_updated)

                # 防止单批死循环
                if len(rows) < batch_size:
                    break

            elapsed = time.time() - t0
            logger.info('=' * 60)
            logger.info('回填完成:')
            logger.info('  更新行数:    %d', total_updated)
            logger.info('  跳过(测试): %d', total_skipped)
            logger.info('  无匹配:     %d', total_no_match)
            logger.info('  耗时:       %.1fs', elapsed)
            logger.info('=' * 60)

            # 4. 验证: 统计回填后的覆盖率
            cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN process_code IS NULL OR process_code = '' THEN 1 ELSE 0 END) AS empty_cnt,
                    SUM(CASE WHEN process_code LIKE 'P%%' THEN 1 ELSE 0 END) AS process_cnt,
                    SUM(CASE WHEN process_code LIKE 'M%%' THEN 1 ELSE 0 END) AS material_cnt,
                    SUM(CASE WHEN process_code LIKE 'Q%%' THEN 1 ELSE 0 END) AS quality_cnt,
                    SUM(CASE WHEN process_code LIKE 'X%%' THEN 1 ELSE 0 END) AS outsource_cnt
                FROM data_packages
            """)
            cov = cur.fetchone()
            total_all = cov['total'] or 1
            filled = total_all - (cov['empty_cnt'] or 0)
            logger.info('覆盖率验证:')
            logger.info('  总行数:    %d', total_all)
            logger.info('  已填充:    %d (%.1f%%)', filled, 100 * filled / total_all)
            logger.info('  仍为空:    %d', cov['empty_cnt'] or 0)
            logger.info('  P 工序:    %d', cov['process_cnt'] or 0)
            logger.info('  M 物料:    %d', cov['material_cnt'] or 0)
            logger.info('  Q 质检:    %d', cov['quality_cnt'] or 0)
            logger.info('  X 外协:    %d', cov['outsource_cnt'] or 0)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
