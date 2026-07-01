# -*- coding: utf-8 -*-
"""
智能表格台账管理模块
负责：注册、查询、更新、删除 已创建的智能表格记录
台账文件: smartsheet_ledger.json
"""
import json, os, datetime

LEDGER_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), 'smartsheet_ledger.json')
)

def _load():
    if not os.path.exists(LEDGER_PATH):
        return {'version': 1, 'updated_at': '', 'tables': []}
    with open(LEDGER_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def _save(data):
    data['updated_at'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    with open(LEDGER_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _next_id(data):
    ids = [t['id'] for t in data['tables'] if t['id'].startswith('table_')]
    nums = []
    for tid in ids:
        parts = tid.rsplit('_', 1)
        if parts[-1].isdigit():
            nums.append(int(parts[-1]))
    return max(nums) + 1 if nums else 1

def register(docid, s3_id, url, name='', sheet_id='', sheet_name='',
             fields=None, record_count=0, purpose='', created_via='formal_api',
             tags=None):
    data = _load()
    entry = {
        'id': f'table_{created_via}_{_next_id(data):03d}',
        'name': name,
        'docid': docid,
        's3_id': s3_id,
        'url': url,
        'sheet_id': sheet_id,
        'sheet_name': sheet_name,
        'fields': fields or [],
        'record_count': record_count,
        'purpose': purpose,
        'created_via': created_via,
        'created_at': datetime.datetime.now().strftime('%Y-%m-%d'),
        'status': 'active',
        'tags': tags or [],
    }
    data['tables'].append(entry)
    _save(data)
    return entry['id']

def query(tag=None, status=None, name=None, docid=None):
    data = _load()
    results = data['tables']
    if tag:
        results = [t for t in results if tag in t.get('tags', [])]
    if status:
        results = [t for t in results if t.get('status') == status]
    if name:
        results = [t for t in results if name in t.get('name', '')]
    if docid:
        results = [t for t in results if t.get('docid') == docid]
    return results

def get_active():
    return query(status='active')

def get_by_docid(docid):
    results = query(docid=docid)
    return results[0] if results else None

def get_by_s3(s3_id):
    data = _load()
    for t in data['tables']:
        if t.get('s3_id') == s3_id:
            return t
    return None

def update(table_id, **kwargs):
    data = _load()
    for t in data['tables']:
        if t['id'] == table_id:
            for k, v in kwargs.items():
                if v is not None:
                    t[k] = v
            _save(data)
            return True
    return False

def mark_deleted(table_id):
    return update(table_id, status='deleted')

def list_all():
    data = _load()
    return data['tables']

def summary():
    data = _load()
    tables = data['tables']
    active = [t for t in tables if t.get('status') == 'active']
    return {
        'total': len(tables),
        'active': len(active),
        'deprecated': sum(1 for t in tables if t.get('status') == 'deprecated'),
        'tables': tables,
    }

if __name__ == '__main__':
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'list'

    if mode == 'list':
        s = summary()
        print(f'台账: 共 {s["total"]} 个表格 (活跃 {s["active"]}, 废弃 {s["deprecated"]})\n')
        for t in s['tables']:
            status_icon = '[A]' if t.get('status') == 'active' else '[D]'
            tags = ', '.join(t.get('tags', []))
            print(f'  {status_icon} [{t["id"]}] {t["name"]}')
            docid_show = t['docid'][:20] + '...' if t.get('docid') else '(无)'
            print(f'     docid: {docid_show}')
            print(f'     字段数: {len(t.get("fields", []))} | 记录: {t.get("record_count", 0)} | 标签: {tags}')
            print(f'     用途: {t.get("purpose", "")}')
            print()
    elif mode == 'active':
        for t in get_active():
            print(f'  [{t["id"]}] {t["name"]} | docid={t["docid"][:20]}... | sheet={t.get("sheet_id","")}')
            print(f'     url: {t.get("url","")}')
    else:
        print(f'用法: python smartsheet_ledger.py [list|active]')
