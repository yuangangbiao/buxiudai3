import os
from dotenv import load_dotenv
load_dotenv('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/.env')
import pymysql

c = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', 'localhost'),
    port=int(os.environ.get('MYSQL_PORT', 3306)),
    user=os.environ.get('MYSQL_USER', 'root'),
    password=os.environ.get('MYSQL_PASSWORD', ''),
    database='steel_belt',
    charset='utf8mb4'
)
cc = c.cursor()
cc.execute('SHOW INDEX FROM production_orders WHERE Column_name="work_order_no"')
if cc.fetchone():
    print('索引已存在，跳过')
else:
    cc.execute('ALTER TABLE production_orders ADD INDEX idx_wo_no (work_order_no)')
    c.commit()
    print('索引添加成功')

cc.execute('DESC production_orders')
cols = {r[0]: r[1] for r in cc.fetchall()}
print('production_orders 表字段:', list(cols.keys()))
cc.close()
c.close()
