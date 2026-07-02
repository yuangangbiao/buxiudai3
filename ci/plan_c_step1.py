# -*- coding: utf-8 -*-
"""
[C 方案 C.1] 清理 scripts/ 一级目录含 data_packages 引用的脚本
保留：scripts/verify_*.py 和 scripts/check_*.py（CI 必需）
"""
import os
import shutil
from datetime import datetime

PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts')
ARCHIVE_DIR = os.path.join(PROJECT_ROOT, 'archive', f'scripts_c1_{datetime.now().strftime("%Y%m%d")}')


# 30+ 含 data_packages 引用的脚本清单
TARGET_FILES = [
    '__pre_tests__/test_backfill_data_packages_flow_type.py',
    '_check_schema.py',
    '_debug_db.py',
    '_debug_db2.py',
    '_debug_schema.py',
    'audit_today.py',
    'backfill_data_packages.py',
    'backfill_data_packages_flow_type.py',
    'check_cc_setup.py',
    'cleanup_quality_task.py',
    'describe_all.py',
    'e2e_publish_test.py',
    'fill_data_packages_process_code.py',
    'fix_4orders_anomaly.py',
    'inspect_full.py',
    'migrations/migrate_add_task_fields_0620.py',
    'migrations/migrate_backfill_completed_qty_0620.py',
    'migrations/migrate_data_type_to_v1.py',
    'p4_scan_legacy.py',
    'patch_related_order.py',
    'q3_db_inspect.py',
    'q3_describe.py',
    'sync_task_published.py',
    't4.3.1_create_data_packages.py',
    'verify_data_packages.py',
]


def main():
    print('===== C.1 清理 scripts/ 一级目录 30+ 脚本 =====\n')
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    moved = []
    for rel in TARGET_FILES:
        src = os.path.join(SCRIPTS_DIR, rel)
        if not os.path.exists(src):
            print(f'  ⚠️ 不存在: {rel}')
            continue

        # 保留迁移脚本中只读的不动（migration_*.py 中是 ALTER 历史）
        # 只 move 调试/查询/验证类脚本
        dst = os.path.join(ARCHIVE_DIR, rel.replace('/', '__'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        moved.append(rel)
        print(f'  ✅ {rel}')

    print(f'\n===== 总结 =====')
    print(f'移动文件: {len(moved)} 个')
    print(f'归档到: {ARCHIVE_DIR}')

    # 验证
    print(f'\n===== 验证 scripts/ 剩余 data_packages 引用 =====')
    import subprocess
    r = subprocess.run(
        f'grep -rn "data_packages" "{SCRIPTS_DIR}" --include=*.py',
        capture_output=True, text=True, timeout=20, shell=True
    )
    lines = [l for l in r.stdout.split('\n') if l.strip() and 'data_packages_deprecated' not in l]
    if not lines:
        print('  ✅ scripts/ 核心代码无 data_packages 引用')
    else:
        print(f'  ⚠️ 仍有 {len(lines)} 处:')
        for l in lines[:10]:
            print(f'    {l}')


if __name__ == '__main__':
    main()
