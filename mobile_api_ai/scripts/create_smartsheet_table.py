# -*- coding: utf-8 -*-
"""
企业微信智能表格 - 创建新表 → 添加子表 → 批量添加15个字段 → 写入工单数据 → 验证

正确 API 调用链:
  1. POST /cgi-bin/wedoc/create_doc?doc_type=10        ✅ 创建智能表格
  2. POST /cgi-bin/wedoc/smartsheet/add_sheet           ✅ 添加子表
  3. POST /cgi-bin/wedoc/smartsheet/add_fields fields[]  ✅ 批量添加字段
  4. POST /cgi-bin/wedoc/smartsheet/get_fields           ✅ 获取字段 ID
  5. POST /cgi-bin/wedoc/smartsheet/add_records FIELD_ID ✅ 写入数据
  6. POST /cgi-bin/wedoc/smartsheet/get_records          ✅ 验证数据
"""
import sys, os, json, requests, time, re
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
RESULT_FILE = 'd:/yuan/table_result.json'

# 台账模块
LEDGER_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, LEDGER_DIR)
import smartsheet_ledger as ledger

ENV_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '.env')
)
load_dotenv(ENV_PATH)

CORP_ID = os.getenv('WECHAT_CORP_ID')
CORP_SECRET = os.getenv('WECHAT_SECRET')
ADMIN_USER = 'YuanGangBiao'
TABLE_NAME = '跟单系统工单总表'
SHEET_NAME = '工单数据'

FIELD_NAMES = [
    '分类', '订单号', '客户名称', '产品类型', '材质',
    '状态', '创建日期', '订单数量', '单位', '订单号',
    '当前工序', '数据来源', '工序总数', '完成进度', '备注',
]

BASE_API = 'https://qyapi.weixin.qq.com/cgi-bin'
API = {
    'token':    f'{BASE_API}/gettoken',
    'create':   f'{BASE_API}/wedoc/create_doc',
    'add_sheet':f'{BASE_API}/wedoc/smartsheet/add_sheet',
    'add_fields':f'{BASE_API}/wedoc/smartsheet/add_fields',
    'get_fields':f'{BASE_API}/wedoc/smartsheet/get_fields',
    'add_records':f'{BASE_API}/wedoc/smartsheet/add_records',
    'get_records':f'{BASE_API}/wedoc/smartsheet/get_records',
}

result = {'steps': [], 'status': 'started'}

def save():
    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

def step(name, status='ok', details=None):
    s = {'name': name, 'status': status}
    if details:
        s['details'] = details
    result['steps'].append(s)
    result['status'] = status
    save()
    detail_str = json.dumps(details or {}, ensure_ascii=False)
    print(f'  [{status}] {name}: {detail_str[:200]}')

def get_token():
    resp = requests.get(API['token'], params={'corpid': CORP_ID, 'corpsecret': CORP_SECRET}, timeout=10)
    data = resp.json()
    if data.get('errcode') != 0:
        step('get_token', 'fail', data)
        raise Exception(f'gettoken failed: {data}')
    token = data['access_token']
    step('get_token', 'ok', {'prefix': token[:8]})
    return token

def create_doc(token):
    resp = requests.post(f"{API['create']}?access_token={token}",
        json={'doc_type': 10, 'doc_name': TABLE_NAME, 'admin_users': [ADMIN_USER]}, timeout=15)
    data = resp.json()
    if data.get('errcode') != 0:
        step('create_doc', 'fail', data)
        raise Exception(f'create_doc failed: {data}')
    doc_id = data.get('docid', '')
    url = data.get('url', '')
    step('create_doc', 'ok', {'docid': doc_id[:30]+'...', 'url': url})
    return doc_id, url

def add_sheet(token, doc_id):
    resp = requests.post(f"{API['add_sheet']}?access_token={token}",
        json={'docid': doc_id, 'sheet_name': SHEET_NAME}, timeout=15)
    data = resp.json()
    if data.get('errcode') != 0:
        step('add_sheet', 'fail', data)
        raise Exception(f'add_sheet failed: {data}')
    sheet_id = data.get('properties', {}).get('sheet_id', '')
    step('add_sheet', 'ok', {'sheet_id': sheet_id})
    return sheet_id

def add_fields_batch(token, doc_id, sheet_id):
    """批量添加字段：必须传 fields 数组（非 field 单个）"""
    # 查已有字段
    resp = requests.post(f"{API['get_fields']}?access_token={token}",
        json={'docid': doc_id, 'sheet_id': sheet_id, 'limit': 50}, timeout=15)
    existing = set()
    if resp.status_code == 200:
        fd = resp.json()
        if fd.get('errcode') == 0:
            existing = {f['field_title'] for f in fd.get('fields', [])}

    to_add = [n for n in FIELD_NAMES if n not in existing]
    if not to_add:
        step('add_fields', 'ok', {'msg': 'all fields already exist', 'count': len(FIELD_NAMES)})
        return

    # 批量添加
    fields_payload = [{'field_title': name, 'field_type': 'FIELD_TYPE_TEXT'} for name in to_add]
    resp = requests.post(f"{API['add_fields']}?access_token={token}",
        json={'docid': doc_id, 'sheet_id': sheet_id, 'fields': fields_payload}, timeout=30)
    data = resp.json()
    if data.get('errcode') != 0:
        step('add_fields', 'fail', data)
        raise Exception(f'add_fields failed: {data}')
    added = data.get('fields', [])
    step('add_fields', 'ok', {'added_count': len(added), 'names': [f.get('field_title','') for f in added]})

def get_field_map(token, doc_id, sheet_id):
    """获取 field_title → field_id 映射"""
    time.sleep(1)
    resp = requests.post(f"{API['get_fields']}?access_token={token}",
        json={'docid': doc_id, 'sheet_id': sheet_id, 'limit': 50}, timeout=15)
    data = resp.json()
    if data.get('errcode') != 0:
        step('get_field_map', 'fail', data)
        return {}
    fmap = {f['field_title']: f['field_id'] for f in data.get('fields', [])}
    step('get_field_map', 'ok', {'count': len(fmap)})
    return fmap

def add_record(token, doc_id, sheet_id, field_map):
    """写入数据：必须用 FIELD_ID，值格式 [{"type":"text","text":"值"}]"""
    record_data = {
        '分类': '生产工单', '订单号': 'WO-202605006', '客户名称': '山东济南食品',
        '产品类型': '平板型网带', '材质': '304不锈钢', '状态': '已创建',
        '创建日期': '2026-05-17', '订单数量': '50', '单位': '件',
        '订单号': 'ORD-202604290001', '当前工序': '原材料准备', '数据来源': '跟单系统',
        '工序总数': '11', '完成进度': '9% (1/11)', '备注': '正式API写入测试',
    }
    # 转为 FIELD_ID → 值格式
    values = {}
    for title, val in record_data.items():
        fid = field_map.get(title)
        if fid:
            values[fid] = [{'type': 'text', 'text': val}]

    resp = requests.post(f"{API['add_records']}?access_token={token}",
        json={'docid': doc_id, 'sheet_id': sheet_id,
              'key_type': 'CELL_VALUE_KEY_TYPE_FIELD_ID',
              'records': [{'values': values}]}, timeout=15)
    data = resp.json()
    if data.get('errcode') == 0:
        rec = data.get('records', [{}])[0]
        rid = rec.get('record_id', '')
        vals = rec.get('values', {})
        filled = sum(1 for v in vals.values() if v)
        step('add_record', 'ok', {'record_id': rid, 'fields_filled': filled})
        return rid
    else:
        step('add_record', 'fail', data)
        return None

def verify_records(token, doc_id, sheet_id):
    time.sleep(1)
    resp = requests.post(f"{API['get_records']}?access_token={token}",
        json={'docid': doc_id, 'sheet_id': sheet_id,
              'key_type': 'CELL_VALUE_KEY_TYPE_FIELD_ID',
              'limit': 5, 'offset': 0}, timeout=15)
    data = resp.json()
    if data.get('errcode') == 0:
        records = data.get('records', [])
        previews = []
        for rec in records[:3]:
            vals = rec.get('values', {})
            p = {}
            for k in list(vals.keys())[:5]:
                v = vals[k]
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    p[k] = v[0].get('text', '')
                else:
                    p[k] = str(v)[:30]
            previews.append({'record_id': rec['record_id'], 'preview': p})
        step('verify_records', 'ok', {'total': data.get('total'), 'samples': previews})
    else:
        step('verify_records', 'fail', data)

def main():
    print('===== 企业微信智能表格 - 创建+写入 正式API =====\n')
    result['table_name'] = TABLE_NAME
    result['admin_user'] = ADMIN_USER
    save()
    try:
        token = get_token()
        doc_id, doc_url = create_doc(token)
        sheet_id = add_sheet(token, doc_id)
        add_fields_batch(token, doc_id, sheet_id)
        fmap = get_field_map(token, doc_id, sheet_id)
        rid = add_record(token, doc_id, sheet_id, fmap)
        verify_records(token, doc_id, sheet_id)
        result['status'] = 'completed'
        result['summary'] = {
            'docid': doc_id,
            'sheet_id': sheet_id,
            'url': doc_url,
            'record_id': rid or '-',
            'fields_count': len(FIELD_NAMES),
        }
        save()
        s3_match = re.search(r'/smartsheet/(s3_[^\s?]+)', doc_url)
        s3_id = s3_match.group(1) if s3_match else ''
        ledger_id = ledger.register(
            docid=doc_id, s3_id=s3_id, url=doc_url,
            name=TABLE_NAME, sheet_id=sheet_id, sheet_name=SHEET_NAME,
            fields=FIELD_NAMES, record_count=1 if rid else 0,
            purpose='create_smartsheet_table.py 创建的正式工单总表',
            created_via='formal_api',
            tags=['正式', '正式API', '可操作', '主用'],
        )
        print('\n===== DONE =====')
        print(f'  docid:    {doc_id}')
        print(f'  sheet_id: {sheet_id}')
        print(f'  url:      {doc_url}')
        if rid:
            print(f'  record:   {rid}')
        print(f'  ledger:   {ledger_id}')
        print(f'  result:   {RESULT_FILE}')
    except Exception as e:
        result['status'] = 'failed'
        result['error'] = str(e)
        save()
        print(f'\nFAILED: {e}', file=sys.stderr)

if __name__ == '__main__':
    main()
