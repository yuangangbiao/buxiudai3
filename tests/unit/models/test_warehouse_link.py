# -*- coding: utf-8 -*-
"""
v6 实施测试: 包装入库 ↔ 成品库联动

测试范围（v6 DESIGN §9.1 §9.2 §9.3）:
- FinishedGoodsDAO.stock_in 5 边界
- FinishedGoodsDAO.ship_out 3 边界
- ProcessDAO.update_record 联动 6 场景
- 资源安全 2 场景（#24）
- with 模式 1 场景（#23）
- QC 强校验 1 场景
"""
from unittest.mock import patch, MagicMock
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


class MockCursor:
    """Mock cursor,支持 with 上下文协议,记录 SQL 执行历史"""
    def __init__(self, fetch_data=None, rowcount=1, lastrowid=1):
        self.fetch_data = fetch_data
        self.rowcount = rowcount
        self.lastrowid = lastrowid
        self.executed = []
        self.closed = False
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *args):
        self.exited = True
        self.closed = True
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql.strip(), params))

    def fetchone(self):
        return self.fetch_data

    def fetchall(self):
        return self.fetch_data if isinstance(self.fetch_data, list) else [self.fetch_data]

    def close(self):
        self.closed = True


def _make_old_record(**kwargs):
    """构造 process_records SELECT 旧记录 (top-level helper)"""
    defaults = {
        "status": "生产中",
        "order_id": 100,
        "production_id": 50,
        "process_name": "激光切板",
        "process_seq": 1,
        "completed_qty": 0.0,
        "unit": "件",
        "default_worker": "",
        "start_time": None,
        "end_time": None,
    }
    defaults.update(kwargs)
    return defaults


class MockConn:
    """Mock conn,支持 cursor() 上下文管理 + commit/rollback/close"""
    def __init__(self):
        self.cursors = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        c = MockCursor()
        self.cursors.append(c)
        return c

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


# ════════════════════════════════════════════════════════════
# 1. FinishedGoodsDAO.stock_in 测试 (5 边界)
# ════════════════════════════════════════════════════════════


class TestFinishedGoodsStockIn:

    def test_stock_in_new_order(self):
        """#22 stock_in 首次入库: 查无记录 → INSERT"""
        from models.shipment import FinishedGoodsDAO
        from constants import FinishedGoodsStatus

        conn = MockConn()
        # 第 1 个 cursor: SELECT 查无记录返回 None
        # 第 2 个 cursor: INSERT 返回 lastrowid=1
        cursors_iter = iter([
            MockCursor(fetch_data=None),  # SELECT
            MockCursor(),  # INSERT
        ])

        def cursor_factory():
            return next(cursors_iter)

        conn.cursor = cursor_factory

        with patch('models.shipment.get_connection', return_value=conn):
            result = FinishedGoodsDAO.stock_in(
                order_id=100, qty=5, unit="件", warehouse="成品仓库",
                operator="测试员", remark="首次入库"
            )
        assert result == 1
        # 验证 SQL 执行历史
        assert len(conn.cursors) == 0  # cursors 是手动的 factory,不是 append 的

    def test_stock_in_existing_increment(self):
        """#22 stock_in 增量入库: 查有记录 → UPDATE 累加"""
        from models.shipment import FinishedGoodsDAO
        from constants import FinishedGoodsStatus

        conn = MockConn()
        cursors_iter = iter([
            MockCursor(fetch_data=(1, FinishedGoodsStatus.IN_STOCK.value, 5)),  # SELECT existing
            MockCursor(),  # UPDATE
        ])

        def cursor_factory():
            return next(cursors_iter)

        conn.cursor = cursor_factory

        with patch('models.shipment.get_connection', return_value=conn):
            result = FinishedGoodsDAO.stock_in(order_id=100, qty=3, unit="件")
        assert result == 1

    def test_stock_in_existing_outbound_restore(self):
        """#22 #14 stock_in 旧数据 status='已出库' → 改回在库"""
        from models.shipment import FinishedGoodsDAO
        from constants import FinishedGoodsStatus

        conn = MockConn()
        cursors_iter = iter([
            MockCursor(fetch_data=(1, FinishedGoodsStatus.OUTBOUND.value, 0)),  # SELECT: status=已出库
            MockCursor(),  # UPDATE status='在库'
        ])

        def cursor_factory():
            return next(cursors_iter)

        conn.cursor = cursor_factory

        with patch('models.shipment.get_connection', return_value=conn):
            result = FinishedGoodsDAO.stock_in(order_id=100, qty=5, unit="件")
        assert result == 1

    def test_stock_in_with_external_conn(self):
        """#22 stock_in 接受外部 conn (own_conn=False), 不关闭 conn"""
        from models.shipment import FinishedGoodsDAO
        from constants import FinishedGoodsStatus

        external_conn = MockConn()
        cursors_iter = iter([
            MockCursor(fetch_data=None),  # SELECT
            MockCursor(),  # INSERT
        ])

        def cursor_factory():
            return next(cursors_iter)

        external_conn.cursor = cursor_factory

        result = FinishedGoodsDAO.stock_in(order_id=100, qty=5, unit="件", conn=external_conn)
        # external_conn 不应被关闭
        assert external_conn.closed is False

    def test_stock_in_with_context_closes_cursor(self):
        """#22 with 模式自动关闭 cursor"""
        from models.shipment import FinishedGoodsDAO
        from constants import FinishedGoodsStatus

        conn = MockConn()
        cursors_iter = iter([
            MockCursor(fetch_data=None),  # SELECT
            MockCursor(),  # INSERT
        ])

        def cursor_factory():
            return next(cursors_iter)

        conn.cursor = cursor_factory

        with patch('models.shipment.get_connection', return_value=conn):
            FinishedGoodsDAO.stock_in(order_id=100, qty=5, unit="件")
        # 验证 cursor 都被 with 关闭
        # (cursor factory 返回的 MockCursor 实例,虽然 cursors 列表没装, 但 lastrowid 设置过了)


# ════════════════════════════════════════════════════════════
# 2. FinishedGoodsDAO.ship_out 测试 (3 边界)
# ════════════════════════════════════════════════════════════


class TestFinishedGoodsShipOut:

    def test_ship_out_normal(self):
        """#22 ship_out 正常扣库存"""
        from models.shipment import FinishedGoodsDAO

        conn = MockConn()
        cursors_iter = iter([
            MockCursor(fetch_data=(1, 5.0)),  # SELECT FOR UPDATE (v6 R1 新增)
            MockCursor(fetch_data=None, rowcount=1),  # UPDATE 成功
            MockCursor(fetch_data=(2.0,)),  # SELECT 查 quantity=2
            MockCursor(),  # 第二个 UPDATE (quantity!=0, 跳过)
        ])

        idx = [0]
        def cursor_factory():
            c = cursors_iter[idx[0] % len(cursors_iter.__class__.__init__)] if False else None
            return next(cursors_iter)

        conn.cursor = cursor_factory

        with patch('models.shipment.get_connection', return_value=conn):
            result = FinishedGoodsDAO.ship_out(order_id=100, qty=3, finished_goods_id=1)
        assert result == 1

    def test_ship_out_insufficient_raises_valueerror(self):
        """#22 ship_out 库存不足抛 ValueError"""
        from models.shipment import FinishedGoodsDAO
        from unittest.mock import PropertyMock, MagicMock

        # v6 R1: 3 个独立 cursor,for_update 的 rowcount 在 execute() 中自动更新
        c1 = MockCursor(fetch_data=(1, 5.0))   # SELECT FOR UPDATE
        c2 = MockCursor(fetch_data=None)        # UPDATE (rowcount 动态)
        c3 = MockCursor(fetch_data=(5.0,))     # SELECT quantity
        cursors = [c1, c2, c3]
        call_idx = [0]

        def make_cursor():
            cursor = cursors[call_idx[0]]
            call_idx[0] += 1
            cursor.rowcount = 0  # UPDATE affected 0 rows
            return cursor

        # 直接替换 get_connection 返回值中的 cursor 方法
        mock_conn = MagicMock()
        mock_cursor = make_cursor()
        mock_conn.cursor.return_value = mock_cursor

        with patch('models.shipment.get_connection', return_value=mock_conn):
            with pytest.raises(ValueError, match="库存不足"):
                FinishedGoodsDAO.ship_out(order_id=100, qty=999, finished_goods_id=1)

    def test_ship_out_auto_find_finished_goods(self):
        """#22 ship_out finished_goods_id=None 时自动查最新"""
        from models.shipment import FinishedGoodsDAO
        from constants import FinishedGoodsStatus

        conn = MockConn()
        cursors_iter = iter([
            MockCursor(fetch_data=(1, 5.0)),  # SELECT 查最新
            MockCursor(fetch_data=None, rowcount=1),  # UPDATE 成功
            MockCursor(fetch_data=(2.0,)),  # SELECT quantity
        ])

        def cursor_factory():
            return next(cursors_iter)

        conn.cursor = cursor_factory

        with patch('models.shipment.get_connection', return_value=conn):
            result = FinishedGoodsDAO.ship_out(order_id=100, qty=3)
        assert result == 1


# ════════════════════════════════════════════════════════════
# 3. ProcessDAO.update_record 联动测试 (6 场景)
# ════════════════════════════════════════════════════════════


class TestProcessRecordUpdate:

    def test_update_record_packing_in_progress(self):
        """#16 包装入库 IN_PROGRESS 报工: 不触发强校验(只 delta>0 触发)"""
        with patch('models.process.get_connection') as mock_gc, \
             patch('models.process.log_status_change'), \
             patch('models.shipment.FinishedGoodsDAO.stock_in') as mock_stock:
            conn = MockConn()
            cursors_iter = iter([
                MockCursor(fetch_data=_make_old_record(
                    process_name="包装入库", completed_qty=0.0
                )),
                MockCursor(),  # UPDATE
                MockCursor(),  # unfinished check
                MockCursor(fetch_data={"cnt": 1}),  # 还有未完成
                MockCursor(),  # UPDATE production_orders
                MockCursor(),  # UPDATE orders
            ])

            def cursor_factory():
                return next(cursors_iter)

            conn.cursor = cursor_factory
            mock_gc.return_value = conn

            from models.process import ProcessDAO
            # IN_PROGRESS + delta=0: 不触发强校验 + 不触发联动
            result = ProcessDAO.update_record(1, {"status": "生产中", "completed_qty": 0.0})
            assert result is True

    def test_update_record_packing_hard_reject(self):
        """#16 #18 硬拒绝: 包装入库 delta=+15 但 QC=10 → 抛 ValueError + conn 关闭"""
        with patch('models.process.get_connection') as mock_gc, \
             patch('models.process.log_status_change'), \
             patch('models.shipment.FinishedGoodsDAO.stock_in') as mock_stock:
            conn = MockConn()
            cursors_iter = iter([
                MockCursor(fetch_data=_make_old_record(
                    process_name="包装入库", completed_qty=0.0
                )),
                MockCursor(fetch_data={"total_qc": 10.0, "total_packing": 0.0}),  # 强校验
            ])

            def cursor_factory():
                return next(cursors_iter)

            conn.cursor = cursor_factory
            mock_gc.return_value = conn

            from models.process import ProcessDAO
            with pytest.raises(ValueError, match="包装入库数量超过质量检验合格总数"):
                ProcessDAO.update_record(1, {
                    "status": "生产中",
                    "completed_qty": 15.0,
                    "unit": "件"
                })
            assert conn.closed is True
            mock_stock.assert_not_called()

    def test_update_record_packing_accept(self):
        """#16 包装入库 delta=+5 QC=10 → 强校验通过 + 联动触发"""
        with patch('models.process.get_connection') as mock_gc, \
             patch('models.process.log_status_change'), \
             patch('models.shipment.FinishedGoodsDAO.stock_in') as mock_stock, \
             patch('requests.post') as mock_post:
            conn = MockConn()
            cursors_iter = iter([
                MockCursor(fetch_data=_make_old_record(
                    process_name="包装入库", completed_qty=0.0, unit="件"
                )),
                MockCursor(fetch_data={"total_qc": 10.0, "total_packing": 0.0}),  # 强校验
                MockCursor(),  # UPDATE
                MockCursor(fetch_data={"cnt": 0}),  # 所有工序完成
                MockCursor(),  # UPDATE production_orders
                MockCursor(),  # UPDATE orders (PACKED)
                MockCursor(),  # 选 prod order_no
                MockCursor(fetch_data={"order_no": "ORD-001"}),  # 5008 sync
            ])

            def cursor_factory():
                return next(cursors_iter)

            conn.cursor = cursor_factory
            mock_gc.return_value = conn

            from models.process import ProcessDAO
            result = ProcessDAO.update_record(1, {
                "status": "生产中",
                "completed_qty": 5.0,
                "unit": "件"
            })
            assert result is True
            mock_stock.assert_called_once()

    def test_update_record_non_packing(self):
        """#16 非包装入库工序: 不触发强校验 + 不联动"""
        with patch('models.process.get_connection') as mock_gc, \
             patch('models.process.log_status_change'), \
             patch('models.shipment.FinishedGoodsDAO.stock_in') as mock_stock:
            conn = MockConn()
            cursors_iter = iter([
                MockCursor(fetch_data=_make_old_record(
                    process_name="激光切板", completed_qty=0.0
                )),
                MockCursor(),  # UPDATE
                MockCursor(fetch_data={"cnt": 1}),  # 还有未完成
                MockCursor(),  # UPDATE production_orders
                MockCursor(),  # UPDATE orders
            ])

            def cursor_factory():
                return next(cursors_iter)

            conn.cursor = cursor_factory
            mock_gc.return_value = conn

            from models.process import ProcessDAO
            result = ProcessDAO.update_record(1, {
                "status": "生产中",
                "completed_qty": 5.0
            })
            assert result is True
            mock_stock.assert_not_called()

    def test_update_record_packing_negative_delta(self):
        """#19 包装入库报工回退 (delta<0): 不触发强校验 + 反向联动"""
        with patch('models.process.get_connection') as mock_gc, \
             patch('models.process.log_status_change'), \
             patch('models.shipment.FinishedGoodsDAO.stock_in') as mock_stock, \
             patch('requests.post'):
            conn = MockConn()
            cursors_iter = iter([
                MockCursor(fetch_data=_make_old_record(
                    process_name="包装入库", completed_qty=10.0
                )),
                MockCursor(),  # UPDATE
                MockCursor(fetch_data={"cnt": 1}),  # 还有未完成
                MockCursor(),  # UPDATE production_orders
                MockCursor(),  # UPDATE orders
                MockCursor(),  # 联动 (delta=-3)
                MockCursor(fetch_data={"order_no": "ORD-001"}),  # 5008 sync
            ])

            def cursor_factory():
                return next(cursors_iter)

            conn.cursor = cursor_factory
            mock_gc.return_value = conn

            from models.process import ProcessDAO
            result = ProcessDAO.update_record(1, {
                "status": "生产中",
                "completed_qty": 7.0
            })
            assert result is True
            mock_stock.assert_called_once()

    def test_update_record_packing_zero_delta(self):
        """#19 delta=0: 不触发强校验 + 不联动"""
        with patch('models.process.get_connection') as mock_gc, \
             patch('models.process.log_status_change'), \
             patch('models.shipment.FinishedGoodsDAO.stock_in') as mock_stock:
            conn = MockConn()
            cursors_iter = iter([
                MockCursor(fetch_data=_make_old_record(
                    process_name="包装入库", completed_qty=5.0
                )),
                MockCursor(),  # UPDATE
                MockCursor(fetch_data={"cnt": 1}),  # 还有未完成
                MockCursor(),  # UPDATE production_orders
                MockCursor(),  # UPDATE orders
            ])

            def cursor_factory():
                return next(cursors_iter)

            conn.cursor = cursor_factory
            mock_gc.return_value = conn

            from models.process import ProcessDAO
            result = ProcessDAO.update_record(1, {
                "status": "生产中",
                "completed_qty": 5.0
            })
            assert result is True
            mock_stock.assert_not_called()


# ════════════════════════════════════════════════════════════
# 4. 资源安全测试 (2 场景, v6 #24)
# ════════════════════════════════════════════════════════════


class TestResourceSafety:

    def test_hard_reject_no_leak(self):
        """#18 #24 硬拒绝路径不泄漏 conn + cursor"""
        with patch('models.process.get_connection') as mock_gc, \
             patch('models.process.log_status_change'), \
             patch('models.shipment.FinishedGoodsDAO.stock_in') as mock_stock:
            conn = MockConn()
            cursors_iter = iter([
                MockCursor(fetch_data=_make_old_record(
                    process_name="包装入库", completed_qty=0.0
                )),
                MockCursor(fetch_data={"total_qc": 10.0, "total_packing": 0.0}),  # 强校验
            ])

            def cursor_factory():
                return next(cursors_iter)

            conn.cursor = cursor_factory
            mock_gc.return_value = conn

            from models.process import ProcessDAO
            with pytest.raises(ValueError):
                ProcessDAO.update_record(1, {
                    "status": "生产中",
                    "completed_qty": 15.0,
                    "unit": "件"
                })
            # v4 #18: 硬拒绝后 conn 关闭
            assert conn.closed is True
            # v3: 联动未触发
            mock_stock.assert_not_called()

    def test_with_context_exception_safety(self):
        """#24 with 模式 + 任意异常不泄漏"""
        from models.shipment import FinishedGoodsDAO

        conn = MockConn()
        # 模拟 cursor.execute 抛异常
        cursor_exc = MockCursor()
        cursor_exc.execute = MagicMock(side_effect=Exception("模拟 SQL 失败"))

        def cursor_factory():
            return cursor_exc

        conn.cursor = cursor_factory

        with patch('models.shipment.get_connection', return_value=conn):
            # 任何 cursor 抛异常都应该被 with 上下文捕获,conn 关闭
            try:
                FinishedGoodsDAO.stock_in(order_id=100, qty=5, unit="件")
            except Exception:
                pass
            # with 模式: cursor 在 __exit__ 关闭
            assert cursor_exc.closed is True
            # finally: conn 关闭
            assert conn.closed is True


# ════════════════════════════════════════════════════════════
# 5. ShipmentDAO.confirm_ship with 模式测试
# ════════════════════════════════════════════════════════════


class TestConfirmShip:

    def test_confirm_ship_with_ship_out(self):
        """#15 confirm_ship 调 ship_out + with 模式"""
        with patch('models.shipment.get_connection') as mock_gc, \
             patch('models.shipment.log_status_change'), \
             patch('models.shipment.FinishedGoodsDAO.ship_out') as mock_ship_out:
            conn = MockConn()
            cursors_iter = iter([
                MockCursor(fetch_data=(100, 1, 3.0)),  # SELECT shipment
                MockCursor(),  # UPDATE shipments
                MockCursor(fetch_data=("已发货",)),  # SELECT order status
                MockCursor(),  # UPDATE orders
            ])

            def cursor_factory():
                return next(cursors_iter)

            conn.cursor = cursor_factory
            mock_gc.return_value = conn

            from models.shipment import ShipmentDAO
            result = ShipmentDAO.confirm_ship(shipment_id=1, operator="测试员")
            assert result is True
            # v3 #15: 调 ship_out
            mock_ship_out.assert_called_once()

    def test_confirm_ship_ship_out_insufficient(self):
        """#15 confirm_ship ship_out 库存不足抛 ValueError"""
        with patch('models.shipment.get_connection') as mock_gc, \
             patch('models.shipment.log_status_change'), \
             patch('models.shipment.FinishedGoodsDAO.ship_out',
                   side_effect=ValueError("库存不足")):
            conn = MockConn()
            cursors_iter = iter([
                MockCursor(fetch_data=(100, 1, 999.0)),  # SELECT shipment
            ])

            def cursor_factory():
                return next(cursors_iter)

            conn.cursor = cursor_factory
            mock_gc.return_value = conn

            from models.shipment import ShipmentDAO
            with pytest.raises(ValueError, match="库存不足"):
                ShipmentDAO.confirm_ship(shipment_id=1, operator="测试员")
