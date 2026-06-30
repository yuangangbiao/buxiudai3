"""[v3.7.8] 手动 e2e 检查脚本

不用 docker，不用启动 5003，今天就能跑。
验证 publisher.py 的运行时行为：数据到底存到哪？
"""
import sys
import os
import time
sys.path.insert(0, '.')


def section(title):
    print()
    print('=' * 60)
    print(f'  {title}')
    print('=' * 60)


def check(label, condition, detail=''):
    icon = '✅' if condition else '❌'
    print(f'  {icon} {label}')
    if detail:
        print(f'     {detail}')
    return condition


def main():
    print('#' * 60)
    print('# 手动 e2e 检查: publisher.py 运行时行为')
    print('# 目的: 验证报工数据到底存到哪')
    print('# 日期:', time.strftime('%Y-%m-%d %H:%M:%S'))
    print('#' * 60)

    failures = []

    # ----------------------------------------------------------------------
    section('Step 1: 验证 publisher.py 模块加载')
    try:
        from mobile_api_ai.dispatch_center.publisher import (
            get_publisher, get_all_tasks, get_task_count,
        )
        check('import 成功', True)
    except Exception as e:
        check('import 失败', False, str(e))
        return 1

    # ----------------------------------------------------------------------
    section('Step 2: 验证兼容 API（旧签名）')
    report = get_publisher('report')
    check('ReportPublisher 实例', report is not None)
    check('has publish_report_task', hasattr(report, 'publish_report_task'))
    check('has publish_material_task', hasattr(get_publisher('material'), 'publish_material_task'))
    check('has publish_quality_task', hasattr(get_publisher('quality'), 'publish_quality_task'))

    # ----------------------------------------------------------------------
    section('Step 3: 模拟 service 调用')

    # 模拟 manual_publish_service.py:179-191 的真实调用
    try:
        task_id = report.publish_report_task(
            order_no='WO-2026-MANUAL-001',
            process_name='拉丝',
            customer_name='客户A',
            product_type='304钢',
            quantity=100,
            unit='米',
            planned_qty=100,
            operator_id='OP001',
            operator_name='张三',
            priority='normal',
        )
        check('publish_report_task 调用成功', task_id is not None, f'returned: {task_id}')
    except AttributeError as e:
        check('publish_report_task 调用', False, f'AttributeError: {e}')
        failures.append('API 不匹配')
    except Exception as e:
        check('publish_report_task 调用', False, f'{type(e).__name__}: {e}')
        failures.append(f'调用异常: {e}')

    # ----------------------------------------------------------------------
    section('Step 4: 验证任务存储')
    all_tasks = get_all_tasks()
    check('get_all_tasks() 不崩溃', isinstance(all_tasks, list))
    check('至少有 1 条任务', len(all_tasks) >= 1, f'实际: {len(all_tasks)} 条')

    matching = [t for t in all_tasks if t.get('id') == 'WO-2026-MANUAL-001']
    check('任务 WO-2026-MANUAL-001 存在', len(matching) == 1)

    if matching:
        task = matching[0]
        check('任务 type 是 report', task.get('type') == 'report')
        check('payload 含 order_no', task.get('payload', {}).get('order_no') == 'WO-2026-MANUAL-001')
        check('payload 含 process_name', task.get('payload', {}).get('process_name') == '拉丝')

    # ----------------------------------------------------------------------
    section('Step 5: 验证数据流向（关键!）')
    print('  ⚠️ 当前 publisher.py 只写内存 dict')
    print('  验证方法：检查是否调用了外部依赖（HTTP / DB）')

    # 检查 publisher.py 模块有没有 import pymysql / requests / ContainerCenterClient
    import mobile_api_ai.dispatch_center.publisher as pub_module
    pub_source = open(pub_module.__file__, 'r', encoding='utf-8').read()

    has_pymysql = 'import pymysql' in pub_source
    has_requests = 'import requests' in pub_source
    has_center_client = 'ContainerCenterClient' in pub_source

    check('import pymysql', has_pymysql, '直连 MySQL' if has_pymysql else '❌ 没有')
    check('import requests', has_requests, 'HTTP 调用' if has_requests else '❌ 没有')
    check('ContainerCenterClient', has_center_client, '调容器中心' if has_center_client else '❌ 没有')

    if not any([has_pymysql, has_requests, has_center_client]):
        check('数据流向', False, '只写内存 dict，重启就丢')
        failures.append('数据流向缺失（只内存）')
    else:
        check('数据流向', True, '有外部依赖')

    # ----------------------------------------------------------------------
    section('Step 6: 总结')
    if failures:
        print(f'❌ {len(failures)} 项失败:')
        for f in failures:
            print(f'  - {f}')
        print()
        print('下一步：')
        print('  1. 实施 publisher.py 真实数据流（HTTP 或 DB）')
        print('  2. 重启服务前不要做任何生产操作')
        return 1
    else:
        print('✅ 所有检查通过')
        print()
        print('注意：本脚本只验证 API 和内存存储，')
        print('     真实数据流向需要 tests/integration/test_publisher_e2e.py 验证')
        return 0


if __name__ == '__main__':
    sys.exit(main())