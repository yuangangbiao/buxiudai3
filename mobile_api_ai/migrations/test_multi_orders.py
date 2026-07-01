# -*- coding: utf-8 -*-
"""测试多个工单的按 process_code 分类"""
import requests
import json

orders = ['ORD-202604210002', 'ORD-202604210004', 'ORD-202605010001', 'ORD-202604160001']

for order_no in orders:
    print('=' * 60)
    print('工单:', order_no)
    print('=' * 60)
    resp = requests.get('http://localhost:5003/api/dispatch-center/workorder/{}'.format(order_no), timeout=10)
    if resp.status_code != 200:
        print('  错误:', resp.text[:200])
        continue
    d = resp.json().get('data', {})
    print('  product_name:', d.get('product_name'))
    print('  status:', d.get('status'))
    print()
    print('  --- 按 data_type 分类 ---')
    for k in ['process_tasks', 'material_tasks', 'quality_tasks', 'repair_tasks', 'outsource_tasks', 'flow_steps']:
        tasks = d.get(k, [])
        print('    {}: {} 条'.format(k, len(tasks)))
    print()
    print('  --- 按 process_code 分类（与手机报工一致）---')
    for k in ['production_tasks', 'material_tasks_v2', 'quality_tasks_v2', 'warehousing_tasks', 'ignored_tasks']:
        tasks = d.get(k, [])
        print('    {}: {} 条'.format(k, len(tasks)))
    print()
    print('  --- 详细任务列表 ---')
    for k in ['production_tasks', 'material_tasks_v2', 'quality_tasks_v2', 'warehousing_tasks', 'ignored_tasks']:
        tasks = d.get(k, [])
        if tasks:
            print('  [{}]'.format(k))
            for t in tasks:
                code = t.get('process_code', '')
                related = (t.get('related_process') or '')[:30]
                status = t.get('status', '')
                print('    code={}, related={}, status={}'.format(code, related, status))
    print()
