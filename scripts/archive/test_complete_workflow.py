# -*- coding: utf-8 -*-
"""
测试完整流程：扫码 -> 获取任务 -> 确认 -> 报工
"""
import requests
import json
import time

BASE_URL = 'http://localhost:5003'

def test_full_workflow():
    print('=' * 60)
    print('生产任务助手 - 完整流程测试')
    print('=' * 60)

    # 1. 健康检查
    print('\n[1] 健康检查...')
    try:
        resp = requests.get(f'{BASE_URL}/api/health', timeout=5)
        print(f'状态码: {resp.status_code}')
        print(f'响应: {resp.json()}')
    except Exception as e:
        print(f'错误: {e}')
        return

    # 2. 获取所有任务
    print('\n[2] 获取所有任务...')
    try:
        resp = requests.get(f'{BASE_URL}/api/wechat/pool/tasks/all', timeout=5)
        print(f'状态码: {resp.status_code}')
        data = resp.json()
        print(f'任务总数: {len(data.get("tasks", []))}')
        for task in data.get('tasks', [])[:3]:  # 只显示前3个
            print(f'  - {task.get("title")} | {task.get("status")} | {task.get("id")}')
    except Exception as e:
        print(f'错误: {e}')

    # 3. 扫码获取任务（使用测试工单）
    print('\n[3] 扫码获取任务...')
    test_work_orders = ['WO202604001', 'WO202604002']
    for wo in test_work_orders:
        try:
            resp = requests.post(
                f'{BASE_URL}/api/scan/task',
                json={'work_order_no': wo},
                timeout=5
            )
            print(f'工单 {wo}:')
            print(f'  状态码: {resp.status_code}')
            if resp.status_code == 200:
                result = resp.json()
                print(f'  结果: {result.get("message", "")}')
                if result.get('task'):
                    print(f'  任务ID: {result["task"].get("id")}')
                    print(f'  标题: {result["task"].get("title")}')
        except Exception as e:
            print(f'  错误: {e}')

    # 4. 测试确认任务（如果有任务的话）
    print('\n[4] 测试确认任务...')
    try:
        resp = requests.get(f'{BASE_URL}/api/wechat/pool/tasks/all', timeout=5)
        tasks = resp.json().get('tasks', [])
        if tasks:
            # 尝试确认第一个待分配的任务
            for task in tasks:
                if task.get('status') == 'pending':
                    task_id = task.get('id')
                    print(f'尝试确认任务: {task_id}')
                    resp = requests.post(
                        f'{BASE_URL}/api/tasks/{task_id}/acknowledge',
                        json={'operator_id': 'OP001', 'operator_name': '测试操作员'},
                        timeout=5
                    )
                    print(f'  状态码: {resp.status_code}')
                    print(f'  响应: {resp.json()}')
                    break
        else:
            print('没有待确认的任务')
    except Exception as e:
        print(f'错误: {e}')

    # 5. 测试报工（如果有已确认任务）
    print('\n[5] 测试报工...')
    try:
        resp = requests.get(f'{BASE_URL}/api/wechat/pool/tasks/all', timeout=5)
        tasks = resp.json().get('tasks', [])
        if tasks:
            for task in tasks:
                if task.get('status') in ['pending', 'distributed', 'acknowledged']:
                    task_id = task.get('id')
                    print(f'尝试报工任务: {task_id}')
                    resp = requests.post(
                        f'{BASE_URL}/api/wechat/pool/report',
                        json={
                            'task_id': task_id,
                            'completed_qty': 50,
                            'qualified_qty': 48,
                            'worker': '测试工人',
                            'remark': '测试报工'
                        },
                        timeout=5
                    )
                    print(f'  状态码: {resp.status_code}')
                    print(f'  响应: {resp.json()}')
                    break
        else:
            print('没有可报工的任务')
    except Exception as e:
        print(f'错误: {e}')

    # 6. 最终状态检查
    print('\n[6] 最终状态检查...')
    try:
        resp = requests.get(f'{BASE_URL}/api/wechat/pool/tasks/all', timeout=5)
        data = resp.json()
        print(f'任务总数: {len(data.get("tasks", []))}')
        status_counts = {}
        for task in data.get('tasks', []):
            status = task.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        print('状态分布:')
        for status, count in status_counts.items():
            print(f'  {status}: {count}')
    except Exception as e:
        print(f'错误: {e}')

    print('\n' + '=' * 60)
    print('测试完成！')
    print('=' * 60)

if __name__ == '__main__':
    test_full_workflow()
