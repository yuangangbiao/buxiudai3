"""启动 5010 (inventory_api_server.py / 库存管理)"""
import os
import sys
import shutil

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
os.environ['INVENTORY_API_PORT'] = '5010'
os.environ['WAITRESS_THREADS'] = '4'

# 复制 core/db.py 到 mobile_api_ai/core
src_db = r'D:\yuan\不锈钢网带跟单3.0\core\db.py'
dst_db = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\core\db.py'
if os.path.exists(src_db) and not os.path.exists(dst_db):
    shutil.copy(src_db, dst_db)

proj = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
sys.path.insert(0, proj)
sys.path.insert(0, r'D:\yuan\不锈钢网带跟单3.0')

print('=== 启动 5010 (inventory_api_server) ===', flush=True)

# 改用 Waitress（之前已对 5008 做过）
src = open(os.path.join(proj, 'inventory_api_server.py'), encoding='utf-8').read()
# 替换 app.run 改用 Waitress
new_run = '''if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('INVENTORY_API_PORT', '5010'))
    logger.info(f'库存系统 v2.3 启动: http://{host}:{port} (Web + API)')
    for r in app.url_map.iter_rules():
        logger.debug(f'  {r.rule} -> {r.endpoint}')
    # [K27 同款修复 2026-06-14] Waitress 替代 Flask dev server
    try:
        from waitress import serve
        threads = int(os.getenv('WAITRESS_THREADS', 4))
        serve(app, host=host, port=port, threads=threads, ident='yuan-5010')
        logger.info(f'[5010 启动] Waitress listening on {host}:{port} threads={threads}')
    except ImportError:
        logger.warning('[5010 启动] Waitress 未安装，降级到 Flask dev server（不推荐）')
        app.run(host=host, port=port, debug=False)'''
src = src.replace(
    "if __name__ == '__main__':\n    host = os.getenv('FLASK_HOST', '0.0.0.0')\n    port = int(os.getenv('INVENTORY_API_PORT', '5010'))\n    logger.info(f'库存系统 v2.3 启动: http://{host}:{port} (Web + API)')\n    for r in app.url_map.iter_rules():\n        logger.debug(f'  {r.rule} -> {r.endpoint}')\n    app.run(host=host, port=port, debug=False)",
    new_run
)
exec(compile(src, 'inventory_api_server.py', 'exec'), {'__file__': os.path.join(proj, 'inventory_api_server.py'), '__name__': '__main__'})
