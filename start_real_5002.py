"""启动完整 5002 - 不预启动 worker [T15 2026-06-14] 加载 .env"""
import os
import sys

# [T15 修复 2026-06-14] 先加载 .env，再 setdefault（不覆盖已设 env）
# 之前：硬编码 5 个 env 变量 → 改 .env 无效
# 现在：从 .env 读取所有配置，env 变量已设时优先用 env
from pathlib import Path
env_path = Path(r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\.env')
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

# [T15 兜底] .env 未设时使用内置默认值（开发用，生产应在 .env 设）
os.environ.setdefault('API_KEY', 'test-api-key-12345')
os.environ.setdefault('MIRROR_SHARED_SECRET', 'test-mirror-secret-67890')
os.environ.setdefault('API_SECRET_KEY', 'test-api-secret')
os.environ.setdefault('ES_HOST', '')  # 禁用 ES
os.environ.setdefault('FLASK_HOST', '127.0.0.1')

# 修改 sys.path
sys.path.insert(0, r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai')

print('=== 启动 5002 ===', flush=True)

# 直接 exec（不预启动 worker）
src_path = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\container_center_api.py'
with open(src_path, encoding='utf-8') as f:
    src = f.read()
src = src.replace("if __name__ == '__main__':", "if True:")
exec(compile(src, src_path, 'exec'), {'__name__': '__main__', '__file__': src_path})
