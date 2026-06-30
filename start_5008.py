"""启动 5008 (app.py / start_local.py)"""
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
os.environ['PORT'] = '5008'
# [K42 修复 2026-06-14] 压测发现 5008 队列满/连接限制触顶
# 之前：threads=4, max connections=100（默认）→ 队列深度 94+ 时拒绝新连接
# 现在：threads=8, channel_timeout=60, max connections 由 accept_threshold 决定
os.environ['WAITRESS_THREADS'] = '8'
# 5008 默认是 mobile_api 业务端口
# [T15 修复 2026-06-14] 硬编码 88888888 改为 setdefault，.env 优先
os.environ.setdefault('API_KEY', 'test-api-key-12345')
os.environ.setdefault('MIRROR_SHARED_SECRET', 'test-mirror-secret-67890')
os.environ.setdefault('CONTAINER_MYSQL_PASSWORD', '88888888')
os.environ.setdefault('MYSQL_PASSWORD', '88888888')

# 复制 core/db.py 到 mobile_api_ai/core
# [P1-2 说明 2026-06-24] 这是变通方案，因为 mobile_api_ai/core/ 已有 db.py
# （与项目根 core/ 不同）。理想方案：统一 PYTHONPATH，让服务直接用项目根 core/
import shutil
src_db = r'D:\yuan\不锈钢网带跟单3.0\core\db.py'
dst_db = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\core\db.py'
if os.path.exists(src_db) and not os.path.exists(dst_db):
    shutil.copy(src_db, dst_db)

proj = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
sys.path.insert(0, proj)
sys.path.insert(0, r'D:\yuan\不锈钢网带跟单3.0')
os.chdir(proj)  # 修复：Flask root_path 基于工作目录，必须切换到 mobile_api_ai
print(f'[start_5008] os.chdir({proj}), cwd={os.getcwd()}', flush=True)

# [T2b 修复 2026-06-14] 解决 core 包冲突
# mobile_api_ai/core 和项目根 core 同时存在
# app.py 启动时会把项目根加 sys.path[0] 抢走 core 包 → 路由 from core.db_compat 失败
# 修复：把 mobile_api_ai/core/db_compat 注入到项目根 core 包中（符号链接级别）
import shutil as _sh
_dst = r'D:\yuan\不锈钢网带跟单3.0\core\db_compat.py'
if not __import__('os').path.exists(_dst):
    _src = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\core\db_compat.py'
    if __import__('os').path.exists(_src):
        _sh.copy(_src, _dst)
        print('[T2b] 已复制 core/db_compat.py 到项目根 core/')

print('=== 启动 5008 (app.py) ===', flush=True)

# 用 start_local.py 方式（exec 避免重复 import）
app_path = os.path.join(proj, 'app.py')
# 修复：Flask 通过 __main__.__file__ 确定 root_path，必须设置
sys.modules['__main__'].__file__ = app_path
code = compile(open(app_path, encoding='utf-8').read(), app_path, 'exec')
exec(code, {'__file__': app_path, '__name__': '__main__'})
