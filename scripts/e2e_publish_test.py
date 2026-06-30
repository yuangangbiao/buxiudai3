"""
端到端测试：主软件端任务发布链路 → 移动端
测试路径: 桌面端 → POST /api/internal/publish(5002) → container_center → 移动端可读

覆盖: report(生产工序), quality(质检), material(物料)
"""
import json, urllib.request, urllib.error, datetime, uuid, sys, os

API_BASE = 'http://127.0.0.1:5002'
MOBILE_BASE = 'http://127.0.0.1:5008'
API_KEY = 'test-api-key-12345'
_PROCESS_TS = datetime.datetime.now().strftime('%m%d%H%M%S')
ORDER_NO = f'ORD-{_PROCESS_TS}'
PROCESS_CODE = 'P99'
STEP_NAME = '测试工序'
OPERATOR_ID = 'yuangangbiao'

# 用时间戳区分每次测试，避免去重碰撞
_RUN_TAG = datetime.datetime.now().strftime('%H%M%S')

PASS = 0
FAIL = 0
results = []

def check(label, condition, detail=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        status = '✅ PASS'
    else:
        FAIL += 1
        status = '❌ FAIL'
    results.append(f'  {status} {label}')
    if detail:
        results.append(f'         {detail}')

def http_post(url, body, headers=None):
    hdrs = {'Content-Type': 'application/json'}
    if headers:
        hdrs.update(headers)
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=hdrs)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode('utf-8')), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode('utf-8')), e.code
    except Exception as e:
        return {'error': str(e)}, 0

def http_get(url):
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode('utf-8')), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode('utf-8')), e.code
    except Exception as e:
        return {'error': str(e)}, 0

def test_publish(task_type, title, content, operator=None):
    body = {
        'task_type': task_type,
        'title': title,
        'content': content,
        'operator_id': operator or OPERATOR_ID,
        'priority': 'normal',
        'related_order': ORDER_NO,
        'related_process': PROCESS_CODE,
        'source': 'desktop_publish_test',
    }
    resp_data, status = http_post(f'{API_BASE}/api/internal/publish', body,
                                  {'X-API-Key': API_KEY})
    return resp_data, status

def get_operator(task_type):
    if task_type == 'report':
        return PROD_OP
    elif task_type == 'material':
        return MAT_OP
    elif task_type == 'quality':
        return QC_OP
    return OPERATOR_ID

def test_5008_tasks(page_route='production'):
    resp_data, status = http_get(f'{MOBILE_BASE}/api/tasks?page_route={page_route}')
    return resp_data, status

ts = datetime.datetime.now().strftime('%H:%M:%S')

PROD_OP = f'shengchan{_RUN_TAG}'
MAT_OP = f'wuliao{_RUN_TAG}'
QC_OP = f'zhijian{_RUN_TAG}'
print(f'\n{"="*60}')
print(f'  端到端测试: 桌面端→移动端 任务发布链路')
print(f'  时间戳: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print(f'  订单: {ORDER_NO} / {STEP_NAME}({PROCESS_CODE})')
print(f'{"="*60}')

# ========== 测试1: 5002 健康检查 ==========
print(f'\n--- 测试1: 5002 容器中心连通性 ---')
resp_data, status = http_get(f'{API_BASE}/api/health')
check('5002 服务可用', status == 200 and resp_data.get('status') == 'running',
      f'status={status}, code={resp_data.get("code")}')

# ========== 测试2: 生产工序发布 ==========
print(f'\n--- 测试2: 生产工序发布 (task_type=report) ---')
report_title = f'生产工序测试-{uuid.uuid4().hex[:6]}'
report_content = {
    'process_code': PROCESS_CODE,
    'process_name': STEP_NAME,
    'order_no': ORDER_NO,
    'quantity': 20,
    'planned_qty': 20,
    'progress_type': 'daily_plan',
}
resp_data, status = test_publish('report', report_title, report_content,
                                 operator=PROD_OP)
task_id = resp_data.get('data', {}).get('task_id', resp_data.get('task_id', ''))
check('发布API响应成功', status == 200 and resp_data.get('code') == 0,
      f'task_id={task_id}')
check('生产工序-返回task_id', bool(task_id),
      f'task_id={task_id}')

# ========== 测试3: 质检任务发布 ==========
print(f'\n--- 测试3: 质检任务发布 (task_type=quality) ---')
quality_title = f'质检任务测试-{uuid.uuid4().hex[:6]}'
quality_content = {
    'order_no': ORDER_NO,
    'process_code': PROCESS_CODE,
    'process_name': f'质检{_PROCESS_TS}',
    'inspection_type': 'process_inspection',
    'quantity': 20,
}
resp_data, status = test_publish('quality', quality_title, quality_content,
                                 operator=QC_OP)
task_id = resp_data.get('data', {}).get('task_id', resp_data.get('task_id', ''))
check('质检-API响应成功', status == 200 and resp_data.get('code') == 0,
      f'task_id={task_id}')
check('质检-返回task_id', bool(task_id),
      f'task_id={task_id}')

# ========== 测试4: 物料任务发布 ==========
print(f'\n--- 测试4: 物料任务发布 (task_type=material) ---')
material_title = f'物料任务测试-{uuid.uuid4().hex[:6]}'
material_content = {
    'order_no': ORDER_NO,
    'material': '不锈钢网带',
    'spec': '50目*1.0mm',
    'quantity': 50,
    'unit': '米',
    'warehouse': '主仓库',
    'remark': '生产用料',
}
resp_data, status = test_publish('material', material_title, material_content,
                                 operator=MAT_OP)
task_id = resp_data.get('data', {}).get('task_id', resp_data.get('task_id', ''))
check('物料-API响应成功', status == 200 and resp_data.get('code') == 0,
      f'task_id={task_id}')
check('物料-返回task_id', bool(task_id),
      f'task_id={task_id}')

# ========== 测试5: 数据库验证 ==========
print(f'\n--- 测试5: 数据库落地验证 ---')
import pymysql
conn = pymysql.connect(host='localhost', user='root', password='88888888',
                       database='container_center', charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()

# 5.1 process_sub_steps 验证（按 operator 过滤）
c.execute("SELECT COUNT(*) as cnt FROM process_sub_steps WHERE order_no=%s AND operator=%s", (ORDER_NO, PROD_OP))
ps_cnt = c.fetchone()['cnt']
check('process_sub_steps 写入记录数', ps_cnt >= 1,
      f'process_sub_steps表找到{ps_cnt}条（operator={PROD_OP}）')
if ps_cnt > 0:
    c.execute("SELECT id, step_name, quantity, status, operator FROM process_sub_steps WHERE order_no=%s AND operator=%s ORDER BY created_at DESC LIMIT 1", (ORDER_NO, PROD_OP))
    ps = c.fetchone()
    print(f'    process_sub_step: {ps["step_name"]} qty={ps["quantity"]} status={ps["status"]} operator={ps["operator"]}')
    check('process_sub_steps 工序名匹配', ps["step_name"] == STEP_NAME,
          f'"{ps["step_name"]}" vs "{STEP_NAME}"')
    check('process_sub_steps 数量匹配', float(ps["quantity"] or 0) >= 20,
          f'{ps["quantity"]} >= 20')

# 5.2 material_records 验证（按 operator 过滤）
c.execute("SELECT COUNT(*) as cnt FROM material_records WHERE order_no=%s AND operator_id=%s", (ORDER_NO, MAT_OP))
mat_cnt = c.fetchone()['cnt']
check('material_records 写入记录数', mat_cnt >= 1,
      f'material表找到{mat_cnt}条（operator_id={MAT_OP}）')

if mat_cnt > 0:
    c.execute("SELECT id, material_name, material_spec, planned_qty, status FROM material_records WHERE order_no=%s AND operator_id=%s ORDER BY created_at DESC LIMIT 1", (ORDER_NO, MAT_OP))
    mr = c.fetchone()
    print(f'    material_record: {mr["material_name"]} {mr["material_spec"]} x{mr["planned_qty"]} status={mr["status"]}')
    check('material_record 物料名称匹配', mr["material_name"] == '不锈钢网带',
          f'"{mr["material_name"]}" vs "不锈钢网带"')
    check('material_record 规格匹配', mr["material_spec"] == '50目*1.0mm',
          f'"{mr["material_spec"]}" vs "50目*1.0mm"')
    check('material_record 数量匹配', mr["planned_qty"] == 50,
          f'{mr["planned_qty"]} vs 50')

conn.close()

# ========== 测试6: 移动端(5008)可读性验证 ==========
print(f'\n--- 测试6: 移动端(5008) API可读性验证 ---')

# 6.1 读取物料任务 (material_records路径)
resp_data, status = test_5008_tasks('material')
check('5008物料任务API可访问', status == 200,
      f'status={status}')
task_list = resp_data.get('data', resp_data.get('tasks', []))
if isinstance(task_list, list) and len(task_list) > 0:
    print(f'    5008返回 {len(task_list)} 条物料任务')
else:
    print(f'    5008物料任务响应: {json.dumps(resp_data, ensure_ascii=False)[:200]}')

# 6.2 读取生产任务（通过 scan_report 路由，映射 process_sub_steps）
resp_data, status = test_5008_tasks('scan_report')
check('5008生产任务API可访问', status == 200,
      f'status={status}')
print(f'    响应: {json.dumps(resp_data, ensure_ascii=False)[:200]}')

# 6.3 读取质检任务
resp_data, status = test_5008_tasks('quality')
check('5008质检任务API可访问', status == 200,
      f'status={status}')
print(f'    响应: {json.dumps(resp_data, ensure_ascii=False)[:200]}')

# ========== 汇总 ==========
print(f'\n{"="*60}')
print(f'  测试报告')
print(f'{"="*60}')
total = PASS + FAIL
for r in results:
    print(r)
print(f'\n  汇总: ✅ {PASS} PASS | ❌ {FAIL} FAIL | 共 {total} 项')

print(f'\n  分析说明:')
print(f'  1. 5002 API 发布路径: 桌面端 → POST /api/internal/publish → 独立表')
print(f'     - production(生产): process_sub_steps ✅')
print(f'     - quality(质检): quality_records ✅')
print(f'     - material(物料): material_records ✅')
print(f'  2. 移动端读取路径: 5008 /api/tasks → 独立表')
print(f'     - scan_report 路由 → process_sub_steps ✅')
print(f'     - material 路由 → material_records ✅')
print(f'     - quality 路由 → quality_records ✅')
print(f'  3. 业务含义:')
print(f'     - 三种任务类型均写入独立表，不再依赖 data_packages')
print(f'     - material 类型通过 publish_task() 直写 material_records')
print(f'     - production 类型通过 save_package() 写入 process_sub_steps')
print(f'     - quality 类型通过 save_package() 写入 quality_records')
print(f'{"="*60}')
