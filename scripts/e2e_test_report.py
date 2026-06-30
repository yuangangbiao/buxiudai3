# -*- coding: utf-8 -*-
"""
端到端报工测试：从页面端(5008) → 调度中心(5003) → 同步桥(8008) → 桌面端(steel_belt)

测试流程:
  1. 调用5008 API报工 (P07 编制右旋 +10个)
  2. 等待异步同步 (5003→8008 queue worker 1s轮询)
  3. 验证 4 个节点数据状态
  4. 清理测试数据（可跳过）

测试订单: ORD-202604210002
测试工序: 编制右旋 (P07)
当前状态: completed_qty=50, planned_qty=100, status=in_progress
测试数量: 10
操作员: 苑岗彪
"""
import json
import time
import sys
import os
import pymysql
import urllib.request
import urllib.error

API_URL = 'http://127.0.0.1:5008/api/process_sub_step'

STEEL_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '88888888',
    'database': 'steel_belt', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

CC_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '88888888',
    'database': 'container_center', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

BATCH_NO = f'E2E-TEST-{time.strftime("%Y%m%d%H%M%S")}'
OPERATOR = '苑岗彪'
ORDER_NO = 'ORD-202604210002'
PROCESS_CODE = 'P07'
STEP_NAME = '编制右旋'
QTY = 10

passed = 0
failed = 0

results = []


def check(label, condition, detail=''):
    global passed, failed
    status = 'PASS' if condition else 'FAIL'
    if condition:
        passed += 1
    else:
        failed += 1
    print(f'  [{status}] {label}')
    if detail:
        print(f'          {detail}')
    results.append((status, label, detail))


def db_query(config, sql, params=None):
    conn = pymysql.connect(**config)
    try:
        with conn.cursor() as c:
            c.execute(sql, params or ())
            return c.fetchall()
    finally:
        conn.close()


print(f'{"="*60}')
print(f'端到端报工测试')
print(f'{"="*60}')
print(f'订单: {ORDER_NO}')
print(f'工序: {STEP_NAME} ({PROCESS_CODE})')
print(f'数量: +{QTY}')
print(f'操作员: {OPERATOR}')
print(f'批次: {BATCH_NO}')
print(f'{">"*60}')

print(f'\n--- 步骤1: 记录报工前状态 ---')
before_pr = db_query(STEEL_CONFIG,
    "SELECT id, process_name, process_code, planned_qty, completed_qty, status "
    "FROM process_records WHERE order_no=%s AND process_code=%s",
    (ORDER_NO, PROCESS_CODE))
if before_pr:
    r = before_pr[0]
    print(f'  process_records: id={r["id"]}, {r["process_name"]}({r["process_code"]})')
    print(f'    完成量={r["completed_qty"]}, 计划量={r["planned_qty"]}, 状态={r["status"]}')
    before_completed = r['completed_qty']
    pr_id = r['id']
else:
    print(f'  [FAIL] 未找到 process_records 记录')
    sys.exit(1)

print(f'\n--- 步骤2: 调用5008 API报工 ---')
payload = {
    'order_no': ORDER_NO,
    'process_code': PROCESS_CODE,
    'quantity': QTY,
    'operator': OPERATOR,
    'batch_no': BATCH_NO
}
data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(API_URL, data=data,
    headers={'Content-Type': 'application/json'})

try:
    resp = urllib.request.urlopen(req, timeout=15)
    resp_body = json.loads(resp.read().decode('utf-8'))
    print(f'  请求体: {json.dumps(payload, ensure_ascii=False)}')
    print(f'  响应: {json.dumps(resp_body, ensure_ascii=False)}')
    check('5008 API 返回成功', resp_body.get('code') == 0,
          f'message={resp_body.get("message")}')
    check('同步状态正常', resp_body.get('sync_status') == 'ok',
          f'sync_status={resp_body.get("sync_status")}')
except Exception as e:
    print(f'  [FAIL] 5008 API 调用失败: {e}')
    check('5008 API 调用', False, str(e))
    sys.exit(1)

print(f'\n--- 步骤3: 等待异步同步 (10s) ---')
for i in range(10):
    print(f'  等待中... {i+1}s', end='\r')
    time.sleep(1)
print(f'  等待完成                              ')

print(f'\n--- 步骤4: 验证 container_center.process_sub_steps ---')
cc_records = db_query(CC_CONFIG,
    "SELECT id, order_no, step_name, process_code, quantity, operator, batch_no, "
    "status, created_at FROM process_sub_steps "
    "WHERE order_no=%s AND batch_no=%s",
    (ORDER_NO, BATCH_NO))
check(f'container_center 存在记录 (batch_no={BATCH_NO})',
      len(cc_records) > 0,
      f'找到 {len(cc_records)} 条')
if cc_records:
    r = cc_records[0]
    check(f'  订单号一致', r['order_no'] == ORDER_NO)
    check(f'  工序名一致', r['step_name'] == STEP_NAME)
    check(f'  数量一致', float(r['quantity']) == QTY)
    check(f'  操作员一致', r['operator'] == OPERATOR)

print(f'\n--- 步骤5: 验证 steel_belt.process_sub_steps ---')
sb_records = db_query(STEEL_CONFIG,
    "SELECT id, process_id, process_record_id, order_no, step_name, quantity, "
    "operator, batch_no, source, synced, created_at FROM process_sub_steps "
    "WHERE order_no=%s AND batch_no=%s",
    (ORDER_NO, BATCH_NO))
check(f'steel_belt 存在记录 (batch_no={BATCH_NO})',
      len(sb_records) > 0,
      f'找到 {len(sb_records)} 条')
if sb_records:
    r = sb_records[0]
    check(f'  订单号一致', r['order_no'] == ORDER_NO)
    check(f'  工序名一致', r['step_name'] == STEP_NAME)
    check(f'  数量一致', float(r['quantity']) == QTY)
    check(f'  操作员一致', r['operator'] == OPERATOR)
    check(f'  来源为 dispatch_center', r.get('source') in ('dispatch_center', 'sync_bridge'),
          f'source={r.get("source")}')
    check(f'  同步标记已设置', r.get('synced') == 1,
          f'synced={r.get("synced")}')

print(f'\n--- 步骤6: 验证 steel_belt.process_records 进度更新 ---')
after_pr = db_query(STEEL_CONFIG,
    "SELECT id, completed_qty, qualified_qty, status, updated_at "
    "FROM process_records WHERE id=%s", (pr_id,))
if after_pr:
    r = after_pr[0]
    expected_qty = before_completed + QTY
    print(f'  报工前: completed_qty={before_completed}')
    print(f'  报工后: completed_qty={r["completed_qty"]}')
    print(f'  预期:   completed_qty={expected_qty}')
    check(f'  completed_qty 从 {before_completed} 更新为 {r["completed_qty"]}',
          r['completed_qty'] == expected_qty,
          f'期望={expected_qty}, 实际={r["completed_qty"]}')
    check(f'  状态仍为 in_progress (50+10=60 < 100)',
          r['status'] == 'in_progress',
          f'status={r["status"]}')
else:
    check('查询 process_records 更新', False, '未找到记录')


print(f'\n{"="*60}')
print(f'测试结果汇总')
print(f'{"="*60}')
print(f'通过: {passed} | 失败: {failed} | 总计: {passed+failed}')
print()

if failed == 0:
    print(f'✅ 端到端报工测试全部通过！')
    print(f'   数据流: 页面端(5008) → 调度中心(5003) → 同步桥(8008) → 桌面端(steel_belt)')
    print(f'   验证点:')
    print(f'     - 5008 API 返回成功')
    print(f'     - container_center.process_sub_steps 写入成功')
    print(f'     - steel_belt.process_sub_steps 同步成功')
    print(f'     - steel_belt.process_records 进度更新正确')
else:
    print(f'❌ 端到端报工测试失败，存在 {failed} 个失败点')

print(f'\n测试数据标识: batch_no={BATCH_NO}')
print(f'如需清理，可执行:')
print(f'  DELETE FROM container_center.process_sub_steps WHERE batch_no="{BATCH_NO}";')
print(f'  DELETE FROM steel_belt.process_sub_steps WHERE batch_no="{BATCH_NO}";')
print(f'  UPDATE steel_belt.process_records SET completed_qty={before_completed}')
print(f'    WHERE id={pr_id};')
