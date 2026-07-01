# -*- coding: utf-8 -*-
"""
企业微信智能表格 正式 API 测试
支持: 查询表格信息、获取字段、读取记录、更新记录、新增记录

用法:
    python test_smartsheet_api.py              # 完整测试流程
    python test_smartsheet_api.py --read-only  # 只读不写
"""
import sys, os, json, requests, argparse
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

# 加载企业微信凭证
ENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')
ENV_PATH = os.path.normpath(ENV_PATH)
load_dotenv(ENV_PATH)

CORP_ID = os.getenv('WECHAT_CORP_ID')
CORP_SECRET = os.getenv('WECHAT_SECRET')
DOC_ID = 's3_AKwAWxSZABQCNlYR0OoQTQHqiQ2oD_a'

API_BASE = 'https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet'


def api_url(path, token):
    return f'{API_BASE}/{path}?access_token={token}'


def get_token():
    """获取 access_token"""
    resp = requests.get(
        'https://qyapi.weixin.qq.com/cgi-bin/gettoken',
        params={'corpid': CORP_ID, 'corpsecret': CORP_SECRET},
        timeout=10,
    )
    data = resp.json()
    if data.get('errcode') != 0:
        raise Exception(f'gettoken 失败: {data}')
    token = data['access_token']
    print(f'[OK] access_token 获取成功 ({token[:8]}...)')
    return token


def list_sheets(token):
    """获取表格的所有 sheet，返回 sheet_id 列表"""
    resp = requests.post(
        api_url('list_sheets', token),
        json={'docid': DOC_ID},
        timeout=15,
    )
    data = resp.json()
    if data.get('errcode') != 0:
        raise Exception(f'list_sheets 失败: {data}')
    sheets = data.get('sheets', data.get('items', []))
    print(f'[OK] 共 {len(sheets)} 个工作表:')
    for s in sheets:
        sid = s.get('sheet_id', '')
        title = s.get('title', '(未命名)')
        print(f'      - [{sid}] {title}')
    return sheets


def list_fields(token, sheet_id):
    """获取字段列表"""
    resp = requests.post(
        api_url('list_fields', token),
        json={'docid': DOC_ID, 'sheet_id': sheet_id, 'limit': 50},
        timeout=15,
    )
    data = resp.json()
    if data.get('errcode') != 0:
        # 可能没有 list_fields，改用 get_fields
        resp2 = requests.post(
            api_url('get_fields', token),
            json={'docid': DOC_ID, 'sheet_id': sheet_id, 'limit': 50},
            timeout=15,
        )
        data = resp2.json()
    if data.get('errcode') != 0:
        print(f'[!!] 获取字段失败: {data.get("errmsg", "")}')
        return []
    fields = data.get('fields', data.get('items', []))
    print(f'[OK] 共 {len(fields)} 个字段:')
    for f in fields:
        fid = f.get('field_id', '')
        title = f.get('field_title', f.get('title', ''))
        ftype = f.get('field_type', f.get('type', ''))
        print(f'      [{fid}] {title} ({ftype})')
    return fields


def get_records(token, sheet_id, limit=20):
    """读取已有记录"""
    resp = requests.post(
        api_url('get_records', token),
        json={
            'docid': DOC_ID,
            'sheet_id': sheet_id,
            'key_type': 'CELL_VALUE_KEY_TYPE_FIELD_TITLE',
            'limit': limit,
            'offset': 0,
        },
        timeout=15,
    )
    data = resp.json()
    if data.get('errcode') != 0:
        print(f'[!!] 读取记录失败: {data.get("errmsg", "")}')
        return []
    records = data.get('records', [])
    total = data.get('total', len(records))
    print(f'[OK] 共 {total} 条记录 (显示前 {len(records)} 条):')
    for r in records:
        rid = r.get('record_id', '')
        vals = r.get('values', {})
        preview = {}
        for k in list(vals.keys())[:4]:
            v = vals[k]
            if isinstance(v, list) and len(v) > 0:
                preview[k] = v[0].get('text', '') if isinstance(v[0], dict) else str(v[0])
            else:
                preview[k] = str(v)
        print(f'      [{rid}] {json.dumps(preview, ensure_ascii=False)}')
    return records


def update_record(token, sheet_id, record_id, field_updates):
    """更新记录中指定字段"""
    url = api_url('update_records', token)
    values = {}
    for title, text_val in field_updates.items():
        values[title] = [{'type': 'text', 'text': text_val}]

    body = {
        'docid': DOC_ID,
        'sheet_id': sheet_id,
        'key_type': 'CELL_VALUE_KEY_TYPE_FIELD_TITLE',
        'records': [
            {
                'record_id': record_id,
                'values': values,
            }
        ],
    }
    print(f'      请求: {json.dumps(body, ensure_ascii=False, indent=4)}')
    resp = requests.post(url, json=body, timeout=15)
    data = resp.json()
    if data.get('errcode') == 0:
        print(f'      [OK] 更新成功')
    else:
        print(f'      [!!] 更新失败: errcode={data.get("errcode")}, {data.get("errmsg", "")}')
    return data


def add_record(token, sheet_id, field_values):
    """新增一条记录（使用字段标题）"""
    url = api_url('add_records', token)
    fields = {}
    for title, text_val in field_values.items():
        fields[title] = [{'type': 'text', 'text': text_val}]

    body = {
        'docid': DOC_ID,
        'sheet_id': sheet_id,
        'key_type': 'CELL_VALUE_KEY_TYPE_FIELD_TITLE',
        'records': [{'fields': fields}],
    }
    print(f'      请求: {json.dumps(body, ensure_ascii=False, indent=4)}')
    resp = requests.post(url, json=body, timeout=15)
    data = resp.json()
    if data.get('errcode') == 0:
        new_records = data.get('records', [])
        if new_records:
            rid = new_records[0].get('record_id', '')
            print(f'      [OK] 新增成功, record_id: {rid}')
        else:
            print(f'      [OK] 新增成功')
    else:
        print(f'      [!!] 新增失败: errcode={data.get("errcode")}, {data.get("errmsg", "")}')
    return data


def main():
    parser = argparse.ArgumentParser(description='智能表格正式 API 测试')
    parser.add_argument('--read-only', action='store_true', help='只读模式（不执行写入操作）')
    args = parser.parse_args()

    print('=' * 60)
    print('企业微信智能表格 - 正式 API 测试')
    print(f'DocID: {DOC_ID}')
    print(f'只读模式: {"是" if args.read_only else "否"}')
    print('=' * 60)

    # 1. 获取 token
    token = get_token()

    # 2. 查询 sheet 信息
    sheets = list_sheets(token)
    if not sheets:
        print('[!!] 未找到任何工作表，退出')
        return
    sheet_id = sheets[0]['sheet_id']
    print(f'\n使用第一个工作表: [{sheet_id}]')

    # 3. 查看字段
    print()
    fields = list_fields(token, sheet_id)
    if not fields:
        print('[!!] 无法获取字段信息，后续操作可能失败')

    # 4. 读取已有记录
    print()
    records = get_records(token, sheet_id, limit=10)

    # 5. 测试更新（如果有记录且不是只读模式）
    if records and not args.read_only:
        target = records[0]
        rid = target['record_id']
        vals = target.get('values', {})
        field_titles = list(vals.keys())

        print(f'\n--- 测试: 更新记录 [{rid}] ---')
        updates = {}
        if len(field_titles) >= 1:
            updates[field_titles[0]] = '[已更新] 正式API测试'
        if len(field_titles) >= 2:
            updates[field_titles[1]] = 'API更新测试'
        if updates:
            update_record(token, sheet_id, rid, updates)

        # 再次读取验证更新结果
        print(f'\n--- 验证: 重新读取记录 ---')
        get_records(token, sheet_id, limit=3)
    elif args.read_only:
        print('\n[跳过] 只读模式，不执行写入操作')
    else:
        print('\n[跳过] 没有记录可更新')

    # 6. 测试新增（非只读模式）
    if not args.read_only:
        print(f'\n--- 测试: 新增记录 ---')
        # 根据实际字段动态构建
        if len(fields) >= 2:
            sample = {'分类': 'API测试', '订单号': 'TEST-API-001'}
            add_record(token, sheet_id, sample)
        else:
            print('[跳过] 字段信息不足，无法构造新增数据')

        print(f'\n--- 验证: 新增后重新读取记录 ---')
        get_records(token, sheet_id, limit=5)

    print('\n' + '=' * 60)
    print('测试完成')
    print('=' * 60)


if __name__ == '__main__':
    main()
