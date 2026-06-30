# -*- coding: utf-8 -*-
"""
发货数据模型深度单元测试
覆盖 shipment.py 剩余未覆盖方法：create, confirm_ship, get_all,
get_all_shipments, get_by_shipment_no, save_tracking,
get_tracking_history, get_latest_tracking, get_all_with_latest_tracking,
get_finished_goods, get_finished_goods_by_id, get_recent_for_dashboard
"""
import json
import pytest
from unittest.mock import MagicMock, patch, call

# ── 辅助函数 ──────────────────────────────────────────────
def _make_mock_row(data: dict):
    """造一个既支持 dict() 又支持 [0] 的 mock row"""
    row = MagicMock()
    def as_dict():
        return data
    row.__iter__ = lambda self: iter(data.items())
    # 这个 mock 会被 dict(row) 正确调用
    row.items.return_value = list(data.items())
    # 模拟 __getitem__ 支持 row[0] 访问（如果源码用 idx）
    row.__getitem__.side_effect = lambda k: list(data.values())[k] if isinstance(k, int) else data[k]
    return row


class TestShipmentCreate:
    """ShipmentDAO.create 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.cursor.lastrowid = 42
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p_ship_no = patch('models.shipment.generate_shipment_no', return_value='SH-TEST-001')
        self.p.start()
        self.p_ship_no.start()
        yield
        self.p_ship_no.stop()
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_create_basic(self, dao):
        """create 基本路径"""
        data = {
            "order_id": 1, "finished_goods_id": 2,
            "ship_quantity": 100, "unit": "米",
            "logistics_company": "顺丰", "tracking_no": "SF123",
            "ship_date": "2024-06-01",
            "recipient": "张三", "recipient_phone": "13800138000",
            "recipient_address": "山东德州", "freight": 50,
            "remark": "测试发货",
        }
        result = dao.create(data)
        assert result == 42
        self.conn.commit.assert_called_once()

    def test_create_defaults(self, dao):
        """create 默认值（空字典）"""
        result = dao.create({})
        assert result == 42
        self.conn.commit.assert_called_once()


class TestShipmentConfirmShip:
    """ShipmentDAO.confirm_ship 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p_log = patch('models.shipment.log_status_change')
        self.p.start()
        self.mock_log = self.p_log.start()
        yield
        self.p_log.stop()
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def _set_fetchone(self, row: tuple):
        """设置 fetchone 返回值（第一个 SELECT）"""
        self.cursor.fetchone.side_effect = None
        self.cursor.fetchone.return_value = row

    def test_confirm_ship_no_row(self, dao):
        """confirm_ship 记录不存在"""
        self._set_fetchone(None)
        result = dao.confirm_ship(999)
        assert result is False

    def test_confirm_ship_no_fg_no_order(self, dao):
        """confirm_ship 有记录但 fg_id 和 order_id 均为 None"""
        # 第一个 fetchone 返回 (order_id, fg_id) = (None, None)
        self._set_fetchone((None, None))
        result = dao.confirm_ship(1)
        assert result is True
        # 验证 UPDATE shipments SET status
        assert self.cursor.execute.call_count >= 1

    def test_confirm_ship_with_fg(self, dao):
        """confirm_ship 有 fg_id 但无 order_id"""
        self._set_fetchone((None, 100))
        result = dao.confirm_ship(1)
        assert result is True
        # 应该调用了 UPDATE finished_goods
        fg_calls = [c for c in self.cursor.execute.call_args_list
                     if 'finished_goods' in str(c)]
        assert len(fg_calls) >= 1

    def test_confirm_ship_with_order(self, dao):
        """confirm_ship 有 order_id 但无 fg_id"""
        # 第一个 fetchone: (order_id=5, fg_id=None)
        # 后续 fetchone: 查询订单旧状态
        self.cursor.fetchone.side_effect = [
            (5, None),      # 第一个 SELECT shipments
            ("生产中",),     # SELECT orders status
        ]
        result = dao.confirm_ship(1)
        assert result is True
        # 验证调用了 UPDATE orders
        order_update_calls = [c for c in self.cursor.execute.call_args_list
                               if 'orders SET status' in str(c[0])]
        assert len(order_update_calls) >= 1

    def test_confirm_ship_with_both(self, dao):
        """confirm_ship 同时有 fg_id 和 order_id"""
        self.cursor.fetchone.side_effect = [
            (5, 100),       # 第一个 SELECT shipments
            ("待发货",),     # SELECT orders status
        ]
        result = dao.confirm_ship(1)
        assert result is True
        # 验证两条 UPDATE 都调了
        fg_calls = [c for c in self.cursor.execute.call_args_list
                     if 'finished_goods' in str(c[0])]
        order_calls = [c for c in self.cursor.execute.call_args_list
                        if 'orders SET status' in str(c[0])]
        assert len(fg_calls) >= 1
        assert len(order_calls) >= 1

    def test_confirm_ship_order_status_fetch_none(self, dao):
        """confirm_ship order_id 有值但查询订单状态返回 None"""
        self.cursor.fetchone.side_effect = [
            (5, None),      # shipments row
            None,           # 查询订单状态返回 None（row = None）
        ]
        result = dao.confirm_ship(1)
        assert result is True


class TestShipmentGetAll:
    """ShipmentDAO.get_all 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.cursor.fetchall.return_value = [
            {"id": 1, "shipment_no": "SH-001", "order_no": "ORD-001"},
            {"id": 2, "shipment_no": "SH-002", "order_no": "ORD-002"},
        ]
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_get_all_no_filter(self, dao):
        """get_all 无 filter"""
        result = dao.get_all()
        assert len(result) == 2

    def test_get_all_with_status_filter(self, dao):
        """get_all 带 status filter"""
        result = dao.get_all({"status": "待发货"})
        assert len(result) == 2

    def test_get_all_with_status_all(self, dao):
        """get_all status=全部（应跳过）"""
        result = dao.get_all({"status": "全部"})
        assert len(result) == 2

    def test_get_all_with_keyword(self, dao):
        """get_all 带 keyword"""
        result = dao.get_all({"keyword": "ORD-001"})
        assert len(result) == 2

    def test_get_all_with_date_from(self, dao):
        """get_all 带 date_from"""
        result = dao.get_all({"date_from": "2024-01-01"})
        assert len(result) == 2

    def test_get_all_with_date_to(self, dao):
        """get_all 带 date_to"""
        result = dao.get_all({"date_to": "2024-12-31"})
        assert len(result) == 2

    def test_get_all_with_all_filters(self, dao):
        """get_all 全 filter 组合"""
        result = dao.get_all({
            "status": "已发货",
            "keyword": "客户A",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        })
        assert len(result) == 2

    def test_get_all_custom_limit(self, dao):
        """get_all 自定义 limit"""
        self.cursor.fetchall.return_value = [{"id": 1}]
        result = dao.get_all({}, limit=50)
        assert len(result) == 1


class TestShipmentGetAllShipments:
    """ShipmentDAO.get_all_shipments 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.cursor.fetchall.return_value = [
            {"id": 1, "shipment_no": "SH-001", "tracking_no": "SF123"},
            {"id": 2, "shipment_no": "SH-002", "tracking_no": "SF456"},
        ]
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_get_all_shipments_no_filter(self, dao):
        """get_all_shipments 无 filter"""
        result = dao.get_all_shipments()
        assert len(result) == 2

    def test_get_all_shipments_with_status(self, dao):
        """get_all_shipments 带 status"""
        result = dao.get_all_shipments({"status": "待发货"})
        assert len(result) == 2

    def test_get_all_shipments_with_keyword(self, dao):
        """get_all_shipments 带 keyword（含 tracking_no 搜索）"""
        result = dao.get_all_shipments({"keyword": "SF123"})
        assert len(result) == 2

    def test_get_all_shipments_with_dates(self, dao):
        """get_all_shipments 带日期范围"""
        result = dao.get_all_shipments({"date_from": "2024-01-01", "date_to": "2024-12-31"})
        assert len(result) == 2

    def test_get_all_shipments_all_filters(self, dao):
        """get_all_shipments 全 filter"""
        result = dao.get_all_shipments({
            "status": "已发货", "keyword": "客户",
            "date_from": "2024-01-01", "date_to": "2024-12-31",
        })
        assert len(result) == 2

    def test_get_all_shipments_none_filter(self, dao):
        """get_all_shipments filters 为 None"""
        result = dao.get_all_shipments(None)
        assert len(result) == 2

    def test_get_all_shipments_empty_filter(self, dao):
        """get_all_shipments filters 为空字典"""
        result = dao.get_all_shipments({})
        assert len(result) == 2


class TestShipmentByNo:
    """ShipmentDAO.get_by_shipment_no 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_get_by_shipment_no_found(self, dao):
        """get_by_shipment_no 找到记录"""
        self.cursor.fetchone.return_value = {"id": 1, "shipment_no": "SH-TEST"}
        result = dao.get_by_shipment_no("SH-TEST")
        assert result is not None
        assert result["shipment_no"] == "SH-TEST"

    def test_get_by_shipment_no_not_found(self, dao):
        """get_by_shipment_no 未找到"""
        self.cursor.fetchone.return_value = None
        result = dao.get_by_shipment_no("NONEXIST")
        assert result is None


class TestShipmentSaveTracking:
    """ShipmentDAO.save_tracking 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_save_tracking_success(self, dao):
        """save_tracking 正常保存"""
        result = dao.save_tracking(1, "SF123", "delivered", "已签收",
                                   [{"time": "2024-06-01", "desc": "已签收"}], "SF")
        assert result is True
        self.conn.commit.assert_called_once()

    def test_save_tracking_empty_traces(self, dao):
        """save_tracking 空 traces 列表"""
        result = dao.save_tracking(1, "SF456", "pending", "运输中", [], "SF")
        assert result is True

    def test_save_tracking_exception(self, dao):
        """save_tracking 异常分支"""
        self.conn.cursor.side_effect = Exception("DB error")
        result = dao.save_tracking(1, "SF123", "error", "异常", [], "SF")
        assert result is False


class TestShipmentTrackingHistory:
    """ShipmentDAO.get_tracking_history 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_get_tracking_history_dict_rows(self, dao):
        """get_tracking_history 返回 dict row（已有最理想情况）"""
        self.cursor.fetchall.return_value = [
            {"id": 1, "shipment_id": 1, "tracking_no": "SF123",
             "state": "delivered", "state_text": "已签收",
             "traces": '[{"time":"2024-06-01","desc":"已签收"}]',
             "company_code": "SF", "query_time": "2024-06-01 10:00:00"},
        ]
        results = dao.get_tracking_history(1)
        assert len(results) == 1
        # traces 应被解析为列表
        assert isinstance(results[0]["traces"], list)

    def test_get_tracking_history_tuple_rows(self, dao):
        """get_tracking_history 返回 tuple row（覆盖最关键的 tuple 分支）"""
        self.cursor.fetchall.return_value = [
            (1, 1, "SF123", "delivered", "已签收",
             '[{"time":"2024-06-01","desc":"已签收"}]', "SF", "2024-06-01 10:00:00"),
        ]
        results = dao.get_tracking_history(1)
        assert len(results) == 1
        assert isinstance(results[0]["traces"], list)
        assert results[0]["id"] == 1

    def test_get_tracking_history_empty(self, dao):
        """get_tracking_history 无记录"""
        self.cursor.fetchall.return_value = []
        results = dao.get_tracking_history(1)
        assert results == []

    def test_get_tracking_history_traces_not_string(self, dao):
        """get_tracking_history traces 不是字符串（已解析）"""
        self.cursor.fetchall.return_value = [
            {"id": 1, "shipment_id": 1, "tracking_no": "SF123",
             "state": "delivered", "state_text": "已签收",
             "traces": [{"time": "2024-06-01", "desc": "已签收"}],
             "company_code": "SF", "query_time": "2024-06-01 10:00:00"},
        ]
        results = dao.get_tracking_history(1)
        assert len(results) == 1
        assert isinstance(results[0]["traces"], list)

    def test_get_tracking_history_json_decode_error(self, dao):
        """get_tracking_history traces 是无效 JSON"""
        self.cursor.fetchall.return_value = [
            {"id": 1, "shipment_id": 1, "tracking_no": "SF123",
             "state": "delivered", "state_text": "已签收",
             "traces": "不是有效json@@@",
             "company_code": "SF", "query_time": "2024-06-01 10:00:00"},
        ]
        results = dao.get_tracking_history(1)
        assert len(results) == 1
        assert results[0]["traces"] == []

    def test_get_tracking_history_custom_limit(self, dao):
        """get_tracking_history 自定义 limit"""
        self.cursor.fetchall.return_value = [{"id": 1, "traces": "[]"}]
        results = dao.get_tracking_history(1, limit=5)
        assert len(results) == 1


class TestShipmentLatestTracking:
    """ShipmentDAO.get_latest_tracking 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_get_latest_tracking_found(self, dao):
        """get_latest_tracking 有记录"""
        self.cursor.fetchall.return_value = [
            {"id": 1, "shipment_id": 1, "traces": "[]"},
        ]
        result = dao.get_latest_tracking(1)
        assert result is not None
        assert result["id"] == 1

    def test_get_latest_tracking_not_found(self, dao):
        """get_latest_tracking 无记录"""
        self.cursor.fetchall.return_value = []
        result = dao.get_latest_tracking(1)
        assert result is None


class TestShipmentWithLatestTracking:
    """ShipmentDAO.get_all_with_latest_tracking 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.cursor.fetchall.return_value = [
            {"id": 1, "shipment_no": "SH-001", "track_state": "已签收", "track_time": "2024-06-01"},
            {"id": 2, "shipment_no": "SH-002", "track_state": None, "track_time": None},
        ]
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_get_all_with_latest_tracking_no_filter(self, dao):
        """get_all_with_latest_tracking 无 filter"""
        result = dao.get_all_with_latest_tracking()
        assert len(result) == 2

    def test_get_all_with_latest_tracking_with_status(self, dao):
        """get_all_with_latest_tracking 带 status"""
        result = dao.get_all_with_latest_tracking({"status": "待发货"})
        assert len(result) == 2

    def test_get_all_with_latest_tracking_with_keyword(self, dao):
        """get_all_with_latest_tracking 带 keyword"""
        result = dao.get_all_with_latest_tracking({"keyword": "SH-001"})
        assert len(result) == 2

    def test_get_all_with_latest_tracking_with_dates(self, dao):
        """get_all_with_latest_tracking 带日期"""
        result = dao.get_all_with_latest_tracking({"date_from": "2024-01-01", "date_to": "2024-12-31"})
        assert len(result) == 2

    def test_get_all_with_latest_tracking_all_filters(self, dao):
        """get_all_with_latest_tracking 全 filter"""
        result = dao.get_all_with_latest_tracking({
            "status": "已发货", "keyword": "客户",
            "date_from": "2024-01-01", "date_to": "2024-12-31",
        })
        assert len(result) == 2

    def test_get_all_with_latest_tracking_none_filter(self, dao):
        """get_all_with_latest_tracking filters=None"""
        result = dao.get_all_with_latest_tracking(None)
        assert len(result) == 2

    def test_get_all_with_latest_tracking_empty_filter(self, dao):
        """get_all_with_latest_tracking 空字典 filter"""
        result = dao.get_all_with_latest_tracking({})
        assert len(result) == 2


class TestShipmentFinishedGoods:
    """ShipmentDAO.get_finished_goods 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.cursor.fetchall.return_value = [
            {"id": 1, "order_no": "ORD-001", "status": "在库"},
            {"id": 2, "order_no": "ORD-002", "status": "在库"},
        ]
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_get_finished_goods_with_order_id_days_limit(self, dao):
        """get_finished_goods 有 order_id + days_limit"""
        result = dao.get_finished_goods(order_id=1, days_limit=60)
        assert len(result) == 2

    def test_get_finished_goods_with_order_id_no_days_limit(self, dao):
        """get_finished_goods 有 order_id 但 days_limit=None"""
        result = dao.get_finished_goods(order_id=1, days_limit=None)
        assert len(result) == 2

    def test_get_finished_goods_no_order_id_days_limit(self, dao):
        """get_finished_goods 无 order_id + 有 days_limit"""
        result = dao.get_finished_goods(order_id=None, days_limit=30)
        assert len(result) == 2

    def test_get_finished_goods_no_order_id_no_days_limit(self, dao):
        """get_finished_goods 无 order_id + days_limit=None"""
        result = dao.get_finished_goods(order_id=None, days_limit=None)
        assert len(result) == 2

    def test_get_finished_goods_empty(self, dao):
        """get_finished_goods 无结果"""
        self.cursor.fetchall.return_value = []
        result = dao.get_finished_goods(order_id=999)
        assert result == []


class TestShipmentFinishedGoodsById:
    """ShipmentDAO.get_finished_goods_by_id 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_get_finished_goods_by_id_found(self, dao):
        """get_finished_goods_by_id 找到"""
        self.cursor.fetchone.return_value = {"id": 1, "order_no": "ORD-001"}
        result = dao.get_finished_goods_by_id(1)
        assert result is not None
        assert result["id"] == 1

    def test_get_finished_goods_by_id_not_found(self, dao):
        """get_finished_goods_by_id 未找到"""
        self.cursor.fetchone.return_value = None
        result = dao.get_finished_goods_by_id(999)
        assert result is None


class TestShipmentRecentForDashboard:
    """ShipmentDAO.get_recent_for_dashboard 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.cursor = MagicMock()
        self.conn = MagicMock()
        self.conn.cursor.return_value = self.cursor
        self.cursor.fetchall.return_value = [
            {"shipment_no": "SH-001", "order_no": "ORD-001", "customer_name": "客户A",
             "ship_quantity": 100, "unit": "米", "logistics_company": "顺丰",
             "status": "已发货", "ship_date": "2024-06-01"},
        ]
        self.p = patch('models.shipment.get_connection', return_value=self.conn)
        self.p.start()
        yield
        self.p.stop()

    @pytest.fixture
    def dao(self):
        from models.shipment import ShipmentDAO
        return ShipmentDAO()

    def test_get_recent_for_dashboard(self, dao):
        """get_recent_for_dashboard 正常"""
        result = dao.get_recent_for_dashboard()
        assert len(result) == 1
        assert result[0]["shipment_no"] == "SH-001"

    def test_get_recent_for_dashboard_custom_limit(self, dao):
        """get_recent_for_dashboard 自定义 limit=5"""
        result = dao.get_recent_for_dashboard(limit=5)
        assert len(result) == 1

    def test_get_recent_for_dashboard_empty(self, dao):
        """get_recent_for_dashboard 空结果"""
        self.cursor.fetchall.return_value = []
        result = dao.get_recent_for_dashboard()
        assert result == []
