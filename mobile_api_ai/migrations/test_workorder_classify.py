# -*- coding: utf-8 -*-
"""测试 workorder_detail API 新增的按 process_code 分类字段"""
import requests
import json

resp = requests.get('http://localhost:5003/api/dispatch-center/workorder/ORD-202604210002', timeout=10)
print('Status:', resp.status_code)
if resp.status_code == 200:
    d = resp.json().get('data', {})
    print('order_no:', d.get('order_no'))
    print()
    print('--- 按 data_type 分类（原有 6 类）---')
    for k in ['process_tasks', 'material_tasks', 'quality_tasks', 'repair_tasks', 'outsource_tasks', 'flow_steps']:
        tasks = d.get(k, [])
        print('  {}: {} 条'.format(k, len(tasks)))
    print()
    print('--- 按 process_code 分类（新增 5 类，与手机报工一致）---')
    for k in ['production_tasks', 'material_tasks_v2', 'quality_tasks_v2', 'warehousing_tasks', 'ignored_tasks']:
        tasks = d.get(k, [])
        print('  {}: {} 条'.format(k, len(tasks)))
    print()
    print('--- 详细列出按 process_code 分类的任务 ---')
    for k in ['production_tasks', 'material_tasks_v2', 'quality_tasks_v2', 'warehousing_tasks', 'ignored_tasks']:
        tasks = d.get(k, [])
        for t in tasks[:3]:
            code = t.get('process_code', '')
            related = (t.get('related_process') or '')[:30]
            status = t.get('status', '')
            print('  [{}] code={}, related={}, status={}'.format(k, code, related, status))
else:
    print('Error:', resp.text[:500])
