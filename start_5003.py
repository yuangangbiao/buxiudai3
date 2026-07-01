"""启动 5003 (调度中心 standalone_dispatch_server)"""
import os
import sys
from pathlib import Path

env_path = Path(r'D:\yuan\不锈钢网带跟单3.0\.env')
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

os.environ['ES_HOST'] = ''
os.environ['FLASK_HOST'] = '127.0.0.1'
os.environ['PORT'] = '5003'

sys.path.insert(0, r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
sys.path.insert(0, r'D:\yuan\不锈钢网带跟单3.0')

import runpy
src_path = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\standalone_dispatch_server.py'
sys.argv = ['standalone_dispatch_server.py']
runpy.run_path(src_path, run_name='__main__')
