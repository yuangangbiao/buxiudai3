"""迁移 dispatch_center_data.json 中的工序任务到 process_records 表"""
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_FILE = os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'dispatch_center_data.json')
DB_PATH = os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'wechat_container.db')


def get_process_records_ids(cur):
    cur.execute('SELECT id FROM process_records')
    return {row[0] for row in cur.fetchall()}


def main():
    if not os.path.exists(CACHE_FILE):
        print(f"[错误] dispatch_center_data.json 不存在: {CACHE_FILE}")
        sys.exit(1)

    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)

    processes = cache_data.get('processes', [])
    if not processes:
        print("dispatch_center_data.json 中无工序数据，无需迁移")
        return

    import sqlite3
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()

    existing_ids = get_process_records_ids(cur)
    imported = 0
    skipped = 0

    for p in processes:
        pid = p.get('id', '')
        if not pid or pid in existing_ids:
            skipped += 1
            continue

        steps = p.get('steps', [])
        steps_json = json.dumps(steps, ensure_ascii=False) if isinstance(steps, list) else steps

        cur.execute('''
            INSERT OR REPLACE INTO process_records
            (id, process_type, order_no, order_no, product_name, quantity, unit,
             status, current_step, steps, source, flow_type,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pid,
            p.get('flow_type', p.get('process_type', 'production')),
            p.get('order_no', ''),
            p.get('order_no', ''),
            p.get('product_name', ''),
            p.get('quantity', 0),
            p.get('unit', '件'),
            p.get('status', 'created'),
            p.get('current_step', 0),
            steps_json,
            p.get('source', 'migration'),
            p.get('flow_type', 'production'),
            p.get('created_at', datetime.now().isoformat()),
            p.get('updated_at', datetime.now().isoformat()),
        ))
        imported += 1

    db.commit()
    db.close()

    print(f"迁移完成: 导入 {imported} 条, 跳过(已存在) {skipped} 条, 总计 {len(processes)} 条")


if __name__ == '__main__':
    main()
