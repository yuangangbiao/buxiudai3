# -*- coding: utf-8 -*-
import os, sys
PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())
print('PROJECT_ROOT:', PROJECT_ROOT)
MOBILE_API = os.path.join(PROJECT_ROOT, 'mobile_api_ai')
print('MOBILE_API:', MOBILE_API)
SCRIPTS = os.path.join(PROJECT_ROOT, 'scripts')
print('SCRIPTS:', SCRIPTS)
print('MOBILE_API exists:', os.path.exists(MOBILE_API))
print('SCRIPTS exists:', os.path.exists(SCRIPTS))

# 跑 check_stage_1 单独看
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\ci')
os.chdir(r'd:\yuan\不锈钢网带跟单3.0')
import subprocess
r = subprocess.run(
    ['grep', '-rn', 'password.=.88888888', MOBILE_API, SCRIPTS, '--include=*.py'],
    capture_output=True, text=True, timeout=20
)
print('rc:', r.returncode)
print('stdout:', r.stdout[:500])
print('stderr:', r.stderr[:300])
