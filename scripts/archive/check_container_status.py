# -*- coding: utf-8 -*-
"""
[v3.7.7 迁移] 检查容器池状态

[v3.7.7 2026-06-25] 从 desktop_container_integration 迁移到 dispatch_center.publisher

使用方式:
    python scripts/archive/check_container_status.py

注意: 这是归档目录中的脚本，新功能请用 dispatch_center 模块
"""
import sys
import os

# 项目根加入 sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
_MOBILE_API_AI = os.path.join(_PROJECT_ROOT, 'mobile_api_ai')
if _MOBILE_API_AI not in sys.path:
    sys.path.insert(0, _MOBILE_API_AI)


def main():
    """检查容器池状态"""
    print('=' * 60)
    print('容器池状态检查 (v3.7.7 新版)')
    print('=' * 60)

    try:
        # [v3.7.7] 改用 dispatch_center.publisher
        from mobile_api_ai.dispatch_center.publisher import (
            get_publisher,
            get_all_tasks,
            get_task_count,
        )
    except ImportError as e:
        print(f'[ERROR] 无法导入 dispatch_center.publisher: {e}')
        print('请确认 mobile_api_ai/dispatch_center/publisher.py 存在')
        return

    # 检查 report publisher 是否可用
    integ = get_publisher('report')
    if not integ.is_available:
        print('[ERROR] 容器集成不可用（熔断器可能 OPEN）')
        cb_status = integ.get_circuit_breaker_status()
        print(f'熔断器状态: {cb_status["state"]}，失败次数: {cb_status["failures"]}')
        return

    # 查看所有任务
    tasks = get_all_tasks()
    print(f'\n总任务数: {len(tasks)}\n')

    for i, task in enumerate(tasks, 1):
        print(f'任务 {i}:')
        print(f'  ID: {task.get("id")}')
        print(f'  类型: {task.get("type")}')  # [v3.7.7] 字段名 type（原为 task_type）
        payload = task.get('payload', {})
        print(f'  订单: {payload.get("order_no", "N/A")}')
        print(f'  工序: {payload.get("process_name", "N/A")}')
        print(f'  数量: {payload.get("quantity", "N/A")} {payload.get("unit", "")}')
        print()

    # 显示统计信息
    print('=' * 60)
    print('任务统计:')
    count = get_task_count()
    print(f'  总数: {count.get("total", 0)}')
    for k, v in count.items():
        if k != 'total':
            print(f'  {k}: {v}')


if __name__ == '__main__':
    main()