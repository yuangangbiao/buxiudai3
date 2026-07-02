# -*- coding: utf-8 -*-
"""
[CI Fix] PROJECT_ROOT 改为读 GITHUB_WORKSPACE / cwd
"""
import os, re

FILES = [
    'ci/check_stage_1.py',
    'ci/check_stage_2.py',
    'ci/check_stage_3.py',
    'ci/check_stage_4.py',
    'ci/test_v3_6_full.py',
    'ci/test_t1_routing.py',
    'ci/test_t2b_auth.py',
    'ci/plan_c_step3.py',
    'ci/plan_c_replace_data_packages.py',
    'ci/fix_ci_db_host.py',
    'ci/find_data_packages_refs.py',
    'ci/find_real_sql.py',
    'ci/plan_c_step1.py',
    'ci/plan_c_step2.py',
    'ci/plan_c_step5.py',
]

for rel in FILES:
    path = os.path.join(r'd:\yuan\不锈钢网带跟单3.0', rel)
    if not os.path.exists(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content
    # 替换硬编码 Windows 路径
    # 真实字符串：PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
    # Python raw string 中 \d 不会被转义，但我们需要处理
    old_str = "PROJECT_ROOT = r'd:\\yuan\\不锈钢网带跟单3.0'"
    new_str = "PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())"
    content = content.replace(old_str, new_str)
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'✅ {rel}')
print('完成')
