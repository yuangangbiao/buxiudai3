import os, sys, glob

sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')

from core.config import DB_PATHS, SERVICE_URLS

db_path = DB_PATHS['wechat_container']
print('wechat_container DB path:', db_path)
print('exists:', os.path.exists(db_path))

dbs = glob.glob(r'd:\yuan\不锈钢网带跟单3.0\**\*.db', recursive=True)
print('All .db files found:', dbs)

url = SERVICE_URLS['container_center']
print('container_center URL:', url)
