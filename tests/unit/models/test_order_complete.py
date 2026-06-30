# -*- coding: utf-8 -*-
"""
models/order.py 完整单元测试

覆盖模块:
- OrderDAO
- _sync_is_archived_to_container_center
"""
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestOrderDAOFixedOrderKeys:
    """OrderDAO 固定字段测试"""

    def test_fixed_order_keys_contains_required_fields(self):
        """测试固定字段包含所有必需字段"""
        from models.order import FIXED_ORDER_KEYS

        required_fields = [
            'order_no', 'customer_name', 'customer_phone',
            'product_type', 'quantity', 'unit', 'unit_price',
            'total_amount', 'status', 'created_at'
        ]

        for field in required_fields:
            assert field in FIXED_ORDER_KEYS, f"缺少必需字段: {field}"


class TestOrderDAOBuildExtraParams:
    """OrderDAO._build_extra_params 测试"""

    def test_build_extra_params_extracts_custom_fields(self):
        """测试提取自定义字段"""
        from models.order import OrderDAO

        data = {
            'order_no': 'A001',
            'customer_name': '张三',
            'quantity': 100,
            'custom_field': '自定义值',
            'another_field': 123
        }

        result = OrderDAO._build_extra_params(data)

        assert 'custom_field' in result
        assert 'another_field' in result
        assert 'order_no' not in result
        assert 'customer_name' not in result

    def test_build_extra_params_ignores_empty_values(self):
        """测试忽略空值"""
        from models.order import OrderDAO

        data = {
            'order_no': 'A001',
            'customer_name': '张三',
            'empty_field': '',
            'none_field': None
        }

        result = OrderDAO._build_extra_params(data)

        assert 'empty_field' not in result
        assert 'none_field' not in result

    def test_build_extra_params_returns_empty_string_when_no_extra(self):
        """测试无额外字段时返回空字符串"""
        from models.order import OrderDAO

        data = {
            'order_no': 'A001',
            'customer_name': '张三',
            'quantity': 100
        }

        result = OrderDAO._build_extra_params(data)

        assert result == ""


class TestOrderDAOCreate:
    """OrderDAO.create 测试"""

    @patch('models.order.log_order_action')
    @patch('models.order.log_status_change')
    @patch('models.order.generate_order_no')
    @patch('models.order.get_connection')
    def test_create_order_success(self, mock_get_conn, mock_gen_order_no, mock_log_status, mock_log_action):
        """测试创建订单成功"""
        from models.order import OrderDAO

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn
        mock_gen_order_no.return_value = 'ORD20240001'

        data = {
            'customer_name': '张三',
            'customer_phone': '13800138000',
            'product_type': '不锈钢网带',
            'quantity': '100',
            'unit_price': '10.5',
            'material': '304'
        }

        result = OrderDAO.create(data)

        assert result == 1
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called()

    @patch('models.order.log_order_action')
    @patch('models.order.log_status_change')
    @patch('models.order.generate_order_no')
    @patch('models.order.get_connection')
    def test_create_order_with_custom_order_no(self, mock_get_conn, mock_gen_order_no, mock_log_status, mock_log_action):
        """测试使用自定义订单号创建订单"""
        from models.order import OrderDAO

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        data = {
            'order_no': 'CUSTOM001',
            'customer_name': '张三',
            'quantity': '50'
        }

        result = OrderDAO.create(data)

        assert result == 1
        mock_gen_order_no.assert_not_called()

    @patch('models.order.get_connection')
    def test_create_order_connects_and_closes(self, mock_get_conn):
        """测试创建订单时连接和关闭"""
        from models.order import OrderDAO

        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        with patch('models.order.log_order_action'):
            with patch('models.order.log_status_change'):
                with patch('models.order.generate_order_no', return_value='TEST001'):
                    data = {'customer_name': '张三', 'quantity': '10'}

                    OrderDAO.create(data)

        mock_conn.close.assert_called()


class TestOrderDAOUpdate:
    """OrderDAO.update 测试"""

    @patch('models.order.log_order_action')
    @patch('models.order.log_status_change')
    @patch('models.order.get_connection')
    def test_update_order_success(self, mock_get_conn, mock_log_status, mock_log_action):
        """测试更新订单成功"""
        from models.order import OrderDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {'status': '待确认'},  # 第一次查询
            {'order_no': 'ORD001'}  # 第二次查询
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        data = {
            'customer_name': '李四',
            'quantity': '200',
            'unit_price': '15'
        }

        result = OrderDAO.update(1, data)

        assert result is True
        mock_conn.commit.assert_called()

    @patch('models.order.log_order_action')
    @patch('models.order.log_status_change')
    @patch('models.order.get_connection')
    def test_update_order_with_status_change(self, mock_get_conn, mock_log_status, mock_log_action):
        """测试状态变更时记录日志"""
        from models.order import OrderDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {'status': '待确认'},  # 查询当前状态
            {'order_no': 'ORD001'}  # 查询订单号
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        data = {
            'customer_name': '王五',
            'status': '已确认'
        }

        result = OrderDAO.update(1, data)

        assert result is True
        mock_log_status.assert_called_once()
        mock_log_action.assert_called()

    @patch('models.order.get_connection')
    def test_update_order_rollback_on_error(self, mock_get_conn):
        """测试错误时回滚"""
        from models.order import OrderDAO

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        data = {'customer_name': '测试'}

        result = OrderDAO.update(1, data)

        assert result is False
        mock_conn.rollback.assert_called()


class TestOrderDAOUpdateStatus:
    """OrderDAO.update_status 测试"""

    @patch('models.order.log_order_action')
    @patch('models.order.log_status_change')
    @patch('models.order.get_connection')
    def test_update_status_success(self, mock_get_conn, mock_log_status, mock_log_action):
        """测试更新状态成功"""
        from models.order import OrderDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {'status': '待确认'},  # 查询当前状态
            {'order_no': 'ORD001'}  # 查询订单号
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = OrderDAO.update_status(1, '已确认')

        assert result is True
        mock_conn.commit.assert_called()

    @patch('models.order.get_connection')
    def test_update_status_with_invalid_id(self, mock_get_conn):
        """测试无效ID"""
        from models.order import OrderDAO

        result = OrderDAO.update_status(0, '已确认')

        assert result is False
        mock_get_conn.assert_not_called()

    @patch('models.order.get_connection')
    def test_update_status_order_not_found(self, mock_get_conn):
        """测试订单不存在"""
        from models.order import OrderDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = OrderDAO.update_status(999, '已确认')

        assert result is False


class TestOrderDAODelete:
    """OrderDAO.delete 测试"""

    @patch('models.order.OrderDAO.update_status')
    def test_delete_order_calls_update_status(self, mock_update_status):
        """测试删除调用状态更新"""
        from models.order import OrderDAO

        mock_update_status.return_value = True

        result = OrderDAO.delete(1)

        assert result is True
        mock_update_status.assert_called_once_with(1, '已取消')


class TestOrderDAOParseExtraParams:
    """OrderDAO._parse_extra_params 测试"""

    def test_parse_extra_params_with_json(self):
        """测试解析JSON格式的额外参数"""
        from models.order import OrderDAO

        order = {
            'order_no': 'A001',
            'extra_params': '{"custom_field": "value", "another": 123}'
        }

        result = OrderDAO._parse_extra_params(order)

        assert result['extra_params'] == {'custom_field': 'value', 'another': 123}
        assert result['custom_field'] == 'value'
        assert result['another'] == 123

    def test_parse_extra_params_with_empty_string(self):
        """测试空字符串"""
        from models.order import OrderDAO

        order = {
            'order_no': 'A001',
            'extra_params': ''
        }

        result = OrderDAO._parse_extra_params(order)

        assert result['extra_params'] == {}

    def test_parse_extra_params_with_invalid_json(self):
        """测试无效JSON"""
        from models.order import OrderDAO

        order = {
            'order_no': 'A001',
            'extra_params': 'not valid json'
        }

        result = OrderDAO._parse_extra_params(order)

        assert result['extra_params'] == {}

    def test_parse_extra_params_expands_to_order(self):
        """测试展开到订单字段"""
        from models.order import OrderDAO

        order = {
            'order_no': 'A001',
            'extra_params': '{"mesh_width": 1000, "surface_treatment": "镀锌"}'
        }

        result = OrderDAO._parse_extra_params(order)

        assert result['mesh_width'] == 1000
        assert result['surface_treatment'] == '镀锌'


class TestOrderDAOGetUnscheduled:
    """OrderDAO.get_unscheduled 测试"""

    @patch('models.order.get_connection')
    def test_get_unscheduled_returns_list(self, mock_get_conn):
        """测试获取未排产订单列表"""
        from models.order import OrderDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'order_no': 'ORD001', 'extra_params': ''},
            {'id': 2, 'order_no': 'ORD002', 'extra_params': '{"custom": "val"}'}
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = OrderDAO.get_unscheduled()

        assert isinstance(result, list)
        assert len(result) == 2


class TestOrderDAOGetById:
    """OrderDAO.get_by_id 测试"""

    @patch('models.order.get_connection')
    def test_get_by_id_success(self, mock_get_conn):
        """测试根据ID获取订单成功"""
        from models.order import OrderDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'order_no': 'ORD001',
            'customer_name': '张三',
            'extra_params': ''
        }

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = OrderDAO.get_by_id(1)

        assert result is not None
        assert result['id'] == 1
        assert result['order_no'] == 'ORD001'

    @patch('models.order.get_connection')
    def test_get_by_id_not_found(self, mock_get_conn):
        """测试根据ID获取订单不存在"""
        from models.order import OrderDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = OrderDAO.get_by_id(999)

        assert result is None


class TestSyncArchivedToContainerCenter:
    """_sync_is_archived_to_container_center 测试"""

    @pytest.mark.skip(reason="外部依赖，集成测试场景")
    def test_sync_success(self):
        """测试同步归档状态成功 - 需要真实的container_center数据库"""
        pass

    @pytest.mark.skip(reason="外部依赖，集成测试场景")
    def test_sync_no_orders(self):
        """测试同步时没有订单 - 需要真实的container_center数据库"""
        pass

    @pytest.mark.skip(reason="外部依赖，集成测试场景")
    def test_sync_error_returns_zero(self):
        """测试同步出错时返回0 - 需要真实的container_center数据库"""
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
