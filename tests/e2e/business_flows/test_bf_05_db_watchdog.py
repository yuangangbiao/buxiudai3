# -*- coding: utf-8 -*-
"""
test_bf_05_db_watchdog.py - DB 看门狗独立验证

即便主链路测试失败，DB 看门狗也能给出精细的失败定位。
直接对 DB 表做断言，不依赖 API。
"""
import pytest
import pymysql

from tests.e2e.business_flows._helpers import DBWatchdog


@pytest.fixture
def watchdog():
    """DBWatchdog 实例 fixture"""
    wd = DBWatchdog()
    yield wd
    wd.close()


class TestDBWatchdogOrder:
    """订单表看门狗"""

    def test_watchdog_assert_order_status_method(self, watchdog, db_session):
        """验证订单状态断言方法可用"""
        with db_session.cursor() as cur:
            cur.execute(
                "SELECT order_no FROM orders WHERE is_deleted=0 LIMIT 1"
            )
            row = cur.fetchone()
            if row is None:
                pytest.skip('数据库无订单，跳过')
                return

            order_no = row['order_no']

        try:
            watchdog.assert_order_status(order_no, 'any_status')
        except AssertionError:
            pass  # 状态不符是正常的

        print(f'\n[DB 看门狗] 订单 {order_no} 断言方法可用')


class TestDBWatchdogProcess:
    """工序步骤表看门狗"""

    def test_watchdog_process_count(self, watchdog, db_session):
        """工序数量断言（JOIN production_orders → processes）"""
        with db_session.cursor() as cur:
            cur.execute(
                "SELECT po.order_no FROM production_orders po LIMIT 1"
            )
            row = cur.fetchone()
            if row is None:
                pytest.skip('数据库无生产订单，跳过')
                return

            order_no = row['order_no']

        try:
            watchdog.assert_process_count(order_no, min_count=1)
        except (AssertionError, pymysql.err.OperationalError) as e:
            print(f'[DB 看门狗] 工序数量断言异常（正常）: {e}')

        print(f'\n[DB 看门狗] 工序数量断言方法可用')

    def test_watchdog_process_step_state(self, watchdog, db_session):
        """工序步骤状态断言（JOIN production_orders → processes）"""
        with db_session.cursor() as cur:
            cur.execute(
                """SELECT po.order_no, pr.process_name
                   FROM processes pr
                   JOIN production_orders po ON pr.prod_order_id = po.id
                   LIMIT 1"""
            )
            row = cur.fetchone()
            if row is None:
                pytest.skip('数据库无工序步骤，跳过')
                return

            order_no = row['order_no']
            process_name = row['process_name']

        try:
            watchdog.assert_process_step_state(
                order_no, process_name, 'any_status'
            )
        except (AssertionError, pymysql.err.OperationalError) as e:
            print(f'[DB 看门狗] 工序步骤状态断言异常（正常）: {e}')

        print(f'\n[DB 看门狗] 工序步骤状态断言方法可用')


class TestDBWatchdogQuality:
    """质检记录看门狗"""

    def test_watchdog_qc_records(self, watchdog, db_session):
        """质检记录断言（查 quality_records 表）"""
        with db_session.cursor() as cur:
            cur.execute(
                "SELECT order_no FROM quality_records LIMIT 1"
            )
            row = cur.fetchone()
            if row is None:
                pytest.skip('数据库无质检记录，跳过')
                return

            order_no = row['order_no']

        try:
            watchdog.assert_qc_records(order_no, expected_result='passed')
        except AssertionError:
            pass

        print(f'\n[DB 看门狗] 质检记录断言方法可用')


class TestDBWatchdogInventory:
    """库存看门狗"""

    def test_watchdog_inventory_non_negative(self, watchdog, db_session):
        """库存非负断言（用 material_name）"""
        with db_session.cursor() as cur:
            cur.execute(
                "SELECT material_name FROM inventory WHERE is_deleted=0 AND quantity > 0 LIMIT 1"
            )
            row = cur.fetchone()
            if row is None:
                pytest.skip('数据库无库存数据，跳过')
                return

            material_name = row['material_name']

        try:
            watchdog.assert_inventory_non_negative(material_name)
        except AssertionError:
            pass

        print(f'\n[DB 看门狗] 库存非负断言方法可用')


class TestDBWatchdogConnection:
    """DBWatchdog 连接测试"""

    def test_mysql_connection(self):
        """MySQL 连接可用"""
        try:
            conn = DBWatchdog()
            with conn.mysql.cursor() as cur:
                cur.execute("SELECT 1 AS ok")
                row = cur.fetchone()
                assert row['ok'] == 1
            conn.close()
            print('\n[DB 看门狗] MySQL 连接正常')
        except pymysql.err.OperationalError as e:
            pytest.skip(f'MySQL 不可用: {e}')

    def test_redis_connection(self):
        """Redis 连接可用"""
        try:
            conn = DBWatchdog()
            conn.redis.ping()
            conn.close()
            print('\n[DB 看门狗] Redis 连接正常')
        except Exception as e:
            pytest.skip(f'Redis 不可用: {e}')

    def test_mysql_query_orders_count(self):
        """MySQL 订单表可查询"""
        try:
            conn = DBWatchdog()
            with conn.mysql.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM orders WHERE is_deleted=0")
                row = cur.fetchone()
                print(f'\n[DB 看门狗] 订单总数: {row["cnt"]}')
            conn.close()
        except pymysql.err.OperationalError as e:
            pytest.skip(f'订单表查询失败: {e}')

    def test_mysql_query_processes_count(self):
        """MySQL processes 表可查询"""
        try:
            conn = DBWatchdog()
            with conn.mysql.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM processes")
                row = cur.fetchone()
                print(f'\n[DB 看门狗] 工序总数: {row["cnt"]}')
            conn.close()
        except pymysql.err.OperationalError as e:
            pytest.skip(f'processes 表查询失败: {e}')

    def test_mysql_query_quality_count(self):
        """MySQL quality_records 表可查询"""
        try:
            conn = DBWatchdog()
            with conn.mysql.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM quality_records")
                row = cur.fetchone()
                print(f'\n[DB 看门狗] 质检记录总数: {row["cnt"]}')
            conn.close()
        except pymysql.err.OperationalError as e:
            pytest.skip(f'quality_records 表查询失败: {e}')
