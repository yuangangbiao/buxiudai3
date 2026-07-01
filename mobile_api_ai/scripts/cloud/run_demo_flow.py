#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全程模拟：从软件端发布任务 -> 工人扫码确认 -> 报工完成
同时记录日志到文件 demo_flow_result.txt
"""
import os
import sys
import json
import time
import requests

BASE = 'http://localhost:5002'
LOG_FILE = 'demo_flow_result.txt'

log = None


def w(text=''):
    print(text)
    if log:
        print(text, file=log)


def step(num, title):
    w()
    w('=' * 60)
    w('  第%d步：%s' % (num, title))
    w('=' * 60)


def ok(msg, detail=''):
    w('  [OK] ' + msg)
    if detail:
        w('      ' + detail)


def fail(msg, detail=''):
    w('  [FAIL] ' + msg)
    if detail:
        w('      ' + detail)


def main():
    global log
    log = open(LOG_FILE, 'w', encoding='utf-8')

    w('=' * 60)
    w('  模拟从软件端发出任务的完整流程')
    w('=' * 60)
    w('  容器中心: ' + BASE)
    w('  时间: ' + time.strftime('%Y-%m-%d %H:%M:%S'))
    w()

    # Step 1
    step(1, '服务健康检查')
    try:
        r = requests.get(BASE + '/health', timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        ok('服务健康检查通过', '版本: ' + d['data']['version'])
    except Exception as e:
        fail('服务未启动', str(e))
        log.close()
        return

    # Step 2
    step(2, '操作员登录 - 张三')
    try:
        r = requests.post(BASE + '/api/auth/login',
                          json={'operator_id': 'OP001'}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        op = d['data']['operator']
        ok('登录成功: ' + op['name'] + '(' + op['id'] + ')',
           '角色: ' + op['role'] + ', 班组: ' + op['team_name'])
        token = d['data']['token']
        headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    except Exception as e:
        fail('登录失败', str(e))
        log.close()
        return

    # Step 3
    step(3, '查看容器池初始状态')
    try:
        r = requests.post(BASE + '/api/auth/login',
                          json={'operator_id': 'MG001'}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        mgr_token = r.json()['data']['token']
        r = requests.get(BASE + '/api/pool/status',
                         headers={'Authorization': 'Bearer ' + mgr_token}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        ok('容器池状态', json.dumps(r.json()['data'], ensure_ascii=False, indent=2))
    except Exception as e:
        ok('提示', '跳过-仅管理员可查看')

    # Step 4
    step(4, '模拟软件端发布报工任务')
    payload = {
        'task_type': 'report',
        'title': '编织工序报工',
        'content': {
            'order_no': 'ORD2026050801',
            'process_name': '编织',
            'process_seq': 1,
            'planned_qty': 100,
            'unit': '米'
        },
        'operator_id': 'OP001',
        'priority': 'high',
        'related_order': 'ORD2026050801',
        'tags': ['编织', '一班']
    }
    try:
        r = requests.post(BASE + '/api/internal/publish',
                          json=payload, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        task_id = d['task_id']
        ok('任务已发布: ' + task_id, '订单: ORD2026050801 | 编织 100米')
    except Exception as e:
        fail('发布失败', str(e))
        log.close()
        return
    time.sleep(0.3)

    # Step 5
    step(5, '确认任务进入容器池')
    try:
        r = requests.get(BASE, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        pool = r.json()['data']['pool_status']
        ok('容器池状态', json.dumps(pool, ensure_ascii=False, indent=2))
    except Exception as e:
        ok('获取状态', str(e))

    # Step 6
    step(6, '模拟工人扫码/派发任务')
    try:
        r = requests.post(BASE + '/api/tasks/dispatch',
                          json={'task_types': ['report'], 'max_count': 10},
                          headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        ok('派发结果: ' + d['message'])
        for t in d['data']['tasks']:
            ok('  任务 ' + t['id'] + ': ' + t['title'] + ' [' + t['status'] + ']')
    except Exception as e:
        fail('派发失败', str(e))

    # Step 7
    step(7, '查看待处理任务')
    try:
        r = requests.get(BASE + '/api/tasks?types=report',
                         headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        tasks = r.json()['data']['tasks']
        ok('待处理任务: ' + str(len(tasks)) + '个')
    except Exception as e:
        ok('获取任务列表', str(e))

    # Step 8
    step(8, '扫码确认开始执行')
    try:
        r = requests.post(BASE + '/api/tasks/' + task_id + '/start',
                          headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        ok('开始执行', '状态: ' + d['data']['status'] +
           ' | 开始时间: ' + str(d['data'].get('started_at', 'N/A')))
    except Exception as e:
        fail('开始任务失败', str(e))

    # Step 9
    step(9, '工人报工完成')
    result = {
        'completed_qty': 100,
        'defect_qty': 2,
        'status': 'completed',
        'quality': '合格',
        'remark': '编织完成，2米瑕疵已标记',
        'work_time_minutes': 45,
        'operator_name': '张三'
    }
    try:
        r = requests.post(BASE + '/api/tasks/' + task_id + '/complete',
                          json=result, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        ok('报工结果', json.dumps(d, ensure_ascii=False, indent=2))
    except Exception as e:
        fail('报工失败', str(e))

    # Step 10
    step(10, '全流程验证')
    try:
        r = requests.get(BASE + '/api/tasks/' + task_id,
                         headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        t = r.json()['data']
        ok('任务详情',
           '状态: ' + t['status'] +
           ' | 完成时间: ' + str(t.get('completed_at', 'N/A')))

        r = requests.get(BASE + '/api/pool/status',
                         headers={'Authorization': 'Bearer ' + mgr_token}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        ok('最终容器池', json.dumps(r.json()['data'], ensure_ascii=False, indent=2))
    except Exception as e:
        fail('验证失败', str(e))

    # Summary
    w()
    w('=' * 60)
    w('  *** 全流程模拟完成！***')
    w('=' * 60)
    w('  流程: 软件端 -> API -> 容器池 -> 派发 -> 扫码 -> 报工')
    w('  任务: 编织报工 100米 | 操作员: 张三 | 质量: 合格')
    w('  任务ID: ' + task_id + ' | 耗时: 45分钟 | 瑕疵: 2米')
    w('=' * 60)

    log.close()
    print()
    print('结果已保存到: ' + LOG_FILE)


if __name__ == '__main__':
    main()
