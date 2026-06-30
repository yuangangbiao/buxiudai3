# -*- coding: utf-8 -*-
"""
SQLite 数据回填脚本
为 data_packages 表的 content JSON 补充 process_code + order_no
"""

import sqlite3, json, hashlib, sys, os

# 工序编码映射（与 core/config.py PROCESS_CODES 一致）
PROCESS_CODES = {
    '原材料准备': 'P01',
    '焊接眼镜网': 'P02',
    '激光切板': 'P03',
    '链板冲压孔': 'P04',
    '链板冲压成型': 'P05',
    '编制左旋': 'P06',
    '编制右旋': 'P07',
    '穿曲轴': 'P08',
    '输送带组装穿杆': 'P09',
    '安装链条': 'P10',
    '安装裙边': 'P11',
    '整形校直': 'P12',
    '焊接输送带': 'P13',
    '表面处理': 'P14',
    '质量检验': 'P15',
    '包装入库': 'P16',
}


def get_process_code(name):
    """获取工序编码"""
    if not name:
        return ''
    code = PROCESS_CODES.get(name)
    if code:
        return code
    return 'PX' + hashlib.md5(name.encode()).hexdigest()[:4].upper()


def backfill_one_db(db_path):
    """回填单个 SQLite 数据库"""
    if not os.path.exists(db_path):
        return 0, 0

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 先检查表和数据
    cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='data_packages'")
    if cur.fetchone()[0] == 0:
        conn.close()
        return 0, 0

    cur.execute("SELECT COUNT(*) FROM data_packages")
    total = cur.fetchone()[0]

    cur.execute("SELECT rowid, content, related_order, related_process FROM data_packages")
    updated = 0
    for row in cur.fetchall():
        content = row['content']
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                content = {}
        if content is None:
            content = {}
        if isinstance(content, str):
            continue

        changed = False

        # 补充 process_code
        if not content.get('process_code'):
            pname = content.get('process_name', '') or row['related_process'] or ''
            if pname:
                content['process_code'] = get_process_code(pname)
                changed = True

        # 补充 order_no
        if not content.get('order_no'):
            ono = content.get('order_no', '') or row['related_order'] or ''
            if ono:
                content['order_no'] = ono
                changed = True

        if changed:
            cur.execute(
                "UPDATE data_packages SET content=? WHERE rowid=?",
                (json.dumps(content, ensure_ascii=False), row['rowid'])
            )
            updated += 1

    conn.commit()

    # 验证
    missing_pc = cur.execute(
        "SELECT COUNT(*) FROM data_packages WHERE json_extract(content, '$.process_code') IS NULL OR json_extract(content, '$.process_code') = ''"
    ).fetchone()[0]
    missing_on = cur.execute(
        "SELECT COUNT(*) FROM data_packages WHERE json_extract(content, '$.order_no') IS NULL OR json_extract(content, '$.order_no') = ''"
    ).fetchone()[0]

    conn.close()
    return total, updated, missing_pc, missing_on


def main():
    BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mobile_api_ai')
    dbs = ['wechat_container.db', 'container_center.db']

    grand_total = 0
    grand_updated = 0

    for db_name in dbs:
        path = os.path.join(BASE, db_name)
        print(f'[{db_name}]', flush=True)
        result = backfill_one_db(path)
        if result == (0, 0):
            print(f'  SKIP: no data_packages table or file missing', flush=True)
            continue
        total, updated, missing_pc, missing_on = result
        print(f'  Total packages: {total}', flush=True)
        print(f'  Updated: {updated}', flush=True)
        print(f'  Remaining missing process_code: {missing_pc}', flush=True)
        print(f'  Remaining missing order_no: {missing_on}', flush=True)
        grand_total += total
        grand_updated += updated

    print(f'\n=== SUMMARY ===', flush=True)
    print(f'Total packages across all DBs: {grand_total}', flush=True)
    print(f'Total updated: {grand_updated}', flush=True)
    print('DONE.', flush=True)


if __name__ == '__main__':
    main()
