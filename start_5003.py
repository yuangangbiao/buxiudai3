"""启动 5003 (wechat_server / dispatch_center)"""
import os
import sys

# 加载 .env
from pathlib import Path
env_path = Path(r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\.env')
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

# 关键：复制缺失的文件到 mobile_api_ai/
import shutil

# 1. 复制 core/db.py
src_db = r'D:\yuan\不锈钢网带跟单3.0\core\db.py'
dst_db = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\core\db.py'
if os.path.exists(src_db) and not os.path.exists(dst_db):
    shutil.copy(src_db, dst_db)
    print('复制 core/db.py', flush=True)

# 2. 复制缺失的 utils 文件（dispatch_center 需要 data_type_contract.py）
src_utils = r'D:\yuan\不锈钢网带跟单3.0\utils'
dst_utils = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\utils'
required_files = ['data_type_contract.py', 'validation', 'storage']
for item in required_files:
    src = os.path.join(src_utils, item)
    dst = os.path.join(dst_utils, item)
    if os.path.exists(src) and not os.path.exists(dst):
        if os.path.isdir(src):
            shutil.copytree(src, dst)
            print(f'复制 utils/{item}/', flush=True)
        else:
            shutil.copy(src, dst)
            print(f'复制 utils/{item}', flush=True)

print('=== 启动 5003 (wechat_server) ===', flush=True)
sys.stderr.write('[启动器] 即将启动 wechat_server\n')
sys.stderr.flush()

src_path = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_server.py'
with open(src_path, encoding='utf-8') as f:
    src = f.read()
# 强制改 port=5003
src = src.replace("default=5003, help='监听端口')", "default=5003, help='监听端口')")
# 修改 __main__ 块的 app.run 强制传 --port 5003
# 用 runpy 方式更安全
import runpy
sys.argv = ['wechat_server.py', '--port', '5003', '--host', '127.0.0.1']
runpy.run_path(src_path, run_name='__main__')
