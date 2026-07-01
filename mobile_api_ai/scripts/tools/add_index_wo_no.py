import os
from dotenv import load_dotenv
load_dotenv('d:/yuan/涓嶉攬閽㈢綉甯﹁窡鍗?.0/mobile_api_ai/.env')
import pymysql

c = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', ''),
    port=int(os.environ.get('MYSQL_PORT', 3306)),
    user=os.environ.get('MYSQL_USER', 'root'),
    password=os.environ.get('MYSQL_PASSWORD', ''),
    database='steel_belt',
    charset='utf8mb4'
)
cc = c.cursor()
cc.execute('SHOW INDEX FROM production_orders WHERE Column_name="order_no"')
if cc.fetchone():
    print('绱㈠紩宸插瓨鍦紝璺宠繃')
else:
    cc.execute('ALTER TABLE production_orders ADD INDEX idx_wo_no (order_no)')
    c.commit()
    print('绱㈠紩娣诲姞鎴愬姛')

cc.execute('DESC production_orders')
cols = {r[0]: r[1] for r in cc.fetchall()}
print('production_orders 琛ㄥ瓧娈?', list(cols.keys()))
cc.close()
c.close()
