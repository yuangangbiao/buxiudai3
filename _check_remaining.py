# -*- coding: utf-8 -*-
import sqlite3, json, os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mobile_api_ai')

for db_name in ['wechat_container.db', 'container_center.db']:
    path = os.path.join(BASE, db_name)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print(f'\n=== {db_name} - Missing process_code ===')
    cur.execute(
        "SELECT rowid, content, related_order, related_process FROM data_packages "
        "WHERE json_extract(content, '$.process_code') IS NULL "
        "OR json_extract(content, '$.process_code') = ''"
    )
    for r in cur.fetchall():
        c = json.loads(r['content']) if isinstance(r['content'], str) else r['content']
        print(f'  rowid={r["rowid"]} '
              f'related_process={r["related_process"]!r} '
              f'content_keys={list(c.keys())[:8] if isinstance(c, dict) else type(c).__name__} '
              f'process_name={c.get("process_name","N/A") if isinstance(c, dict) else "N/A"}')

    print(f'\n=== {db_name} - Missing order_no ===')
    cur.execute(
        "SELECT rowid, content, related_order, related_process FROM data_packages "
        "WHERE json_extract(content, '$.order_no') IS NULL "
        "OR json_extract(content, '$.order_no') = ''"
    )
    for r in cur.fetchall():
        c = json.loads(r['content']) if isinstance(r['content'], str) else r['content']
        print(f'  rowid={r["rowid"]} '
              f'related_order={r["related_order"]!r} '
              f'content_order_no={c.get("order_no","N/A") if isinstance(c, dict) else "N/A"}')

    conn.close()
