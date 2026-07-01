#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全程模拟：从软件端发布任务 → 工人扫码确认 → 报工完成
流程: 登录 → 发布 → 派发 → 扫码开始 → 完成报工
"""
import os
import sys
import requests
import json
import time

os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = 'http://localhost:5002'

def log_step(step: str, status: str, detail: str = ''):
    mark = '[OK]' if status == 'OK' else '[FAIL]' if status == 'FAIL' else '[--]'
    line = f'  {mark} {step}'
    print(line)
    if detail:
        print(f'      {detail}')
    # 同时写入日志文件
    if hasattr(log_step, 'log_file'):
        print(line, file=log_step.log_file)
        if detail:
            print(f'      {detail}', file=log_step.log_file)


def print_separator(title: str):
    print()
    print('=' * 60)
    print(f'  {title}')
    print('=' * 60)
    if hasattr(log_step, 'log_file'):
        print(file=log_step.log_file)
        print('=' * 60, file=log_step.log_file)
        print(f'  {title}', file=log_step.log_file)
        print('=' * 60, file=log_step.log_file)


def main():
    # 打开日志文件
    log_step.log_file = open('demo_flow_output.txt', 'w', encoding='utf-8')
    print_separator('模拟从软件端发出任务的完整流程')
    print(f'  容器中心: {BASE_URL}')
    print(f'  时间: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    # ── 第1步: 健康检查 ──
    print_separator('第1步：检查服务状态')
    try:
        r = requests.get(f'{BASE_URL}/health', timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        data = r.json()
        assert data.get('code') == 0
        log_step('服务健康检查', 'OK', f'版本: {data["data"]["version"]}')
    except Exception as e:
        log_step('服务健康检查', 'FAIL', f'请先启动服务: python start_all.py')
        return

    # ── 第2步: 登录(张三 - 工人) ──
    print_separator('第2步：操作员登录')
    token = None
    try:
        r = requests.post(f'{BASE_URL}/api/auth/login', json={'operator_id': 'OP001'}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        data = r.json()
        assert data.get('code') == 0
        token = data['data']['token']
        op = data['data']['operator']
        log_step(f'登录成功: {op["name"]}({op["id"]})', 'OK',
                 f'角色: {op["role"]}, 班组: {op["team_name"]}')
    except Exception as e:
        log_step('登录失败', 'FAIL', str(e))
        return

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    # ── 第3步: 查看当前容器池初始状态(用主管账号查看) ──
    print_separator('第3步：查看容器池初始状态')
    try:
        r_mgr = requests.post(f'{BASE_URL}/api/auth/login',
                              json={'operator_id': 'MG001'}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        mgr_data = r_mgr.json()
        mgr_token = mgr_data['data']['token']
        r = requests.get(f'{BASE_URL}/api/pool/status',
                         headers={'Authorization': f'Bearer {mgr_token}'}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        data = r.json()
        log_step('容器池状态', 'OK', json.dumps(data.get('data', {}), ensure_ascii=False))
    except Exception as e:
        log_step('获取状态(跳过:仅管理员可查看)', '--', str(e))

    # ── 第4步: 发布报工任务(模拟软件端发出任务) ──
    print_separator('第4步：模拟软件端发布报工任务')
    task_id = None
    try:
        payload = {
            'task_type': 'report',
            'title': '编织工序报工',
            'content': {
                'order_no': 'ORD2026050801',
                'process_name': '编织',
                'process_seq': 1,
                'planned_qty': 100,
                'completed_qty': 0,
                'unit': '米',
                'record_id': int(time.time()),
                'operator_name': '张三'
            },
            'operator_id': 'OP001',
            'priority': 'high',
            'related_order': 'ORD2026050801',
            'tags': ['编织', '一班']
        }
        r = requests.post(f'{BASE_URL}/api/internal/publish', json=payload, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        data = r.json()
        assert data.get('success')
        task_id = data['task_id']
        log_step(f'任务已发布', 'OK',
                 f'任务ID: {task_id} | 订单: ORD2026050801 | 编织 100米')
        time.sleep(0.5)
    except Exception as e:
        log_step('发布任务失败', 'FAIL', str(e))
        return

    # ── 第5步: 查看发布后的容器池状态 ──
    print_separator('第5步：确认任务已进入容器池')
    try:
        r = requests.get(f'{BASE_URL}', headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        data = r.json()
        pool = data.get('data', {}).get('pool_status', {})
        log_step('容器池状态', 'OK', json.dumps(pool, ensure_ascii=False))
    except Exception as e:
        log_step('获取状态失败', 'FAIL', str(e))

    # ── 第6步: 派发任务(工人扫码/登录后自动获取) ──
    print_separator('第6步：模拟工人扫码/派发任务')
    try:
        r = requests.post(f'{BASE_URL}/api/tasks/dispatch', json={
            'task_types': ['report', 'quality', 'material', 'approval'],
            'max_count': 10
        }, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        data = r.json()
        assert data.get('success')
        assigned = data.get('data', {}).get('tasks', [])
        log_step(f'任务已分配', 'OK',
                 f'本次分配 {len(assigned)} 个任务')
        for t in assigned:
            log_step(f'  任务 {t["id"]}', 'ASSIGNED',
                     f'{t["title"]} | 优先级: {t["priority"]} | 状态: {t["status"]}')
    except Exception as e:
        log_step('任务派发失败', 'FAIL', str(e))

    # ── 第7步: 查看待处理任务列表 ──
    print_separator('第7步：查看我的待处理任务')
    try:
        r = requests.get(f'{BASE_URL}/api/tasks?types=report,quality', headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        data = r.json()
        tasks = data.get('data', {}).get('tasks', [])
        log_step(f'待处理任务', 'OK', f'共 {len(tasks)} 个任务')
        for t in tasks:
            log_step(f'  任务 {t["id"]}', 'PENDING',
                     f'{t["title"]} | 订单: {t.get("related_order", "N/A")}')
    except Exception as e:
        log_step('获取任务列表失败', 'FAIL', str(e))

    # ── 第8步: 开始执行任务(扫码确认) ──
    print_separator('第8步：模拟扫码确认 → 开始执行')
    try:
        r = requests.post(f'{BASE_URL}/api/tasks/{task_id}/start', headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        data = r.json()
        assert data.get('code') == 0
        task = data.get('data', {})
        log_step('任务已开始执行', 'OK',
                 f'状态: {task["status"]} | 开始时间: {task.get("started_at", "N/A")}')
    except Exception as e:
        log_step('开始任务失败', 'FAIL', str(e))

    # ── 第9步: 完成任务(报工) ──
    print_separator('第9步：模拟工人报工 → 完成任务')
    try:
        result_payload = {
            'completed_qty': 100,
            'defect_qty': 2,
            'status': 'completed',
            'quality': '合格',
            'remark': '编织工序完成，2米瑕疵已标记',
            'work_time_minutes': 45,
            'operator_name': '张三'
        }
        r = requests.post(f'{BASE_URL}/api/tasks/{task_id}/complete',
                          json=result_payload, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        data = r.json()
        assert data.get('success')
        log_step('报工成功', 'OK', json.dumps(data, ensure_ascii=False))
    except Exception as e:
        log_step('报工失败', 'FAIL', str(e))

    # ── 第10步: 最终验证 ──
    print_separator('第10步：验证全流程结果')
    try:
        # 查看容器池状态(用主管账号)
        r_mgr = requests.post(f'{BASE_URL}/api/auth/login',
                              json={'operator_id': 'MG001'}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        mgr_token = r_mgr.json()['data']['token']
        r = requests.get(f'{BASE_URL}/api/pool/status',
                         headers={'Authorization': f'Bearer {mgr_token}'}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        data = r.json()
        log_step('最终容器池状态', 'OK', json.dumps(data.get('data', {}), ensure_ascii=False))

        # 查看任务详情
        r = requests.get(f'{BASE_URL}/api/tasks/{task_id}', headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        data = r.json()
        if data.get('success'):
            task = data.get('data', {})
            log_step('任务最终详情', 'OK',
                     f'状态: {task.get("status")} | 完成时间: {task.get("completed_at", "N/A")}')
            log_step('完成结果', 'OK',
                     json.dumps(task.get('result', {}), ensure_ascii=False))
    except Exception as e:
        log_step('验证失败', 'FAIL', str(e))

    # ── 汇总 ──
    print()
    print('=' * 60)
    print('  *** 全流程模拟完成！***')
    print('=' * 60)
    print('  流程路径:')
    print('    软件端 -> API -> 容器池 -> 微信推送 -> 工人扫码 -> 报工完成')
    print()
    print('  数据流:')
    print(f'    工单 ORD2026050801 | 编织 100米')
    print(f'    操作员: 张三(OP001) | 质量: 合格')
    print(f'    耗时: 45分钟 | 瑕疵: 2米')
    print()
    print('  API调用时序:')
    print('    1. POST /api/auth/login             -> 获取Token')
    print('    2. POST /api/internal/publish       -> 发布任务')
    print('    3. POST /api/tasks/dispatch         -> 派发任务给工人')
    print('    4. POST /api/tasks/{id}/start       -> 扫码确认开始')
    print('    5. POST /api/tasks/{id}/complete    -> 提交报工结果')
    print('=' * 60)

    # 关闭日志文件
    if hasattr(log_step, 'log_file'):
        log_step.log_file.close()


if __name__ == '__main__':
    main()
