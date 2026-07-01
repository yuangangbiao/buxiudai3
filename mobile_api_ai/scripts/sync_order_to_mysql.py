import os
import sys
import logging
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

_MAIN_SOFTWARE_ROOT = os.path.dirname(_PROJECT_ROOT)  # 当前项目根目录

from dotenv import load_dotenv
load_dotenv(os.path.join(_MAIN_SOFTWARE_ROOT, '.env'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

ORDER_NO = 'WO-202605004'

MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', ''),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4',
}

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    logger.error("pymysql 未安装，请执行: pip install pymysql")
    sys.exit(1)


def sync_order():
    conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=DictCursor)
    try:
        c = conn.cursor()

        c.execute("SELECT id, status FROM orders WHERE order_no = %s", (ORDER_NO,))
        existing_order = c.fetchone()

        if existing_order:
            order_id = existing_order['id']
            logger.info(f'orders 已存在, id={order_id}, status={existing_order["status"]}')
        else:
            c.execute("""
                INSERT INTO orders (order_no, customer_name, product_type, material, quantity, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                ORDER_NO,
                '调度中心',
                '不锈钢网带',
                '304不锈钢',
                50,
                '已排产',
            ))
            order_id = c.lastrowid
            conn.commit()
            logger.info(f'orders 已创建, id={order_id}, status=已排产')

        c.execute("SELECT id, status FROM production_orders WHERE order_no = %s", (ORDER_NO,))
        existing_po = c.fetchone()

        from datetime import timedelta
        plan_start = datetime.now().strftime('%Y-%m-%d')
        plan_end = (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')

        if existing_po:
            po_id = existing_po['id']
            logger.info(f'production_orders 已存在, id={po_id}, status={existing_po["status"]}')

            if existing_po['status'] == '待发布':
                c.execute("""
                    UPDATE production_orders
                    SET status=%s, plan_start=%s, plan_end=%s, updated_at=NOW()
                    WHERE id=%s
                """, ('待开始', plan_start, plan_end, po_id))
                conn.commit()
                logger.info(f'production_orders id={po_id} 已更新: 待发布 → 待开始, plan={plan_start}~{plan_end}')
        else:
            c.execute("""
                INSERT INTO production_orders (order_no, order_id, status, plan_start, plan_end, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                ORDER_NO,
                order_id,
                '待开始',
                plan_start,
                plan_end,
            ))
            po_id = c.lastrowid
            conn.commit()
            logger.info(f'production_orders 已创建, id={po_id}, status=待开始, plan={plan_start}~{plan_end}')

        c.execute("""
            SELECT o.order_no, o.status as order_status,
                   po.status as prod_status, po.plan_start, po.plan_end
            FROM orders o
            LEFT JOIN production_orders po ON po.order_id = o.id AND po.order_no = %s
            WHERE o.order_no = %s
        """, (ORDER_NO, ORDER_NO))
        result = c.fetchone()
        logger.info(f'同步完成: {dict(result) if result else "not found"}')

    except Exception as e:
        logger.exception(f'同步失败: {e}')
        conn.rollback()
    finally:
        conn.close()


if __name__ == '__main__':
    sync_order()
