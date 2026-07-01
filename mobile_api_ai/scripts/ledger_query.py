# -*- coding: utf-8 -*-
"""
智能表格台账查询工具
用于查找已创建的表格信息，获取 docid/sheet_id/url 以便进行数据操作

用法:
    python ledger_query.py                            # 列出所有表格
    python ledger_query.py --active                   # 只列出活跃表格
    python ledger_query.py --name 工单                 # 按名称模糊搜索
    python ledger_query.py --tag 主用                  # 按标签搜索
    python ledger_query.py --detail table_xxx         # 查看表格详细配置
    python ledger_query.py --docid dc...               # 按 docid 查找
    python ledger_query.py --export                   # 导出所有表格到 CSV
    python ledger_query.py --export --active          # 导出活跃表格到 CSV
"""
import sys, json, os, csv

LEDGER_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, LEDGER_DIR)

import smartsheet_ledger as ledger

SEP = '-' * 60

def show_table(t, verbose=False):
    status_tag = '[A]' if t.get('status') == 'active' else '[D]' if t.get('status') == 'deprecated' else '[X]'
    print(f'{status_tag} {t["id"]}')
    print(f'   名称:     {t["name"]}')
    print(f'   状态:     {t.get("status", "?")}')
    print(f'   用途:     {t.get("purpose", "")}')
    print(f'   标签:     {", ".join(t.get("tags", []))}')

    if verbose:
        print(f'   docid:    {t.get("docid", "(无)")}')
        print(f'   s3_id:    {t.get("s3_id", "(无)")}')
        print(f'   sheet_id:  {t.get("sheet_id", "(无)")}')
        print(f'   sheet_name: {t.get("sheet_name", "(无)")}')
        print(f'   字段({len(t.get("fields", []))}): {", ".join(t.get("fields", []))}')
        print(f'   记录数:   {t.get("record_count", 0)}')
        print(f'   创建于:   {t.get("created_at", "?")}')
        print(f'   创建方式: {t.get("created_via", "?")}')
        print(f'   URL:')
        print(f'     {t.get("url", "")}')
    else:
        print(f'   docid:    {t.get("docid", "(无)")[:20]}...' if t.get('docid') else '   docid:    (无)')
        print(f'   字段数:   {len(t.get("fields", []))} | 记录: {t.get("record_count", 0)}')
        print(f'   详情:     ledger_query.py --detail {t["id"]}')

    print(SEP)

def cmd_list(args):
    tables = ledger.list_all()
    if not tables:
        print('台账为空')
        return
    s = ledger.summary()
    print(f'台账: 共 {s["total"]} 个表格 (活跃 {s["active"]}, 废弃 {s["deprecated"]})\n')
    print(SEP)
    for t in tables:
        show_table(t, verbose=False)

def cmd_active(args):
    tables = ledger.get_active()
    if not tables:
        print('没有活跃表格')
        return
    print(f'活跃表格: {len(tables)} 个\n')
    print(SEP)
    for t in tables:
        show_table(t, verbose=True)

def cmd_detail(args):
    table_id = args[0] if args else ''
    if not table_id:
        print('请指定 table_id: ledger_query.py --detail <table_id>')
        return
    tables = ledger.list_all()
    target = None
    for t in tables:
        if t['id'] == table_id:
            target = t
            break
    if not target:
        print(f'未找到表格: {table_id}')
        return
    print(f'表格详细配置: {table_id}\n')
    print(json.dumps(target, ensure_ascii=False, indent=2))

def cmd_name(args):
    keyword = args[0] if args else ''
    if not keyword:
        print('请指定关键词: ledger_query.py --name <关键词>')
        return
    tables = ledger.query(name=keyword)
    if not tables:
        print(f'未找到名称包含 "{keyword}" 的表格')
        return
    print(f'搜索名称 "{keyword}": {len(tables)} 个结果\n')
    print(SEP)
    for t in tables:
        show_table(t, verbose=True)

def cmd_tag(args):
    tag = args[0] if args else ''
    if not tag:
        print('请指定标签: ledger_query.py --tag <标签>')
        return
    tables = ledger.query(tag=tag)
    if not tables:
        print(f'未找到标签为 "{tag}" 的表格')
        return
    print(f'搜索标签 "{tag}": {len(tables)} 个结果\n')
    print(SEP)
    for t in tables:
        show_table(t, verbose=True)

def cmd_docid(args):
    docid = args[0] if args else ''
    if not docid:
        print('请指定 docid: ledger_query.py --docid <docid>')
        return
    t = ledger.get_by_docid(docid)
    if not t:
        print(f'未找到 docid="{docid}" 的表格')
        return
    print(f'找到匹配表格:\n')
    show_table(t, verbose=True)

def cmd_export(args):
    extra_args = [a for a in args if not a.startswith('--')]
    filters = [a for a in args if a.startswith('--')]

    tables = ledger.list_all()
    if '--active' in filters:
        tables = [t for t in tables if t.get('status') == 'active']

    output_path = os.path.join(LEDGER_DIR, 'smartsheet_ledger.csv')
    if extra_args:
        output_path = extra_args[0]

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', '名称', '状态', 'docid', 's3_id', 'sheet_id', 'sheet_name',
                         '字段列表', '字段数', '记录数', '创建日期', '创建方式', '标签', '用途', 'URL'])
        for t in tables:
            writer.writerow([
                t.get('id', ''),
                t.get('name', ''),
                t.get('status', ''),
                t.get('docid', ''),
                t.get('s3_id', ''),
                t.get('sheet_id', ''),
                t.get('sheet_name', ''),
                ', '.join(t.get('fields', [])),
                len(t.get('fields', [])),
                t.get('record_count', 0),
                t.get('created_at', ''),
                t.get('created_via', ''),
                ', '.join(t.get('tags', [])),
                t.get('purpose', ''),
                t.get('url', ''),
            ])

    print(f'导出完成: {output_path}')
    print(f'  共 {len(tables)} 个表格, 可直接用 Excel 打开')

if __name__ == '__main__':
    args = sys.argv[1:]

    if not args:
        cmd_list(args)
    elif args[0] == '--active':
        cmd_active(args[1:])
    elif args[0] == '--detail':
        cmd_detail(args[1:])
    elif args[0] == '--name':
        cmd_name(args[1:])
    elif args[0] == '--tag':
        cmd_tag(args[1:])
    elif args[0] == '--docid':
        cmd_docid(args[1:])
    elif args[0] == '--export':
        cmd_export(args[1:])
    elif args[0] in ('-h', '--help'):
        print(__doc__)
    else:
        print(f'未知参数: {args[0]}')
        print(f'用法: python ledger_query.py [--active|--detail <id>|--name <关键词>|--tag <标签>|--docid <docid>|--export [保存路径]]')
