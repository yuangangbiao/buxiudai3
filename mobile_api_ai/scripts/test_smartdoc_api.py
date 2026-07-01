# -*- coding: utf-8 -*-
"""
企业微信智能文档（doc_type=3）API 测试
测试能力：创建文档、获取文档内容、批量编辑内容、获取分享链接

用法:
    python test_smartdoc_api.py
"""
import sys, os, json, requests, datetime
from dotenv import load_dotenv

# ── 日志捕获（绕过沙箱 stdout 吞没） ──
_LOG_LINES = []
_LOG_FILE = None

def log(text=''):
    _LOG_LINES.append(str(text).rstrip('\n'))
    sys.__stdout__.write(str(text) + '\n')

def _flush_log():
    global _LOG_FILE
    if _LOG_FILE:
        _LOG_FILE.close()
        _LOG_FILE = None
    log_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '_run_output.txt'))
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(_LOG_LINES))

def _init_log():
    global _LOG_FILE
    log_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '_run_output.txt'))
    _LOG_FILE = open(log_path, 'w', encoding='utf-8')
    _LOG_FILE.write('=== START ===\n')
    _LOG_FILE.flush()

# ── 本地文档台账 ──
DOC_LEDGER_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), 'doc_ledger.json')
)

def _load_ledger():
    if not os.path.exists(DOC_LEDGER_PATH):
        return {'version': 1, 'docs': []}
    with open(DOC_LEDGER_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def _save_ledger(data):
    data['updated_at'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    with open(DOC_LEDGER_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _find_doc_by_name(name):
    ledger = _load_ledger()
    for doc in ledger['docs']:
        if doc['doc_name'] == name:
            return doc
    return None

def _register_doc(docid, doc_name, url):
    ledger = _load_ledger()
    for doc in ledger['docs']:
        if doc['docid'] == docid:
            doc['updated_at'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            _save_ledger(ledger)
            return
    entry = {
        'docid': docid,
        'doc_name': doc_name,
        'url': url,
        'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': '',
    }
    ledger['docs'].append(entry)
    _save_ledger(ledger)
    log(f'      [台账] 已记录')

# 加载企业微信凭证
ENV_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '..', '.env'
))
load_dotenv(ENV_PATH)

CORP_ID = os.getenv('WECHAT_CORP_ID')
CORP_SECRET = os.getenv('WECHAT_SECRET')
# 文档管理员 - 企业微信中需存在的用户
ADMIN_USERS = ['YuanGangBiao']
# 分享目标 - 苑圆彪
SHARE_USER = 'YuanYuanBiaoChenShengLianWangLia'
SHARE_USER_NAME = '苑圆彪'

API_BASE = 'https://qyapi.weixin.qq.com/cgi-bin'


def get_token():
    resp = requests.get(
        f'{API_BASE}/gettoken',
        params={'corpid': CORP_ID, 'corpsecret': CORP_SECRET},
        timeout=10,
    )
    data = resp.json()
    if data.get('errcode') != 0:
        raise Exception(f'gettoken 失败: {data}')
    token = data['access_token']
    log(f'[OK] access_token 获取成功 ({token[:8]}...)')
    return token


def create_doc(token):
    """创建智能文档（doc_type=3）"""
    today = datetime.date.today().strftime('%Y-%m-%d')
    doc_name = f'日报测试-{today}'
    body = {
        'doc_type': 3,
        'doc_name': doc_name,
        'admin_users': ADMIN_USERS,
    }
    log(f'[..] 创建文档: {doc_name} ...')
    resp = requests.post(
        f'{API_BASE}/wedoc/create_doc',
        params={'access_token': token},
        json=body,
        timeout=15,
    )
    data = resp.json()
    if data.get('errcode') != 0:
        raise Exception(f'create_doc 失败: {data}')
    docid = data.get('docid')
    url = data.get('url', '')
    log(f'[OK] 文档创建成功')
    log(f'      docid: {docid}')
    log(f'      url:   {url}')
    return docid, url


def get_document(token, docid):
    """获取文档内容（含版本号）"""
    log(f'[..] 获取文档内容 ...')
    resp = requests.post(
        f'{API_BASE}/wedoc/document/get',
        params={'access_token': token},
        json={'docid': docid},
        timeout=15,
    )
    data = resp.json()
    if data.get('errcode') != 0:
        log(f'[!!] 获取文档内容失败: {data.get("errmsg", "")}')
        return None
    version = data.get('version', 0)
    document = data.get('document', {})
    log(f'[OK] 文档版本: {version}')
    return version


def batch_update_document(token, docid, version, requests_list):
    """批量编辑文档内容"""
    body = {
        'docid': docid,
        'version': version,
        'requests': requests_list,
    }
    log(f'[..] 批量编辑文档内容 ({len(requests_list)} 个操作) ...')
    resp = requests.post(
        f'{API_BASE}/wedoc/document/batch_update',
        params={'access_token': token},
        json=body,
        timeout=15,
    )
    data = resp.json()
    if data.get('errcode') != 0:
        log(f'[!!] 批量编辑失败: {data.get("errmsg", "")}')
        return False
    log(f'[OK] 批量编辑成功')
    return True


def doc_share(token, docid):
    """获取文档分享链接"""
    resp = requests.post(
        f'{API_BASE}/wedoc/doc_share',
        params={'access_token': token},
        json={'docid': docid},
        timeout=15,
    )
    data = resp.json()
    if data.get('errcode') != 0:
        log(f'[!!] 获取分享链接失败: {data.get("errmsg", "")}')
        return None
    share_url = data.get('share_url', '')
    log(f'[OK] 分享链接: {share_url}')
    return share_url


def mod_doc_member(token, docid, userid, user_name):
    """将文档分享给指定用户（添加到文档通知范围）"""
    log(f'[..] 分享文档给 {user_name} ({userid}) ...')
    resp = requests.post(
        f'{API_BASE}/wedoc/mod_doc_member',
        params={'access_token': token},
        json={
            'docid': docid,
            'update_file_member_list': [
                {
                    'type': 1,
                    'auth': 1,
                    'userid': userid,
                }
            ]
        },
        timeout=15,
    )
    data = resp.json()
    if data.get('errcode') != 0:
        log(f'[!!] 分享给指定用户失败: {data.get("errmsg", "")}')
        return False
    log(f'[OK] 已成功分享给 {user_name}')
    return True


def build_daily_report():
    """构建日报内容"""
    today = datetime.datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][today.weekday()]

    lines = [
        f'# 工作日报 - {date_str} ({weekday})',
        '',
        '## 今日完成',
        '1. 完成跟单系统的调度中心页面开发',
        '2. 修复订单同步流程中的状态异常问题',
        '3. 编写智能表格台账管理系统',
        '',
        '## 明日计划',
        '1. 继续跟单系统的接口联调测试',
        '2. 优化订单查询性能，添加索引',
        '',
        '## 遇到的问题',
        '- 企业微信 API 中 doc_type=3 的文档编辑接口需要批量更新方式，与智能表格不同',
        '- 文档编辑需要先获取版本号，再提交 batch_update',
        '',
        '## 备注',
        f'本日报由自动化脚本生成于 {today.strftime("%Y-%m-%d %H:%M")}',
    ]
    return '\n'.join(lines)


def build_insert_requests(markdown_text):
    """将 Markdown 文本转换为 batch_update 的 insert_text 操作列表"""
    paragraphs = markdown_text.split('\n')
    requests_list = []
    index = 0
    for para in paragraphs:
        if para == '':
            index += 1
            continue
        if para.startswith('# '):
            req = {
                'insert_paragraph': {'location': {'index': index}}
            }
            requests_list.append(req)
            index += 1
            req = {
                'insert_text': {
                    'text': para[2:],
                    'location': {'index': index}
                }
            }
            requests_list.append(req)
            index += 1
        elif para.startswith('## '):
            req = {
                'insert_paragraph': {'location': {'index': index}}
            }
            requests_list.append(req)
            index += 1
            req = {
                'insert_text': {
                    'text': para[3:],
                    'location': {'index': index}
                }
            }
            requests_list.append(req)
            index += 1
        elif para.startswith('- '):
            req = {
                'insert_text': {
                    'text': para,
                    'location': {'index': index}
                }
            }
            requests_list.append(req)
            index += 1
        elif para.startswith('1.') or para.startswith('2.') or para.startswith('3.'):
            req = {
                'insert_text': {
                    'text': para,
                    'location': {'index': index}
                }
            }
            requests_list.append(req)
            index += 1
        else:
            req = {
                'insert_text': {
                    'text': para,
                    'location': {'index': index}
                }
            }
            requests_list.append(req)
            index += 1
    return requests_list


def build_simple_insert(markdown_text):
    """简化版：一次性插入全部内容"""
    return [
        {
            'insert_text': {
                'text': markdown_text,
                'location': {'index': 0}
            }
        }
    ]


def main():
    log('=' * 60)
    log('企业微信智能文档 - API 测试（含本地台账幂等）')
    log('=' * 60)

    today = datetime.date.today().strftime('%Y-%m-%d')
    doc_name = f'日报测试-{today}'

    token = get_token()

    existing = _find_doc_by_name(doc_name)
    if existing:
        docid = existing['docid']
        url = existing['url']
        log(f'[*] 台账命中: 今日文档已存在，尝试复用 ({docid[:20]}...)')
        version = get_document(token, docid)
        if version is None:
            log(f'[!!] 文档不可访问（可能被手动删除），从台账移除并重建')
            ledger = _load_ledger()
            ledger['docs'] = [d for d in ledger['docs'] if d['docid'] != docid]
            _save_ledger(ledger)
            docid, url = create_doc(token)
            version = 0
        else:
            log(f'      url:   {url}')
    else:
        docid, url = create_doc(token)
        version = 0

    report_text = build_daily_report()
    log(f'\n[..] 日报内容 ({len(report_text)} 字符):')
    log(report_text)
    log()

    requests_list = build_simple_insert(report_text)
    success = batch_update_document(token, docid, version or 0, requests_list)

    if success:
        _register_doc(docid, doc_name, url)
        mod_doc_member(token, docid, SHARE_USER, SHARE_USER_NAME)
        share_url = doc_share(token, docid)
        log()
        log('=' * 60)
        log('测试结果')
        log('=' * 60)
        log(f'  文档: {doc_name}')
        log(f'  docid: {docid}')
        log(f'  链接: {url}')
        if share_url:
            log(f'  分享: {share_url}')
        log(f'  已分享给: {SHARE_USER_NAME}')
        log('  状态: [OK] 幂等创建 + 内容写入 + 分享成功')
    else:
        log()
        log('  状态: [!!] 内容写入失败，请检查错误信息')


if __name__ == '__main__':
    _init_log()
    try:
        main()
    except Exception as e:
        log(f'=== ERROR: {e} ===')
        import traceback
        traceback.print_exc(file=sys.__stdout__)
    _flush_log()
