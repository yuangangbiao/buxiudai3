# -*- coding: utf-8 -*-
"""测试 order_log.py - 订单日志模型（42% → 100%）"""
import pytest
from unittest.mock import patch, MagicMock


# ===================== Fixtures =====================

@pytest.fixture(autouse=True)
def mock_conn():
    """每个测试自动建立 mock 连接"""
    with patch('models.order_log.get_connection') as m:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        m.return_value = conn
        yield conn


# ===================== ORDER_ACTION 常量 =====================

class TestOrderActionConstants:

    def test_all_actions_defined(self):
        """ORDER_ACTION 包含所有标准操作"""
        from models.order_log import ORDER_ACTION
        expected_keys = [
            "CREATE", "UPDATE", "DELETE", "CONFIRM",
            "SCHEDULE", "PRODUCE", "COMPLETE", "SHIP",
            "ARCHIVE", "CANCEL"
        ]
        for key in expected_keys:
            assert key in ORDER_ACTION, f"缺少 {key}"
        assert ORDER_ACTION["CREATE"] == "创建订单"
        assert ORDER_ACTION["COMPLETE"] == "完成订单"

    def test_log_order_action_maps_via_dict(self):
        """log_order_action 通过 ORDER_ACTION 映射中文名"""
        from models.order_log import log_order_action, OrderLogDAO, ORDER_ACTION
        with patch.object(OrderLogDAO, 'create') as mock_create:
            log_order_action(1, "ORD-001", "CREATE", "张三", "创建订单")
            mock_create.assert_called_once_with(
                1, "ORD-001", ORDER_ACTION["CREATE"], "张三", "创建订单"
            )

    def test_log_order_action_fallback_to_raw_key(self):
        """字典中不存在时直接用 action_key"""
        from models.order_log import log_order_action, OrderLogDAO
        with patch.object(OrderLogDAO, 'create') as mock_create:
            log_order_action(2, "ORD-002", "UNKNOWN_ACTION")
            mock_create.assert_called_once_with(
                2, "ORD-002", "UNKNOWN_ACTION", "系统", None
            )


# ===================== OrderLogDAO.create =====================

class TestCreate:

    def test_create_success(self, mock_conn):
        """创建日志成功返回 True"""
        from models.order_log import OrderLogDAO
        from datetime import datetime

        result = OrderLogDAO.create(1, "ORD-001", "创建订单", "张三", "新订单")

        assert result is True
        mock_conn.cursor.return_value.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_create_closes_cursor_and_conn(self, mock_conn):
        """finally 中关闭游标和连接"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value

        OrderLogDAO.create(1, "ORD-001", "创建订单", "张三")

        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_create_failure_rollback(self, mock_conn):
        """异常时回滚并返回 False"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.execute.side_effect = Exception("DB error")

        result = OrderLogDAO.create(1, "ORD-001", "创建订单", "张三")

        assert result is False
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()


# ===================== OrderLogDAO.get_by_order_id =====================

class TestGetByOrderId:

    def test_get_by_order_id_returns_rows(self, mock_conn):
        """按订单ID查询返回结果"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = [{"id": 1, "action": "创建订单"}]

        result = OrderLogDAO.get_by_order_id(1)

        assert result == [{"id": 1, "action": "创建订单"}]
        cursor.execute.assert_called_once()

    def test_get_by_order_id_empty(self, mock_conn):
        """无结果返回空列表"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = []

        result = OrderLogDAO.get_by_order_id(999)
        assert result == []

    def test_get_by_order_id_error_returns_empty(self, mock_conn):
        """异常时返回空列表"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.execute.side_effect = Exception("DB error")

        result = OrderLogDAO.get_by_order_id(1)
        assert result == []

    def test_get_by_order_id_closes_resources(self, mock_conn):
        """finally 释放资源"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value

        OrderLogDAO.get_by_order_id(1)
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== OrderLogDAO.get_all =====================

class TestGetAll:

    def test_get_all_with_default_limit(self, mock_conn):
        """默认 limit=100"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]

        result = OrderLogDAO.get_all()

        assert len(result) == 2
        # 验证 SQL 有 LIMIT 100
        sql = cursor.execute.call_args[0][0]
        assert "LIMIT" in sql
        assert cursor.execute.call_args[0][1] == (100,)

    def test_get_all_custom_limit(self, mock_conn):
        """自定义 limit"""
        from models.order_log import OrderLogDAO

        OrderLogDAO.get_all(limit=50)
        assert mock_conn.cursor.return_value.execute.call_args[0][1] == (50,)

    def test_get_all_empty(self, mock_conn):
        """无日志时返回空"""
        from models.order_log import OrderLogDAO
        mock_conn.cursor.return_value.fetchall.return_value = []

        result = OrderLogDAO.get_all()
        assert result == []

    def test_get_all_error(self, mock_conn):
        """异常返回空"""
        from models.order_log import OrderLogDAO
        mock_conn.cursor.return_value.execute.side_effect = Exception("err")

        result = OrderLogDAO.get_all()
        assert result == []

    def test_get_all_closes_resources(self, mock_conn):
        """资源释放"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value

        OrderLogDAO.get_all()
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== OrderLogDAO.get_by_operator =====================

class TestGetByOperator:

    def test_get_by_operator(self, mock_conn):
        """按操作人查询"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = [{"id": 1, "operator": "张三"}]

        result = OrderLogDAO.get_by_operator("张三")
        assert result == [{"id": 1, "operator": "张三"}]

        sql, params = cursor.execute.call_args[0]
        assert "operator" in sql
        assert params[0] == "张三"

    def test_get_by_operator_default_limit(self, mock_conn):
        """默认 limit=100"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = []

        OrderLogDAO.get_by_operator("李四")
        assert cursor.execute.call_args[0][1][1] == 100

    def test_get_by_operator_custom_limit(self, mock_conn):
        """自定义 limit"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = []

        OrderLogDAO.get_by_operator("李四", limit=20)
        assert cursor.execute.call_args[0][1][1] == 20

    def test_get_by_operator_error(self, mock_conn):
        """异常返回空"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.execute.side_effect = Exception("err")

        result = OrderLogDAO.get_by_operator("张三")
        assert result == []

    def test_get_by_operator_closes_resources(self, mock_conn):
        """资源释放"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value

        OrderLogDAO.get_by_operator("张三")
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== OrderLogDAO.get_by_action =====================

class TestGetByAction:

    def test_get_by_action(self, mock_conn):
        """按操作类型查询"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = [{"id": 1, "action": "创建订单"}]

        result = OrderLogDAO.get_by_action("创建订单")
        assert result == [{"id": 1, "action": "创建订单"}]

        sql, params = cursor.execute.call_args[0]
        assert "action" in sql
        assert params[0] == "创建订单"

    def test_get_by_action_default_limit(self, mock_conn):
        """默认 limit=100"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = []

        OrderLogDAO.get_by_action("UPDATE")
        assert cursor.execute.call_args[0][1][1] == 100

    def test_get_by_action_error(self, mock_conn):
        """异常返回空"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.execute.side_effect = Exception("err")

        result = OrderLogDAO.get_by_action("DELETE")
        assert result == []

    def test_get_by_action_closes_resources(self, mock_conn):
        """资源释放"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value

        OrderLogDAO.get_by_action("CONFIRM")
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== OrderLogDAO.search =====================

class TestSearch:

    def test_search_by_order_no(self, mock_conn):
        """按订单号模糊搜索"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = [{"id": 1, "order_no": "ORD-001"}]

        result = OrderLogDAO.search("ORD-001")
        assert result == [{"id": 1, "order_no": "ORD-001"}]

        sql, params = cursor.execute.call_args[0]
        assert "LIKE" in sql
        assert all("%ORD-001%" in str(p) for p in params[:3])

    def test_search_by_operator(self, mock_conn):
        """按操作人模糊搜索"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = [{"id": 2, "operator": "张三"}]

        result = OrderLogDAO.search("张三")
        assert result == [{"id": 2, "operator": "张三"}]

    def test_search_by_details(self, mock_conn):
        """按详情模糊搜索"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = [{"id": 3, "details": "修改数量"}]

        result = OrderLogDAO.search("修改数量")
        assert result == [{"id": 3, "details": "修改数量"}]

    def test_search_no_results(self, mock_conn):
        """无匹配时返回空"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchall.return_value = []

        result = OrderLogDAO.search("不存在的")
        assert result == []

    def test_search_error(self, mock_conn):
        """异常返回空"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.execute.side_effect = Exception("err")

        result = OrderLogDAO.search("keyword")
        assert result == []

    def test_search_closes_resources(self, mock_conn):
        """资源释放"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value

        OrderLogDAO.search("test")
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# ===================== OrderLogDAO.count_by_action =====================

class TestCountByAction:

    def test_count_by_action_with_filter(self, mock_conn):
        """指定 action 统计"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchone.return_value = (5,)

        result = OrderLogDAO.count_by_action("CREATE")

        assert result == 5
        sql, params = cursor.execute.call_args[0]
        assert "WHERE action = %s" in sql
        assert params == ("CREATE",)

    def test_count_by_action_without_filter(self, mock_conn):
        """不指定 action 时分组统计"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchone.return_value = ("CREATE", 10)

        result = OrderLogDAO.count_by_action()

        sql = cursor.execute.call_args[0][0]
        assert "GROUP BY action" in sql
        # 无 action 时返回 fetchone 结果
        assert result == ("CREATE", 10)

    def test_count_with_filter_no_result(self, mock_conn):
        """有 action 但无结果"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.fetchone.return_value = None

        result = OrderLogDAO.count_by_action("DELETE")
        assert result == 0

    def test_count_error(self, mock_conn):
        """异常返回 0"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value
        cursor.execute.side_effect = Exception("err")

        result = OrderLogDAO.count_by_action("CREATE")
        assert result == 0

    def test_count_by_action_closes_resources(self, mock_conn):
        """资源释放"""
        from models.order_log import OrderLogDAO
        cursor = mock_conn.cursor.return_value

        OrderLogDAO.count_by_action("CREATE")
        cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
