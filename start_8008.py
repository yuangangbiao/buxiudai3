"""启动 8008 - 用 mobile_api_ai/core"""
import os
import sys

# [T15 修复 2026-06-14] 先加载 .env，再 setdefault（不覆盖已设 env）
from pathlib import Path
env_path = Path(r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\.env')
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

# [T15 兜底] .env 未设时使用默认值（开发用）
os.environ.setdefault('API_KEY', 'test-api-key-12345')
os.environ.setdefault('MIRROR_SHARED_SECRET', 'test-mirror-secret-67890')
os.environ.setdefault('CONTAINER_MYSQL_PASSWORD', '88888888')
os.environ.setdefault('MYSQL_PASSWORD', '88888888')
os.environ.setdefault('ES_HOST', '')
os.environ.setdefault('FLASK_HOST', '127.0.0.1')
os.environ.setdefault('PORT', '8008')

# 关键：mobile_api_ai 在前，项目根在后（避免 core 冲突）
# [P1-1 修复 2026-06-24] 原来缺少项目根，导致无法 import core.config
sys.path.insert(0, r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
sys.path.insert(0, r'D:\yuan\不锈钢网带跟单3.0')

# 检查 core.config 和 core.db
import core.config
import core.db
print(f'core.config: {core.config.__file__}', flush=True)
print(f'core.db: {core.db.__file__}', flush=True)
print(f'has now: {hasattr(core.config, "now")}', flush=True)
print(f'has get_process_code: {hasattr(core.config, "get_process_code")}', flush=True)
print(f'has MYSQL_CFG: {hasattr(core.config, "MYSQL_CFG")}', flush=True)
print(f'has CONTAINER_MYSQL_CFG: {hasattr(core.config, "CONTAINER_MYSQL_CFG")}', flush=True)

print('=== 启动 8008 ===', flush=True)

src_path = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\sync_bridge_server.py'
with open(src_path, encoding='utf-8') as f:
    src = f.read()
src = src.replace("if __name__ == '__main__':", "if True:")
exec(compile(src, src_path, 'exec'), {'__name__': '__main__', '__file__': src_path})
