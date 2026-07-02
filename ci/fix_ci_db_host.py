# -*- coding: utf-8 -*-
"""
[G.5] 修复 CI 脚本的 DB_HOST 写死问题
- 改为读环境变量
- 支持 127.0.0.1 (CI) 和 localhost (本地)
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
    'ci/check_data_packages_usage.py',
    'ci/drop_data_packages.py',
    'ci/plan_c_step1.py',
    'ci/plan_c_step2.py',
    'ci/plan_c_step3.py',
    'ci/plan_c_step5.py',
    'ci/plan_c_replace_data_packages.py',
    'ci/find_data_packages_refs.py',
    'ci/find_real_sql.py',
    'ci/final_verify.py',
    'ci/fix_v3_6_4fields.py',
    'ci/list_data_packages.py',
    'ci/run_stage_1_ddl.py',
    'ci/stage3_cleanup.py',
    'ci/clean_nul.py',
    'ci/clean_nul2.py',
    'ci/find_nul.py',
]

for rel in FILES:
    path = os.path.join(r'd:\yuan\不锈钢网带跟单3.0', rel)
    if not os.path.exists(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content
    # 把 'host': 'localhost' 改为 'host': os.getenv('DB_HOST', 'localhost')
    content = re.sub(
        r"'host':\s*'localhost'",
        "'host': os.getenv('DB_HOST', 'localhost')",
        content
    )
    # 单独行 'localhost' (e.g. in main())
    content = re.sub(
        r"^(\s*)DB_HOST\s*=\s*'localhost'",
        r"\1DB_HOST = os.getenv('DB_HOST', 'localhost')",
        content,
        flags=re.MULTILINE
    )
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'✅ {rel}')
print('完成')
