"""手动触发 ETL 一次补同步"""
import sys, os
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
os.chdir(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')

# 加载 .env
from dotenv import load_dotenv
load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\.env')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

from etl_local_mirror import manual_sync_once, start_etl_worker

print("=" * 60)
print("【A】手动同步一次")
print("=" * 60)
try:
    n = manual_sync_once()
    print(f"手动同步完成: {n} 行")
except Exception as e:
    print(f"手动同步失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("【B】启动 ETL 后台 worker")
print("=" * 60)
try:
    t = start_etl_worker(interval_sec=60)
    print(f"ETL worker 已启动: {t.name} alive={t.is_alive()}")
except Exception as e:
    print(f"ETL worker 启动失败: {e}")
    import traceback
    traceback.print_exc()
