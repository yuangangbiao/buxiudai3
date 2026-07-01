# -*- coding: utf-8 -*-
"""
OrderDAO 核心 CRUD 单元测试
使用共享 mock_db fixture，覆盖所有主要业务方法
"""
import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime


# ---------------------------------------------------------------------------
# Local fixtures – compose with shared mock_db
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_order(mock_db):
    """Extends mock_db to patch module-level get_connection in models.order."""
    with patch('models.order.get_connection', return_value=mock_db['conn']), \
         patch('models.order.log_status_change', return_value=None), \
         patch('models.order.log_order_action', return_value=None):
        yield mock_db


@pytest.fixture
def mock_db_order_with_log(mock_db):
    """
    Extends mock_db for tests that need log_status_change/log_order_action
    to actually use the mock connection.
    """
    with patch('models.order.get_connection', return_value=mock_db['conn']):
        yield mock_db


# ===================== BaseDAO 基类测试（使用 mock_db） =====================

class TestBaseDAOWithMock:
    """BaseDAO 基类方法测试（重构自手动 patch → 共享 mock_db fixture）"""

    def test_get_by_id(self, mock_db):
        cursor = mock_db['cursor']
        cursor.fetchone.return_value = {'id': 1, 'order_no': 'ORD001', 'status': '进行中'}

        from models.base_dao import BaseDAO
        dao = BaseDAO('orders')
        result = dao.get_by_id(1)

        assert result is not None
        assert result['id'] == 1
        assert result['order_no'] == 'ORD001'
        cursor.execute.assert_called_once()

    def test_get_by_id_not_found(self, mock_db):
        cursor = mock_db['cursor']
        cursor.fetchone.return_value = None

        from models.base_dao import BaseDAO
        dao = BaseDAO('orders')
        result = dao.get_by_id(9999)

        assert result is None

    def test_get_all(self, mock_db):
        cursor = mock_db['cursor']
        cursor.fetchall.return_value = [
            {'id': 1, 'order_no': 'ORD001'},
            {'id': 2, 'order_no': 'ORD002'},
        ]

        from models.base_dao import BaseDAO
        dao = BaseDAO('orders')
        results = dao.get_all()

        assert len(results) == 2
        assert results[0]['order_no'] == 'ORD001'

    def test_get_all_with_filters(self, mock_db):
        cursor = mock_db['cursor']
        cursor.fetchall.return_value = [{'id': 1, 'status': '进行中'}]

        from models.base_dao import BaseDAO
        dao = BaseDAO('orders')
        results = dao.get_all(filters={'status': '进行中'})

        assert len(results) == 1
        call_args = str(cursor.execute.call_args)
        assert 'status' in call_args

    def test_create(self, mock_db):
        cursor = mock_db['cursor']
        cursor.lastrowid = 123

        from models.base_dao import BaseDAO
        dao = BaseDAO('orders')
        new_id = dao.create({'order_no': 'ORD003', 'customer_name': '测试客户'})

        assert new_id == 123
        mock_db['conn'].commit.assert_called()

    def test_update(self, mock_db):
        cursor = mock_db['cursor']
        cursor.rowcount = 1

        from models.base_dao import BaseDAO
        dao = BaseDAO('orders')
        success = dao.update(1, {'status': '已完成'})

        assert success is True
        mock_db['conn'].commit.assert_called()

    def test_delete_soft(self, mock_db):
        cursor = mock_db['cursor']
        cursor.rowcount = 1

        from models.base_dao import BaseDAO
        dao = BaseDAO('orders')
        success = dao.delete(1, hard=False)

        assert success is True
        call_args = str(cursor.execute.call_args)
        assert 'is_deleted=1' in call_args

    def test_count(self, mock_db):
        cursor = mock_db['cursor']
        cursor.fetchone.return_value = {'cnt': 42}

        from models.base_dao import BaseDAO
        dao = BaseDAO('orders')
        count = dao.count()

        assert count == 42

    def test_pagination(self, mock_db):
        cursor = mock_db['cursor']
        cursor.fetchone.return_value = {'cnt': 100}
        cursor.fetchall.return_value = [
            {'id': 1}, {'id': 2}, {'id': 3}
        ]

        from models.base_dao import BaseDAO
        dao = BaseDAO('orders')
        result = dao.get_paginated(page=2, page_size=10)

        assert result['page'] == 2
        assert result['page_size'] == 10
        assert result['total'] == 100
        assert result['total_pages'] == 10
        assert len(result['items']) == 3

    def test_exists(self, mock_db):
        cursor = mock_db['cursor']
        cursor.fetchone.return_value = {'1': 1}

        from models.base_dao import BaseDAO
        dao = BaseDAO('orders')
        exists = dao.exists(1)

        assert exists is True


# ===================== OrderDAO.create 方法测试 =====================

class TestOrderDAOCreate:
    """OrderDAO.create 新建订单方法测试"""

    def test_create_success(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.lastrowid = 101

        from models.order import OrderDAO
        new_id = OrderDAO.create({
            'order_no': 'ORD-TEST-001',
            'customer_name': '测试客户',
            'product_type': '不锈钢网带',
            'quantity': 10,
            'unit_price': '150',
        })

        assert new_id == 101
        execute_sql = cursor.execute.call_args[0][0] if cursor.execute.call_args else ''
        assert 'INSERT INTO orders' in execute_sql
        mock_db_order['conn'].commit.assert_called_once()

    def test_create_calculates_total_amount(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.lastrowid = 102

        from models.order import OrderDAO
        OrderDAO.create({
            'order_no': 'ORD-TEST-002',
            'customer_name': '客户A',
            'quantity': 20,
            'unit_price': '100',
        })

        call_args = cursor.execute.call_args[0][1]
        assert call_args[14] == 2000.0

    def test_create_with_extra_params(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.lastrowid = 103

        from models.order import OrderDAO
        OrderDAO.create({
            'order_no': 'ORD-TEST-003',
            'customer_name': '客户B',
            'quantity': 1,
            'unit_price': '50',
            '表面处理方式': '抛光',
            '总宽': '1200mm',
        })

        call_args = cursor.execute.call_args[0][1]
        assert '"表面处理方式": "抛光"' in call_args[21]
        assert '"总宽": "1200mm"' in call_args[21]

    def test_create_defaults_quantity_and_price(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.lastrowid = 103
        cursor.fetchone.side_effect = [
            {'id': 103, 'status': '待确认'}, {'cnt': 99},
        ]
        cursor.rowcount = 1

        from models.order import OrderDAO
        result = OrderDAO.create({
            'order_no': 'ORD-TEST-003',
            'customer_name': '默认客户',
            'product_type': '网带',
        })
        assert result == 103

        call_args = cursor.execute.call_args[0][1]
        assert call_args[11] == 1.0
        assert call_args[12] == '米'
        assert call_args[13] == 0.0

    def test_create_sets_pending_status(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.lastrowid = 105

        from constants import OrderStatus
        from models.order import OrderDAO
        OrderDAO.create({
            'order_no': 'ORD-TEST-005',
            'customer_name': '客户D',
        })

        call_args = cursor.execute.call_args[0][1]
        assert call_args[18] == OrderStatus.PENDING.value


# ===================== OrderDAO.update 方法测试 =====================

class TestOrderDAOUpdate:
    """OrderDAO.update 更新订单方法测试"""

    def test_update_success(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.side_effect = [
            {'status': '待确认', 'order_no': 'ORD-UPD-001'},
            {'order_no': 'ORD-UPD-001'},
        ]
        cursor.rowcount = 1

        from models.order import OrderDAO
        result = OrderDAO.update(1, {'customer_name': '新客户名'})

        assert result is True
        execute_sql = cursor.execute.call_args_list[1][0][0]
        assert 'UPDATE orders' in execute_sql
        mock_db_order['conn'].commit.assert_called_once()

    def test_update_with_status_change(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.side_effect = [
            {'status': '待确认', 'order_no': 'ORD-UPD-002'},
            None,
        ]
        cursor.rowcount = 1

        from models.order import OrderDAO
        result = OrderDAO.update(1, {'customer_name': '客户X', 'status': '进行中'})

        assert result is True

    def test_update_not_found(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.return_value = None
        cursor.rowcount = 0

        from models.order import OrderDAO
        result = OrderDAO.update(9999, {'customer_name': '不存在'})

        assert result is True


# ===================== OrderDAO.update_status 方法测试 =====================

class TestOrderDAOUpdateStatus:
    """OrderDAO.update_status 状态更新方法测试"""

    def test_update_status_success(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.side_effect = [
            {'status': '待确认', 'order_no': 'ORD-STAT-001'},
            None,
        ]
        cursor.rowcount = 1

        from models.order import OrderDAO
        result = OrderDAO.update_status(1, '进行中')

        assert result is True
        update_call = cursor.execute.call_args_list[1][0]
        assert 'UPDATE orders SET status=' in update_call[0]

    def test_update_status_order_not_found(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.return_value = None
        cursor.rowcount = 0

        from models.order import OrderDAO
        result = OrderDAO.update_status(9999, '进行中')

        assert result is False

    def test_update_status_invalid_order_id(self, mock_db_order):
        from models.order import OrderDAO
        result = OrderDAO.update_status(None, '进行中')

        assert result is False


# ===================== OrderDAO.delete 方法测试 =====================

class TestOrderDAODelete:
    """OrderDAO.delete 删除方法测试"""

    def test_delete_sets_cancelled_status(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.side_effect = [
            {'status': '待确认', 'order_no': 'ORD-DEL-001'},
            None,
        ]
        cursor.rowcount = 1

        from models.order import OrderDAO
        result = OrderDAO.delete(1)

        assert result is True


# ===================== OrderDAO 查询方法测试 =====================

class TestOrderDAOGetByID:
    """OrderDAO.get_by_id 查询单条方法测试"""

    def test_get_by_id_success(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.return_value = {
            'id': 1, 'order_no': 'ORD-GET-001', 'customer_name': '客户A',
            'status': '进行中', 'extra_params': '', 'is_deleted': 0,
        }

        from models.order import OrderDAO
        result = OrderDAO.get_by_id(1)

        assert result is not None
        assert result['id'] == 1
        assert result['order_no'] == 'ORD-GET-001'
        assert result['extra_params'] == {}

    def test_get_by_id_with_extra_params(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.return_value = {
            'id': 2, 'order_no': 'ORD-GET-002', 'customer_name': '客户B',
            'status': '进行中', 'is_deleted': 0,
            'extra_params': json.dumps({'表面处理方式': '抛光', '总宽': '1200mm'}),
        }

        from models.order import OrderDAO
        result = OrderDAO.get_by_id(2)

        assert result is not None
        assert result['extra_params']['表面处理方式'] == '抛光'
        assert result['表面处理方式'] == '抛光'

    def test_get_by_id_not_found(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.return_value = None

        from models.order import OrderDAO
        result = OrderDAO.get_by_id(9999)

        assert result is None


class TestOrderDAOGetUnscheduled:
    """OrderDAO.get_unscheduled 未排产订单查询测试"""

    def test_get_unscheduled_returns_list(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = [
            {'id': 1, 'order_no': 'ORD-UNS-001', 'extra_params': ''},
            {'id': 2, 'order_no': 'ORD-UNS-002', 'extra_params': ''},
        ]

        from models.order import OrderDAO
        results = OrderDAO.get_unscheduled()

        assert len(results) == 2
        assert results[0]['order_no'] == 'ORD-UNS-001'

    def test_get_unscheduled_empty(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = []

        from models.order import OrderDAO
        results = OrderDAO.get_unscheduled()

        assert results == []


class TestOrderDAOGetAll:
    """OrderDAO.get_all 列表查询方法测试"""

    def test_get_all_default(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = [
            {'id': 1, 'order_no': 'ORD-ALL-001', 'extra_params': ''},
            {'id': 2, 'order_no': 'ORD-ALL-002', 'extra_params': ''},
        ]

        from models.order import OrderDAO
        results = OrderDAO.get_all()

        assert len(results) == 2

    def test_get_all_with_status_filter(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = [
            {'id': 1, 'order_no': 'ORD-FLT-001', 'status': '待确认', 'extra_params': ''},
        ]

        from models.order import OrderDAO
        results = OrderDAO.get_all(filters={'status': '待确认'})

        assert len(results) == 1
        call_args = str(cursor.execute.call_args)
        assert '待确认' in call_args

    def test_get_all_with_keyword(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = [
            {'id': 1, 'order_no': 'ORD-KW-001', 'extra_params': ''},
        ]

        from models.order import OrderDAO
        results = OrderDAO.get_all(filters={'keyword': '不锈钢'})

        assert len(results) == 1


class TestOrderDAOGetAllPaginated:
    """OrderDAO.get_all_paginated 分页查询方法测试"""

    def test_get_all_paginated_basic(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.return_value = {'COUNT(*)': 25}
        cursor.fetchall.return_value = [
            {'id': i, 'order_no': f'ORD-P{i:03d}', 'extra_params': ''}
            for i in range(1, 11)
        ]

        from models.order import OrderDAO
        result = OrderDAO.get_all_paginated(page=1, page_size=10)

        assert result['total'] == 25
        assert result['page'] == 1
        assert result['page_size'] == 10
        assert result['total_pages'] == 3
        assert result['has_next'] is True
        assert result['has_prev'] is False
        assert len(result['data']) == 10

    def test_get_all_paginated_empty(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.return_value = {'COUNT(*)': 0}
        cursor.fetchall.return_value = []

        from models.order import OrderDAO
        result = OrderDAO.get_all_paginated(page=1, page_size=10)

        assert result['total'] == 0
        assert result['data'] == []

    def test_get_all_paginated_with_filters(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.return_value = {'COUNT(*)': 5}
        cursor.fetchall.return_value = [
            {'id': 1, 'order_no': 'ORD-PF-001', 'status': '待确认', 'extra_params': ''},
        ]

        from models.order import OrderDAO
        result = OrderDAO.get_all_paginated(filters={'status': '待确认'}, page=1, page_size=20)

        assert len(result['data']) == 1


class TestOrderDAOQuery:
    """OrderDAO 其他查询方法测试"""

    def test_get_by_status(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = [
            {'id': 1, 'order_no': 'ORD-STAT-001', 'status': '进行中'},
            {'id': 2, 'order_no': 'ORD-STAT-002', 'status': '进行中'},
        ]

        from models.order import OrderDAO
        results = OrderDAO.get_by_status('进行中')

        assert len(results) == 2

    def test_get_process_records(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = [
            {'id': 1, 'order_id': 1, 'process_name': '裁剪'},
            {'id': 2, 'order_id': 1, 'process_name': '编织'},
        ]

        from models.order import OrderDAO
        results = OrderDAO.get_process_records(1)

        assert len(results) == 2

    def test_get_shipments(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = [
            {'id': 1, 'order_id': 1, 'ship_date': '2025-01-01'},
        ]

        from models.order import OrderDAO
        results = OrderDAO.get_shipments(1)

        assert len(results) == 1

    def test_get_status_logs(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = [
            {'id': 1, 'table_name': 'orders', 'record_id': 1},
        ]

        from models.order import OrderDAO
        results = OrderDAO.get_status_logs(1)

        assert len(results) == 1

    def test_fuzzy_search(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = [
            {'id': 1, 'order_no': 'ORD-FUZZY-001', 'customer_name': '测试'},
        ]

        from models.order import OrderDAO
        results = OrderDAO.fuzzy_search('测试')

        assert len(results) == 1

    def test_get_production_order_found(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.return_value = {
            'id': 10, 'order_id': 1, 'order_no': 'WO-001',
        }

        from models.order import OrderDAO
        result = OrderDAO.get_production_order(1)

        assert result is not None
        assert result['order_no'] == 'WO-001'

    def test_get_production_order_not_found(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.return_value = None

        from models.order import OrderDAO
        result = OrderDAO.get_production_order(9999)

        assert result is None

    def test_get_archived_orders(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = [
            {'id': 1, 'order_no': 'ORD-ARC-001', 'extra_params': '', 'is_archived': 1},
        ]

        from models.order import OrderDAO
        results = OrderDAO.get_archived_orders()

        assert len(results) == 1
        assert results[0]['order_no'] == 'ORD-ARC-001'

    def test_get_archived_orders_with_keyword(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.return_value = [
            {'id': 2, 'order_no': 'ORD-ARC-002', 'extra_params': '', 'is_archived': 1},
        ]

        from models.order import OrderDAO
        results = OrderDAO.get_archived_orders(filters={'keyword': '002'})

        assert len(results) == 1


# ===================== OrderDAO 归档/取消归档测试 =====================

class TestOrderDAOArchive:
    """OrderDAO.archive_orders / unarchive_orders 测试"""

    def test_archive_by_ids(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.side_effect = [
            {'cnt': 2},
            None,
        ]
        cursor.rowcount = 2

        from models.order import OrderDAO
        result = OrderDAO.archive_orders(order_ids=[1, 2])

        assert result['archived'] == 2
        update_sql = cursor.execute.call_args_list[1][0][0]
        assert 'SET is_archived = 1' in update_sql

    def test_archive_by_ids_none_found(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.return_value = {'cnt': 0}

        from models.order import OrderDAO
        result = OrderDAO.archive_orders(order_ids=[999])

        assert result['archived'] == 0
        assert result['skipped'] == 0

    def test_archive_by_days(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.side_effect = [
            {'cutoff_date': '2025-01-01'},
            {'cnt': 3},
            None,
        ]
        cursor.rowcount = 3

        from models.order import OrderDAO
        result = OrderDAO.archive_orders(days=365)

        assert result['archived'] == 3

    def test_archive_by_days_none_found(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.side_effect = [
            {'cutoff_date': '2025-01-01'},
            {'cnt': 0},
        ]

        from models.order import OrderDAO
        result = OrderDAO.archive_orders(days=30)

        assert result['archived'] == 0

    def test_unarchive_orders(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.rowcount = 2

        from models.order import OrderDAO
        result = OrderDAO.unarchive_orders([1, 2])

        assert result['unarchived'] == 2
        update_sql = cursor.execute.call_args[0][0]
        assert 'SET is_archived = 0' in update_sql

    def test_unarchive_orders_none_affected(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.rowcount = 0

        from models.order import OrderDAO
        result = OrderDAO.unarchive_orders([999])

        assert result['unarchived'] == 0


# ===================== OrderDAO extra_params 工具方法测试 =====================

class TestOrderDAOExtraParams:
    """OrderDAO._build_extra_params / _parse_extra_params 测试"""

    def test_build_extra_params(self):
        from models.order import OrderDAO
        data = {
            'order_no': 'ORD-001',
            'customer_name': '客户',
            '表面处理方式': '抛光',
            '总宽': '1200mm',
        }
        extra = OrderDAO._build_extra_params(data)
        parsed = json.loads(extra)
        assert '表面处理方式' in parsed
        assert '总宽' in parsed
        assert 'order_no' not in parsed
        assert 'customer_name' not in parsed

    def test_build_extra_params_no_extra(self):
        from models.order import OrderDAO
        data = {'order_no': 'ORD-001', 'customer_name': '客户'}
        extra = OrderDAO._build_extra_params(data)
        assert extra == ''

    def test_build_extra_params_empty_values_skipped(self):
        from models.order import OrderDAO
        data = {
            'order_no': 'ORD-001',
            'customer_name': '客户',
            '表面处理方式': '',
        }
        extra = OrderDAO._build_extra_params(data)
        assert extra == ''

    def test_parse_extra_params_valid_json(self):
        from models.order import OrderDAO
        order = {
            'id': 1,
            'order_no': 'ORD-001',
            'extra_params': json.dumps({'表面处理方式': '抛光', '总宽': '1200mm'}),
        }
        result = OrderDAO._parse_extra_params(order)
        assert result['extra_params']['表面处理方式'] == '抛光'
        assert result['表面处理方式'] == '抛光'

    def test_parse_extra_params_empty_string(self):
        from models.order import OrderDAO
        order = {'id': 1, 'order_no': 'ORD-001', 'extra_params': ''}
        result = OrderDAO._parse_extra_params(order)
        assert result['extra_params'] == {}

    def test_parse_extra_params_missing_field(self):
        from models.order import OrderDAO
        order = {'id': 1, 'order_no': 'ORD-001'}
        result = OrderDAO._parse_extra_params(order)
        assert result['extra_params'] == {}


# ===================== OrderDAO 批量统计方法测试 =====================

class TestOrderDAOStatistics:
    """OrderDAO 批量统计方法测试"""

    def test_get_order_statistics_basic(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchone.side_effect = [
            {'id': 1, 'order_no': 'ORD-STAT-001', 'unit': '米',
             'surface_treatment': '抛光', 'extra_params': '',
             'is_deleted': 0},
            {'created_at': '2025-01-01 10:00:00'},
            {'created_at': '2025-01-10 10:00:00'},
            {'actual_start': '2025-01-02 10:00:00', 'actual_end': '2025-01-09 10:00:00'},
        ]
        cursor.fetchall.return_value = []

        from models.order import OrderDAO
        result = OrderDAO.get_order_statistics(1)

        assert result['unit'] == '米'
        assert result['production_process'] == '抛光'

    def test_get_batch_order_statistics_empty(self, mock_db_order):
        from models.order import OrderDAO
        result = OrderDAO.get_batch_order_statistics([])
        assert result == {}

    def test_get_batch_order_statistics(self, mock_db_order):
        cursor = mock_db_order['cursor']
        cursor.fetchall.side_effect = [
            [
                {'id': 1, 'unit': '米', 'extra_params': '',
                 'surface_treatment': '抛光'},
                {'id': 2, 'unit': '米', 'extra_params': '',
                 'surface_treatment': None},
            ],
            [],
            [],
            [],
            [],
        ]

        from models.order import OrderDAO
        result = OrderDAO.get_batch_order_statistics([1, 2])

        assert 1 in result
        assert 2 in result
        assert result[1]['unit'] == '米'

    def test_batch_get_order_statistics_empty(self, mock_db_order):
        from models.order import OrderDAO
        result = OrderDAO.batch_get_order_statistics([])
        assert result == {}


# ===================== 订单编号生成测试 =====================

class TestOrderNoGeneration:
    """订单编号生成功能测试"""

    def test_generate_order_no_format(self, mock_db):
        cursor = mock_db['cursor']
        cursor.fetchone.return_value = {'cnt': 99}

        try:
            from models.database import generate_order_no
        except ImportError:
            import pytest
            pytest.skip("models.database module not available")
        order_no = generate_order_no()

        assert order_no.startswith('ORD')
        assert len(order_no) >= 16

    def test_order_no_increment(self, mock_db):
        cursor = mock_db['cursor']
        cursor.fetchone.return_value = {'cnt': 100}

        try:
            from models.database import generate_order_no
        except ImportError:
            import pytest
            pytest.skip("models.database module not available")
        order_no = generate_order_no()

        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        assert order_no.startswith(f"ORD-{today}")


# ===================== 数据库连接池测试 =====================
# [F6 P9 2026-06-10] models.database.connection_pool 已归档
# TestDatabaseConnectionPool 整个 class 删除 (2026-06-10):
#   - models/database.py 现在是壳, 内部 import 仍指向 core.db
#   - core.db 目录不存在, 但 models/database.py 自身仍能导入 (项目根 core/db.py)
#   - 永久 skip 的 2 个测试无回归价值, 删 class
#   - 真实连接池覆盖在 test_storage_mysql.py (mock PooledDB)



if __name__ == '__main__':
    pytest.main([__file__, '-v'])
