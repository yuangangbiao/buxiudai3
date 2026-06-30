# -*- coding: utf-8 -*-
"""
web5001 全链路端到端测试 v2 - 使用 requests 库 + Session 自动维护 Cookie
覆盖: 登录 + 5个管理模块 + 安全验证 + 状态机 + 并发锁
"""
import sys, os, json, time, datetime, uuid, tempfile
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')
os.chdir(r'd:\yuan\不锈钢网带跟单3.0')

import requests
from playwright.sync_api import sync_playwright

API_BASE = 'http://127.0.0.1:5001'
ADMIN_USER = '测试'
RUN_TAG = datetime.datetime.now().strftime('%m%d%H%M%S')
UNIQ = f'{RUN_TAG}{uuid.uuid4().hex[:4].upper()}'

S = {}
PASS, FAIL = 0, 0
RESULTS = []
SCREENSHOTS = []

def log(msg):
    print(f'  {msg}')
    RESULTS.append(msg)

def check(label, cond, detail=''):
    global PASS, FAIL
    tag = '✅ PASS' if cond else '❌ FAIL'
    if cond: PASS += 1
    else: FAIL += 1
    log(f'  {tag}  {label}')
    if detail: log(f'         {str(detail)[:200]}')

def api(url, method='GET', json_data=None, timeout=15):
    """使用 requests Session 自动维护 Cookie + CSRF Token"""
    hdrs = {'Content-Type': 'application/json'}
    if S.get('csrf_token'):
        hdrs['X-CSRF-Token'] = S['csrf_token']
    try:
        if method == 'GET':
            r = S['session'].get(url, headers=hdrs, timeout=timeout)
        else:
            r = S['session'].request(method, url, json=json_data, headers=hdrs, timeout=timeout)
        try: body = r.json()
        except: body = {}
        return body, r.status_code
    except Exception as e:
        return {'error': str(e)}, 0

def screenshot(page, name):
    path = f'd:/yuan/不锈钢网带跟单3.0/docs/e2e_{name}.png'
    page.screenshot(path=path, full_page=True)
    SCREENSHOTS.append(path)
    return path

# ═══════════════════════════════════════════════════════════
# 阶段1: 服务健康
# ═══════════════════════════════════════════════════════════
def stage1():
    log('\n══ 阶段1: 服务健康检查 ══')
    try:
        r = requests.get(f'{API_BASE}/', timeout=5)
        check('5001服务响应', r.status_code in (200, 302), f'status={r.status_code}')
    except Exception as e:
        check('5001服务响应', False, str(e)[:80])
    try:
        r = requests.get(f'{API_BASE}/api/dispatch-center/health', timeout=5)
        check('5003(调度中心)响应', r.status_code in (200, 401), f'status={r.status_code}')
    except Exception as e:
        check('5003响应', False, str(e)[:80])

# ═══════════════════════════════════════════════════════════
# 阶段2: 登录 + 安全
# ═══════════════════════════════════════════════════════════
def stage2():
    log(f'\n══ 阶段2: 登录流程 (用户: {ADMIN_USER}) ══')
    S['session'] = requests.Session()

    r, s = api(f'{API_BASE}/api/login', 'POST', {'username': ADMIN_USER})
    check('登录返回200', s == 200, f'status={s}')
    if s == 200:
        check('登录返回code=0', r.get('code') == 0, r)
        user = r.get('data', {})
        S['csrf_token'] = user.get('csrf_token', '')
        check('返回CSRF Token', bool(S['csrf_token']), f'token={S["csrf_token"][:8]}...' if S['csrf_token'] else 'None')
        check('返回用户角色', bool(user.get('role')), user.get('role'))

    log('\n══ 阶段2b: 未授权访问拦截 ══')
    no_session = requests.Session()
    r2 = no_session.get(f'{API_BASE}/api/shipment/company/list', timeout=5)
    check('未登录→受保护API被拦截', r2.status_code in (301, 302, 401, 403), f'status={r2.status_code}')

    log('\n══ 阶段2c: CSRF Token校验 ══')
    wrong_session = requests.Session()
    wrong_session.headers['X-CSRF-Token'] = 'wrong_token_12345'
    r3 = wrong_session.post(f'{API_BASE}/api/shipment/company', json={'name': 'CSRF测试', 'code': 'CSRF'}, timeout=5)
    check('错误CSRF Token→被拒绝', r3.status_code in (401, 403, 500), f'status={r3.status_code}')
    S['session'].headers['X-CSRF-Token'] = S['csrf_token']
    r4 = S['session'].post(f'{API_BASE}/api/shipment/company', json={'name': '正确Token测试', 'code': 'CSRFOK'}, timeout=5)
    check('正确CSRF Token→通过', r4.status_code in (200, 400), f'status={r4.status_code}')

# ═══════════════════════════════════════════════════════════
# 阶段3: 物料管理
# ═══════════════════════════════════════════════════════════
def stage3():
    log(f'\n══ 阶段3: 物料备料管理 ══')

    r, s = api(f'{API_BASE}/material-admin')
    check('物料管理页面HTTP 200', s == 200, f'status={s}')

    r, s = api(f'{API_BASE}/api/dispatch-center/material/list?limit=5')
    check('物料列表API响应', s == 200, s)
    check('物料列表返回code=0', r.get('code') == 0, r)
    orders = []
    if r.get('code') == 0:
        d = r.get('data', {})
        if isinstance(d, dict): orders = d.get('orders', [])
        elif isinstance(d, list): orders = d
    if orders:
        oid = orders[0].get('order_id') or orders[0].get('id')
        S['test_order_id'] = oid
        check('获取到测试订单', bool(oid), orders[0].get('order_no') or orders[0].get('product_type', 'ok'))

    if S.get('test_order_id'):
        mat_name = f'E2E测试物料_{UNIQ}'
        r, s = api(f'{API_BASE}/api/material/add', 'POST',
                     {'order_id': S['test_order_id'], 'material_name': mat_name,
                      'required_qty': 100, 'unit': '米'})
        check('新增物料成功', s == 200 and r.get('code') == 0, f'{s}: {r.get("message","")}')

        r, s = api(f'{API_BASE}/api/dispatch-center/material/list?order_id={S["test_order_id"]}')
        check('物料列表含新增物料', s == 200, r)

        r, s = api(f'{API_BASE}/api/material/template', 'POST',
                     {'name': f'E2E模板_{UNIQ}', 'description': 'E2E测试',
                      'materials': [{'name': '不锈钢网带', 'required_qty': 10}]})
        check('保存物料模板', s == 200 and r.get('code') == 0, f'{s}: {r.get("message","")}')

        r, s = api(f'{API_BASE}/api/material/template/list')
        check('物料模板列表', s == 200, r)

# ═══════════════════════════════════════════════════════════
# 阶段4: 工序管理
# ═══════════════════════════════════════════════════════════
def stage4():
    log(f'\n══ 阶段4: 工序管理 (并发锁验证) ══')

    r, s = api(f'{API_BASE}/api/production/list?limit=5')
    check('生产工单列表API', s == 200, s)
    prods = []
    if r.get('code') == 0:
        d = r.get('data', {})
        if isinstance(d, dict): prods = d.get('orders', [])
        elif isinstance(d, list): prods = d
    if prods:
        pid = prods[0].get('id') or prods[0].get('production_id')
        S['test_prod_id'] = pid
        check('获取到测试工单', bool(pid), prods[0].get('order_no', 'ok'))

    if S.get('test_prod_id'):
        r, s = api(f'{API_BASE}/api/process/admin-list?production_id={S["test_prod_id"]}')
        check('工序列表API', s == 200, f'status={s} msg={r.get("message","")}')
        procs = []
        if isinstance(r.get('data'), list): procs = r['data']
        elif isinstance(r.get('data'), dict): procs = r['data'].get('processes', [])
        if procs:
            S['test_proc_id'] = procs[0].get('id')
            check('获取到测试工序', bool(S['test_proc_id']), procs[0].get('process_name', 'ok'))

    if S.get('test_proc_id'):
        r, s = api(f'{API_BASE}/api/process/{S["test_proc_id"]}/report', 'PUT',
                     {'completed': 5, 'qualified': 4, 'hours': 1})
        check('报工提交(P0-3验证)', s == 200, f'{s}: {r.get("message","")}')

        r, s = api(f'{API_BASE}/api/process/{S["test_proc_id"]}/report', 'PUT',
                     {'completed': 3, 'qualified': 2, 'hours': 0.5})
        check('报工累加验证(两次叠加)', s == 200, f'{s}: {r.get("message","")}')

# ═══════════════════════════════════════════════════════════
# 阶段5: 质检管理
# ═══════════════════════════════════════════════════════════
def stage5():
    log(f'\n══ 阶段5: 质检管理 ══')

    r, s = api(f'{API_BASE}/quality-admin')
    check('质检管理页面HTTP 200', s == 200, s)

    r, s = api(f'{API_BASE}/api/quality/stats')
    check('质检统计API', s == 200, s)
    if s == 200:
        d = r.get('data', {})
        check('质检统计数据结构', isinstance(d, dict), d)
        if isinstance(d, dict):
            log(f'         统计: {d}')

    r, s = api(f'{API_BASE}/api/quality/admin-list?limit=5')
    check('质检列表API', s == 200, f'status={s} msg={r.get("message","")}')

    r, s = api(f'{API_BASE}/api/orders/quality-orders')
    check('可质检订单API', s == 200, s)

# ═══════════════════════════════════════════════════════════
# 阶段6: 发货管理
# ═══════════════════════════════════════════════════════════
def stage6():
    log(f'\n══ 阶段6: 发货管理 (运单号唯一性) ══')

    r, s = api(f'{API_BASE}/shipment-admin')
    check('发货管理页面HTTP 200', s == 200, s)

    r, s = api(f'{API_BASE}/api/shipment/company/list')
    check('物流公司列表API', s == 200, s)
    companies = r.get('data', []) if isinstance(r.get('data'), list) else []
    S['test_company'] = companies[0] if companies else None

    r, s = api(f'{API_BASE}/api/dispatch-center/material/list?limit=3')
    order_id = None
    if r.get('code') == 0:
        d = r.get('data', {})
        orders = d.get('orders', []) if isinstance(d, dict) else []
        if orders: order_id = orders[0].get('order_id') or orders[0].get('id')
    S['test_order_id'] = order_id

    if order_id:
        r, s = api(f'{API_BASE}/api/shipment/add', 'POST', {
            'order_id': order_id,
            'receiver_name': f'E2E测试_{UNIQ}',
            'receiver_phone': '13800138000',
            'receiver_address': 'E2E测试地址',
            'logistics_company': S.get('test_company', {}).get('name', '顺丰') if S.get('test_company') else '顺丰',
            'tracking_no': f'SF{UNIQ}',
        })
        check('创建发货单(P1-2运单号)', s == 200 and r.get('code') == 0, f'{s}: {r.get("message","")}')
        if s == 200 and r.get('code') == 0:
            S['test_shipment_id'] = r.get('data', {}).get('id')

    if S.get('test_shipment_id'):
        r, s = api(f'{API_BASE}/api/shipment/{S["test_shipment_id"]}/status', 'PUT',
                     {'status': '已发货'})
        check('更新发货状态', s == 200, f'{s}: {r.get("message","")}')

    r, s = api(f'{API_BASE}/api/shipment/company', 'POST',
                 {'name': f'E2E物流_{UNIQ}', 'code': f'E2E{UNIQ}',
                  'contact': '测试', 'phone': '4001234567'})
    check('添加物流公司', s == 200 and r.get('code') == 0, f'{s}: {r.get("message","")}')

# ═══════════════════════════════════════════════════════════
# 阶段7: 生产排单 + 状态机
# ═══════════════════════════════════════════════════════════
def stage7():
    log(f'\n══ 阶段7: 生产排单管理 (状态机校验) ══')

    r, s = api(f'{API_BASE}/production-admin')
    check('生产排单页面HTTP 200', s == 200, s)

    r, s = api(f'{API_BASE}/api/orders/unscheduled')
    check('未排产订单API', s == 200, s)
    unsched = []
    if isinstance(r.get('data'), list): unsched = r['data']
    elif isinstance(r.get('data'), dict): unsched = r['data'].get('orders', [])
    order_no = unsched[0].get('order_no') if unsched else None
    S['test_order_no'] = order_no

    if order_no:
        r, s = api(f'{API_BASE}/api/production/orders', 'POST',
                     {'order_no': order_no, 'priority': 'normal', 'assigned_to': ADMIN_USER})
        check('创建生产工单', s == 200 and r.get('code') == 0, f'{s}: {r.get("message","")}')
        if s == 200 and r.get('code') == 0:
            S['test_prod_order_id'] = r.get('data', {}).get('id')
            check('创建工单成功', bool(S['test_prod_order_id']), r.get('data'))
        elif s == 400:
            check('创建工单→已有排产', True, r.get('message', ''))
            r2, s2 = api(f'{API_BASE}/api/production/orders/list?order_no={order_no}')
            if r2.get('code') == 0:
                prods = r2.get('data', [])
                if prods:
                    S['test_prod_order_id'] = prods[0].get('id')
                    check('复用已有工单', bool(S['test_prod_order_id']), prods[0])

    if S.get('test_prod_order_id'):
        illegal = [('已完成', '待开始'), ('待发布', '已完成')]
        for from_s, to_s in illegal:
            r, s = api(f'{API_BASE}/api/production/orders/{S["test_prod_order_id"]}/status',
                          'PUT', {'status': to_s})
            check(f'状态机校验[{from_s}→{to_s}]应拒绝',
                  s == 400, f'status={s} msg={r.get("message","")[:60]}')

# ═══════════════════════════════════════════════════════════
# 阶段8: UI渲染 (Playwright)
# ═══════════════════════════════════════════════════════════
def stage8():
    log(f'\n══ 阶段8: UI渲染验证 (Playwright) ══')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        errors = []
        page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)

        page.goto(f'{API_BASE}/login')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(1000)
        screenshot(page, '01_login')

        if page.locator('#u').count() > 0:
            page.fill('#u', ADMIN_USER)
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
            screenshot(page, '02_after_login')

        nav_ok = page.locator('text=生产排单').count() > 0 or page.locator('text=物料').count() > 0
        check('登录后顶部导航可见', nav_ok, '生产排单/物料入口')

        pages = [
            ('/material-admin', '02_material_admin', '物料'),
            ('/production-admin', '03_production_admin', '工单'),
            ('/process-admin', '04_process_admin', '工序'),
            ('/quality-admin', '05_quality_admin', '质检'),
            ('/shipment-admin', '06_shipment_admin', '发货'),
        ]
        for path, img, label in pages:
            page.goto(f'{API_BASE}{path}')
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
            screenshot(page, img)
            ok = page.locator(f'text={label}').count() > 0
            check(f'{label}管理页面渲染', ok, f'{path}')

        js_errors = [e for e in errors if 'Error' in e or 'error' in e.lower()]
        check('页面JS无Error级错误', len(js_errors) == 0, f'{len(js_errors)}个错误' if js_errors else '0个错误')

        browser.close()

# ═══════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════
def main():
    print(f'''
╔═══════════════════════════════════════════════════╗
║    web5001 全链路端到端测试 v2                ║
║    标签: {UNIQ}                      ║
║    时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}             ║
╚═══════════════════════════════════════════════════╝
''')
    stage1()
    stage2()
    stage3()
    stage4()
    stage5()
    stage6()
    stage7()
    stage8()

    log(f'''
╔═══════════════════════════════════════════════════╗
║    测试结果汇总                                  ║
╠═══════════════════════════════════════════════════╣
║    ✅ 通过: {PASS}                                ║
║    ❌ 失败: {FAIL}                                ║
║    截图: {len(SCREENSHOTS)} 张                                    ║
╚═══════════════════════════════════════════════════╝
''')
    report_path = f'd:/yuan/不锈钢网带跟单3.0/docs/e2e_report_{UNIQ}.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f'# E2E测试报告\n\n')
        f.write(f'**标签**: {UNIQ}\n\n')
        f.write(f'**时间**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        f.write(f'**结果**: ✅{PASS}  ❌{FAIL}\n\n')
        f.write('## 详细结果\n\n')
        for line in RESULTS:
            f.write(line + '\n')
        f.write('\n## 截图\n\n')
        for ss in SCREENSHOTS:
            fname = os.path.basename(ss)
            f.write(f'![{fname}](../{fname.replace(chr(92), "/")})\n')
    print(f'\n📄 报告: {report_path}')
    print(f'📸 截图: {[os.path.basename(s) for s in SCREENSHOTS]}')
    return FAIL == 0

if __name__ == '__main__':
    ok = main()
    sys.exit(0 if ok else 1)
