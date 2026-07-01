"""批量修复 scripts/tools/ 中指向旧 D:\yuan\backend\ 的路径"""
import os
import re

PROJECT_DIR = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
NEW_CS_PATH = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\chengsheng.db'
NEW_WC_PATH = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'

files_to_fix = [
    # scripts/tools/ 目录
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_schema.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_dispatch_data_v6.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'test_submit_290001.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_order_290001.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_all_dbs.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_cs_db.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_order_steps.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_wno.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'sync_container_to_cs.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'cleanup_sync.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'verify_sync.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'test_db.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_op2.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_op.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_orders.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'test_legacy_api.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_cs_tables.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_chengsheng2.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_chengsheng.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'tools', 'check_root_db.py'),
    # 其他目录
    os.path.join(PROJECT_DIR, 'temp_query.py'),
    os.path.join(PROJECT_DIR, '_temp_check_cs.py'),
    os.path.join(PROJECT_DIR, 'scripts', 'add_customer_group_field.py'),
]

replaced_count = 0
error_files = []

for fp in files_to_fix:
    if not os.path.exists(fp):
        error_files.append((fp, '文件不存在'))
        continue
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
        original = content

        # 替换 1: r'D:\yuan\backend\data\chengsheng.db' → 新路径
        content = content.replace(
            r"r'D:\yuan\backend\data\chengsheng.db'",
            repr(NEW_CS_PATH)
        )
        # 替换 2: r"D:\yuan\backend\data\chengsheng.db"
        content = content.replace(
            'r"D:\\yuan\\backend\\data\\chengsheng.db"',
            repr(NEW_CS_PATH)
        )
        # 替换 3: 'D:\\yuan\\backend\\data\\chengsheng.db'
        content = content.replace(
            "'D:\\yuan\\backend\\data\\chengsheng.db'",
            repr(NEW_CS_PATH)
        )

        # 替换 4: os.path.join(..., '..', '..', 'backend', 'data', 'chengsheng.db')
        # 替换为 os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chengsheng.db')
        if 'backend' in content and 'chengsheng.db' in content:
            # 匹配 os.path.join 中包含 backend 的模式
            content = re.sub(
                r"""os\.path\.join\([^)]*backend[^)]*chengsheng\.db[^)]*\)""",
                f"os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chengsheng.db')",
                content
            )

        # 替换 5: r'D:\yuan\mobile_api_ai\wechat_container.db' → 新路径
        content = content.replace(
            r"r'D:\yuan\mobile_api_ai\wechat_container.db'",
            repr(NEW_WC_PATH)
        )

        # 替换 6: os.getenv('CHENGSHENG_DB_PATH', r'D:\yuan\backend\data\chengsheng.db')
        # 默认值改为新路径
        content = content.replace(
            f'os.getenv(\'CHENGSHENG_DB_PATH\', {repr(NEW_CS_PATH)})',
            f'os.getenv(\'CHENGSHENG_DB_PATH\', {repr(NEW_CS_PATH)})'
        )

        if content != original:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(content)
            replaced_count += 1
            print(f'  [OK] 已修复: {os.path.basename(fp)}')
        else:
            print(f'  [-] 无需修改: {os.path.basename(fp)}')
    except Exception as e:
        error_files.append((fp, str(e)))
        print(f'  [ERR] 错误: {os.path.basename(fp)} -> {e}')

print(f'\n完成! 共修复 {replaced_count} 个文件')
if error_files:
    print(f'失败 {len(error_files)} 个文件:')
    for fp, err in error_files:
        print(f'  - {fp}: {err}')
