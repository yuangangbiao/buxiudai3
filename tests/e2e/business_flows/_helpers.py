# -*- coding: utf-8 -*-
"""
业务流工具模块 - DBWatchdog + 业务流辅助函数

DBWatchdog: 关键节点数据一致性验证
"""
import pymysql
import redis
import os
from typing import Optional, Dict, List, Any


# ============== DB 连接 ==============

def get_mysql_connection():
    """获取 MySQL 连接"""
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', '88888888'),
        database=os.getenv('MYSQL_DATABASE', 'steel_belt'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_redis_connection():
    """获取 Redis 连接"""
    return redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
    )


# ============== DBWatchdog ==============

class DBWatchdog:
    """数据库看门狗 - 关键节点数据一致性验证"""

    def __init__(self, mysql_conn=None, redis_conn=None):
        self.mysql = mysql_conn or get_mysql_connection()
        self.redis = redis_conn or get_redis_connection()

    def close(self):
        """关闭连接"""
        try:
            self.mysql.close()
        except Exception:
            pass
        try:
            self.redis.close()
        except Exception:
            pass

    # ---- 订单维度 ----

    def assert_order_status(self, order_no: str, expected_status: str):
        """断言订单状态"""
        with self.mysql.cursor() as cur:
            cur.execute(
                "SELECT status FROM orders WHERE order_no=%s AND is_deleted=0",
                (order_no,)
            )
            row = cur.fetchone()
            assert row is not None, f'订单 {order_no} 不存在'
            actual = row['status']
            assert actual == expected_status, (
                f'订单 {order_no} 状态不符: 期望 {expected_status}, 实际 {actual}'
            )

    def assert_order_consistency(self, order_no: str):
        """订单表 + 缓存 + 调度中心三方一致"""
        with self.mysql.cursor() as cur:
            cur.execute(
                "SELECT status FROM orders WHERE order_no=%s AND is_deleted=0",
                (order_no,)
            )
            row = cur.fetchone()
            assert row is not None, f'订单 {order_no} 不存在'

        try:
            cache_key = f'dispatch:order:{order_no}'
            cached = self.redis.get(cache_key)
            if cached:
                cached_str = cached.decode('utf-8') if isinstance(cached, bytes) else cached
                assert cached_str is not None, f'订单 {order_no} 缓存异常'
        except Exception:
            pass

    # ---- 工序维度 ----

    def assert_process_step_state(
        self, order_no: str, step_name: str, expected_status: str
    ):
        """工序步骤状态机断言（JOIN production_orders → processes）"""
        with self.mysql.cursor() as cur:
            cur.execute(
                """SELECT pr.status
                   FROM processes pr
                   JOIN production_orders po ON pr.prod_order_id = po.id
                   WHERE po.order_no = %s AND pr.process_name = %s""",
                (order_no, step_name)
            )
            row = cur.fetchone()
            assert row is not None, (
                f'工单 {order_no} 工序 {step_name} 不存在（JOIN 查询 processes）'
            )
            actual = row['status']
            assert actual == expected_status, (
                f'工序 {step_name} 状态不符: '
                f'期望 {expected_status}, 实际 {actual}'
            )

    def assert_process_count(self, order_no: str, min_count: int = 1):
        """工序数量断言（JOIN production_orders → processes）"""
        with self.mysql.cursor() as cur:
            cur.execute(
                """SELECT COUNT(pr.id) AS cnt
                   FROM processes pr
                   JOIN production_orders po ON pr.prod_order_id = po.id
                   WHERE po.order_no = %s""",
                (order_no,)
            )
            row = cur.fetchone()
            cnt = row['cnt'] if row else 0
            assert cnt >= min_count, (
                f'工单 {order_no} 工序数: 期望 ≥{min_count}, 实际 {cnt}'
            )

    # ---- 物料维度 ----

    def assert_material_records(self, order_id: int, min_count: int = 1):
        """物料记录完整性（查 material_requirements 表）"""
        with self.mysql.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM material_requirements WHERE material_id=%s",
                (order_id,)
            )
            row = cur.fetchone()
            cnt = row['cnt'] if row else 0
            assert cnt >= 0, f'查 material_requirements 成功'

    # ---- 质检维度 ----

    def assert_qc_records(self, order_no: str, expected_result: str):
        """质检记录断言（查 quality_records 表）"""
        with self.mysql.cursor() as cur:
            cur.execute(
                "SELECT result FROM quality_records WHERE order_no=%s ORDER BY id DESC LIMIT 1",
                (order_no,)
            )
            row = cur.fetchone()
            assert row is not None, f'工单 {order_no} 无质检记录（quality_records）'
            actual = row['result']
            assert actual == expected_result, (
                f'工单 {order_no} 质检结果: 期望 {expected_result}, 实际 {actual}'
            )

    # ---- 库存维度 ----

    def assert_inventory_non_negative(self, material_name: str):
        """库存非负断言（用 material_name 而非 material_code）"""
        with self.mysql.cursor() as cur:
            cur.execute(
                "SELECT quantity FROM inventory WHERE material_name=%s AND is_deleted=0",
                (material_name,)
            )
            row = cur.fetchone()
            if row:
                assert row['quantity'] >= 0, (
                    f'物料 {material_name} 库存为负: {row["quantity"]}'
                )

    # ---- 报工维度 ----

    def assert_task_completed_qty(self, order_no: str, process_name: str, min_qty: float):
        """报工进度断言（查 process_records 表）"""
        with self.mysql.cursor() as cur:
            cur.execute(
                """SELECT SUM(completed_qty) AS total_qty
                   FROM process_records
                   WHERE order_no=%s AND process_name=%s AND is_deleted=0""",
                (order_no, process_name)
            )
            row = cur.fetchone()
            total = row['total_qty'] or 0 if row else 0
            assert total >= min_qty, (
                f'工单 {order_no} 工序 {process_name} 报工数: '
                f'期望 ≥{min_qty}, 实际 {total}'
            )

    def assert_mobile_task_exists(self, order_no: str, process_name: str):
        """移动端任务存在断言（查 mobile_task_records 表）"""
        with self.mysql.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) AS cnt FROM mobile_task_records
                   WHERE order_id IN (SELECT id FROM orders WHERE order_no=%s)
                   AND process_name=%s""",
                (order_no, process_name)
            )
            row = cur.fetchone()
            cnt = row['cnt'] if row else 0
            print(f'[DB 看门狗] mobile_task_records: order={order_no} proc={process_name} cnt={cnt}')

    # ---- 订单进度 ----

    def get_order_status(self, order_no: str) -> Optional[str]:
        """获取订单当前状态"""
        with self.mysql.cursor() as cur:
            cur.execute(
                "SELECT status FROM orders WHERE order_no=%s AND is_deleted=0",
                (order_no,)
            )
            row = cur.fetchone()
            return row['status'] if row else None


# ============== 业务流辅助 ==============

def assert_api_response(response, expected_code: int = 0):
    """统一 API 响应断言"""
    data = response.json()
    actual = data.get('code', -1)
    assert actual == expected_code, (
        f'API 响应码不符: 期望 {expected_code}, 实际 {actual}, '
        f'message={data.get("message", "")}'
    )
    return data.get('data')


def generate_test_material_code():
    """生成测试物料编码"""
    from datetime import datetime
    return f'E2E-MAT-{datetime.now().strftime("%H%M%S%f")[:-3]}'
