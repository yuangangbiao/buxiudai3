# -*- coding: utf-8 -*-
"""
[C 方案 C.4] 批量替换核心文件中 data_packages SQL → process_sub_steps
"""
import os
import re
import subprocess

PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
MOBILE_API = os.path.join(PROJECT_ROOT, 'mobile_api_ai')

# 9 个核心文件
TARGET_FILES = [
    'container_center_api.py',
    'api/process.py',
    'api/process_v2.py',
    'api/quality_inspection.py',
    'sync_bridge.py',
    'wechat_work_bot_bp.py',
    'api/report_record_admin.py',
    'app.py',
]


# 注释掉"修复前" / "data_packages 兼容保护" 类的代码
def transform_sql(line):
    """智能替换单行 SQL"""
    # 跳过注释行（修复前/兼容性提示）
    stripped = line.strip()
    if '修复前' in stripped or '死代码' in stripped or '无读者' in stripped:
        return line, '注释（死代码）'

    # 跳过注释
    if stripped.startswith('#'):
        return line, '跳过'

    # 替换 FROM data_packages → FROM process_sub_steps
    new_line = re.sub(
        r'(?<![_\w.])data_packages(?![_\w])',
        'process_sub_steps',
        line
    )
    # 替换 (CONTAINER_CENTER, 'data_packages', ...) → (CONTAINER_CENTER, 'process_sub_steps', ...)
    new_line = re.sub(
        r"'container_center\.'data_packages'",
        "'container_center'.'process_sub_steps'",
        new_line
    )

    return new_line, '替换' if new_line != line else '不变'


def main():
    print('===== C.4 批量替换核心文件中 data_packages SQL =====\n')
    summary = []

    for rel in TARGET_FILES:
        path = os.path.join(MOBILE_API, rel)
        if not os.path.exists(path):
            print(f'⚠️ 不存在: {rel}')
            continue

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        new_lines = []
        stats = {'替换': 0, '注释': 0, '跳过': 0, '不变': 0}

        for line in lines:
            new_line, action = transform_sql(line)
            new_lines.append(new_line)
            if 'data_packages' in line and 'data_packages_deprecated' not in line:
                stats[action if action in stats else '不变'] += 1

        new_content = '\n'.join(new_lines)
        if new_content != content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'  ✅ {rel}: 替换={stats["替换"]}, 注释={stats["注释"]}')
        summary.append((rel, stats))

    # 重新跑 plan_c_step3 验证
    print(f'\n===== 重新验证 =====')
    r = subprocess.run(
        ['python', os.path.join(PROJECT_ROOT, 'ci', 'plan_c_step3.py')],
        capture_output=True, text=True, timeout=30
    )
    # 提取最后 50 行
    output = r.stdout
    print('\n'.join(output.split('\n')[-30:]))


if __name__ == '__main__':
    main()
