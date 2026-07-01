# -*- coding: utf-8 -*-
"""向智能表格写入工单演示"""
import requests, json, sys

sys.stdout.reconfigure(encoding='utf-8')

URL = 'https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/webhook?key=64eA1txLc3fAZMt2NCyxs2xltBZgmaEiPhv66IBMzJEplpfHEESIc4yWhdNa7uJ4Ynt6SF3bm2QhM8uq6VtIRtvyuCU0IpupRK6LVjFmEhoj'

payload = {
    'schema': {
        'fabcde': '分类',
        'f3TVj5': '订单号',
        'f4lY4B': '客户名称',
        'fexnsG': '产品类型',
        'flrEhY': '材质',
        'fbAHzS': '状态',
        'fALAF6': '创建日期',
        'fj7LI3': '订单数量',
        'f7jOiq': '单位',
        'f0kcf1': '订单号',
        'fvy2Zd': '当前工序',
        'fS7rCo': '数据来源',
        'fIjGmz': '工序总数',
        'fceF0M': '备注'
    },
    'add_records': [
        {
            'values': {
                'fabcde': '生产工单',
                'f3TVj5': 'WO-202605006',
                'f4lY4B': '山东济南食品',
                'fexnsG': '平板型网带',
                'flrEhY': '304不锈钢',
                'fbAHzS': '已创建',
                'fALAF6': '2026-05-17',
                'fj7LI3': '50',
                'f7jOiq': '件',
                'f0kcf1': 'ORD-202604290001',
                'fvy2Zd': '原材料准备',
                'fS7rCo': '跟单系统',
                'fIjGmz': '11',
                'fceF0M': '工单演示数据'
            }
        }
    ]
}

resp = requests.post(URL, json=payload, timeout=15)
result = resp.json()
print(json.dumps(result, ensure_ascii=False, indent=2))

if result.get('errcode') == 0:
    print('\n写入成功')
else:
    print('\n写入失败: ' + result.get('errmsg', ''))
