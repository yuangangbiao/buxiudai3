# -*- coding: utf-8 -*-
"""
models/order.py OrderDAO 覆盖率缺口补充测试

按 ROI 优先级排列：
  第一优先级：_parse_extra_params, get_kanban_stats, get_all,
             get_archived_orders, unarchive_orders
  第二优先级：get_all_paginated, archive_orders, get_dashboard_order_stats

模式（参见 test_order_dao_complete.py）：
  setup 删除 models.order 模块缓存，每个测试方法内先 patch 再 import OrderDAO。
"""
import json
import sys
import pytest
from unittest.mock import patch, MagicMock


def _setup_mocks():
    """创建 mock connection 和 cursor 对，并删除模块缓存"""
    for m in list(sys.modules.keys()):
        if m.startswith('models.order'):
            del sys.modules[m]
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit.return_value = None
    return mock_conn, mock_cursor


def _patch(patchers, mock_conn):
    """启动 patch，返回 patcher 列表以便 stop

    此函数只做底层 connection_pool 的 patch；对 models.database 和
    models.order 的 patch 由 _patch_imported_order 完成。

    注意：不能只 patch 顶层，因为 models.order 使用了
    ``from models.database import get_connection``，
    Python 在导入时会将引用复制到 order 模块的命名空间中，
    此后无论怎样 patch database 模块，order 持有的引用都不会变化。
    """
    p = patch('models.database.connection_pool.get_connection', return_value=mock_conn)
    p.start()
    patchers.append(p)

    # 同时 patch __init__.py 的 re-export（可选，但能覆盖直接 from models.database import）
    import models.database
    p2 = patch.object(models.database, 'get_connection', return_value=mock_conn)
    p2.start()
    patchers.append(p2)


def _evict_order_module():
    """从 sys.modules 中移除 models.order 缓存，确保下次 import 拿到新模块"""
    for m in list(sys.modules.keys()):
        if m.startswith('models.order'):
            del sys.modules[m]


def _patch_and_import_order(patchers, mock_conn):
    """删除模块缓存 → patch → 重新 import OrderDAO"""
    _evict_order_module()
    _patch(patchers, mock_conn)
    from models.order import OrderDAO
    # import 后直接 patch order 模块自己的 get_connection 引用
    import models.order
    p3 = patch.object(models.order, 'get_connection', return_value=mock_conn)
    p3.start()
    patchers.append(p3)
    return OrderDAO


# ============================================================
#  第一优先级 — P1
# ============================================================

class TestParseExtraParams:
    """
    _parse_extra_params (L250-265, 当前 50%)

    Branch 矩阵:
      1. raw 为空字符串 → else: extra_params = {}
      2. raw 为有效 JSON → json.loads 成功, 展开 key
      3. raw 为无效 JSON → json.JSONDecodeError → extra_params = {}
      4. raw 为 TypeError 异常 → extra_params = {}
      5. 展开时 key 已存在且非空 → 不覆盖
      6. 展开时 key 不存在或为空 → 覆盖写入
    """

    def test_empty_raw(self):
        """空字符串 → extra_params = {}"""
        from models.order import OrderDAO
        order = {"id": 1, "extra_params": ""}
        result = OrderDAO._parse_extra_params(order)
        assert result["extra_params"] == {}
        assert "id" in result

    def test_valid_json(self):
        """有效 JSON → 解析并展开"""
        from models.order import OrderDAO
        order = {"id": 1, "extra_params": '{"总宽": "1.2m", "表面处理": "抛光"}'}
        result = OrderDAO._parse_extra_params(order)
        assert result["extra_params"]["总宽"] == "1.2m"
        assert result["extra_params"]["表面处理"] == "抛光"
        assert result["总宽"] == "1.2m"

    def test_invalid_json(self):
        """无效 JSON → json.JSONDecodeError → extra_params = {}"""
        from models.order import OrderDAO
        order = {"id": 2, "extra_params": "not,json{broken"}
        result = OrderDAO._parse_extra_params(order)
        assert result["extra_params"] == {}

    def test_type_error_raw(self):
        """非字符串 raw → TypeError → extra_params = {}"""
        from models.order import OrderDAO
        order = {"id": 3, "extra_params": 12345}
        result = OrderDAO._parse_extra_params(order)
        assert result["extra_params"] == {}

    def test_skip_existing_nonempty_key(self):
        """展开时 key 已存在且非空 → 不覆盖"""
        from models.order import OrderDAO
        order = {
            "id": 4,
            "customer_name": "张三",
            "extra_params": '{"customer_name": "李四", "新字段": "val"}'
        }
        result = OrderDAO._parse_extra_params(order)
        assert result["customer_name"] == "张三"  # 不覆盖
        assert result["新字段"] == "val"  # 新字段写入

    def test_override_empty_existing_key(self):
        """展开时 key 存在但为空 → 覆盖写入"""
        from models.order import OrderDAO
        order = {
            "id": 5,
            "customer_name": "",
            "extra_params": '{"customer_name": "auto_filled", "新字段": "val"}'
        }
        result = OrderDAO._parse_extra_params(order)
        assert result["customer_name"] == "auto_filled"


class TestGetKanbanStats:
    """
    get_kanban_stats (L493-506, 当前 43%)

    Branch 矩阵:
      1. 正常返回统计 dict
      2. 空数据（fetchall 返回 []）
      3. finally 关闭连接
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self._patchers = []
        _evict_order_module()
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        yield
        for p in self._patchers:
            p.stop()

    def test_normal(self):
        """正常返回 {status: count} 字典"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = [
            ("进行中", 10), ("已下单", 5)
        ]
        result = OrderDAO.get_kanban_stats()
        assert result == {"进行中": 10, "已下单": 5}

    def test_empty(self):
        """无数据 → 空字典"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = []
        result = OrderDAO.get_kanban_stats()
        assert result == {}

    def test_finally_closes_connection(self):
        """验证 finally 关闭连接"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = []
        OrderDAO.get_kanban_stats()
        self.mock_conn.close.assert_called_once()


class TestGetAll:
    """
    get_all (L305-352, 当前 77%)

    缺失的 11 行主要在 filters 分支未被覆盖:
      - 无 filters → 自动排除已完成/已归档/已取消
      - filters 带各条件组合
      - keyword 分支 (L332-343)
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self._patchers = []
        _evict_order_module()
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        yield
        for p in self._patchers:
            p.stop()

    def _make_result(self, id_val=1):
        return [{"id": id_val, "extra_params": ""}]

    def test_no_filters(self):
        """无 filters → 自动排除已完成/已归档/已取消"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_all()
        assert len(result) == 1
        sql_executed = self.mock_cursor.execute.call_args[0][0]
        assert "NOT IN" in sql_executed

    def test_filters_status_specific(self):
        """filters.status = '进行中'"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_all(filters={"status": "进行中"})
        assert len(result) == 1

    def test_filters_customer_name(self):
        """filters.customer_name"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_all(filters={"customer_name": "张三"})
        assert len(result) == 1

    def test_filters_product_type_all(self):
        """filters.product_type = '全部' → 忽略这个 filter"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_all(filters={"product_type": "全部"})
        assert len(result) == 1

    def test_filters_product_type_specific(self):
        """filters.product_type = '不锈钢网带'"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_all(filters={"product_type": "不锈钢网带"})
        assert len(result) == 1

    def test_filters_date_range(self):
        """filters.date_from + date_to"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_all(filters={
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        })
        assert len(result) == 1
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "delivery_date >=" in sql
        assert "delivery_date <=" in sql

    def test_filters_keyword(self):
        """filters.keyword → 多字段模糊搜索"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_all(filters={"keyword": "测试"})
        assert len(result) == 1
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "extra_params LIKE" in sql

    def test_filters_combined(self):
        """组合条件: status + keyword + product_type"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_all(filters={
            "status": "进行中",
            "keyword": "test",
            "product_type": "网带",
        })
        assert len(result) == 1

    def test_filters_combined_all(self):
        """全组合: status + customer_name + product_type + date + keyword"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_all(filters={
            "status": "进行中",
            "customer_name": "张",
            "product_type": "网带",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "keyword": "test",
        })
        assert len(result) == 1

    def test_filters_status_all(self):
        """filters.status = '全部' → 不用排除"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_all(filters={"status": "全部"})
        assert len(result) == 1
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "NOT IN" not in sql

    def test_filters_empty_dict(self):
        """filters = {}（空字典但非 None）→ 自动排除"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_all(filters={})
        assert len(result) == 1
        sql = self.mock_cursor.execute.call_args[0][0]
        assert "NOT IN" in sql


class TestGetArchivedOrders:
    """
    get_archived_orders (L1083-1124, 当前 83%)

    缺失 7 行: keyword, customer_name, product_type 过滤分支
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self._patchers = []
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        yield
        for p in self._patchers:
            p.stop()

    def _make_result(self):
        return [{"id": 1, "is_archived": 1, "extra_params": ""}]

    def _patch_and_import(self):
        _patch(self._patchers, self.mock_conn)
        from models.order import OrderDAO
        return OrderDAO

    def test_no_filters(self):
        """无 filters → 基础 SQL"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_archived_orders()
        assert len(result) == 1

    def test_keyword_filter(self):
        """keyword 过滤"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_archived_orders(filters={"keyword": "测试"})
        assert len(result) == 1

    def test_customer_name_filter(self):
        """customer_name 过滤"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_archived_orders(filters={"customer_name": "张三"})
        assert len(result) == 1

    def test_product_type_filter(self):
        """product_type 过滤"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_archived_orders(filters={"product_type": "网带"})
        assert len(result) == 1

    def test_combined_filters(self):
        """所有过滤条件组合"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = self._make_result()
        result = OrderDAO.get_archived_orders(filters={
            "keyword": "测试",
            "customer_name": "张",
            "product_type": "网带",
        })
        assert len(result) == 1


class TestUnarchiveOrders:
    """
    unarchive_orders (L1044-1080, 当前 62%)

    缺失:
      - 正常取消归档
      - SQL 异常 → 回滚 + 返回 error
      - 空 order_ids → SQL 异常 (placeholder 空)
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self._patchers = []
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        yield
        for p in self._patchers:
            p.stop()

    def _patch_and_import(self):
        _patch(self._patchers, self.mock_conn)
        from models.order import OrderDAO
        return OrderDAO

    def test_normal(self):
        """正常取消归档"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.rowcount = 2
        result = OrderDAO.unarchive_orders([1, 2])
        assert result["unarchived"] == 2
        self.mock_conn.commit.assert_called_once()

    def test_no_rows_affected(self):
        """无匹配行"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.rowcount = 0
        result = OrderDAO.unarchive_orders([999])
        assert result["unarchived"] == 0

    def test_exception(self):
        """SQL 异常 → 回滚 + 返回 error"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.execute.side_effect = Exception("DB error")
        result = OrderDAO.unarchive_orders([1])
        assert result["unarchived"] == 0
        assert "error" in result
        assert "DB error" in result["error"]
        self.mock_conn.rollback.assert_called_once()

    def test_finally_closes_connection(self):
        """验证 finally 关闭连接"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.rowcount = 0
        OrderDAO.unarchive_orders([1])
        self.mock_conn.close.assert_called_once()


# ============================================================
#  第二优先级 — P2
# ============================================================

class TestGetAllPaginated:
    """
    get_all_paginated (L392-490, 当前 73%)

    缺失 27 行: filters 分支 (status, customer_name, product_type,
    date_from, date_to, keyword) + count_row 解析 + max_total
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self._patchers = []
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        yield
        for p in self._patchers:
            p.stop()

    def _mock_count(self, total=100):
        self.mock_cursor.fetchone.return_value = {"COUNT(*)": total}

    def _mock_both(self, data_list, total=100):
        self.mock_cursor.fetchall.return_value = data_list
        self.mock_cursor.fetchone.return_value = {"COUNT(*)": total}

    def _patch_and_import(self):
        _patch(self._patchers, self.mock_conn)
        from models.order import OrderDAO
        return OrderDAO

    def test_default_no_filters(self):
        """默认: 无筛选, 第1页"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self._mock_both([{"id": 1, "extra_params": ""}], total=50)
        result = OrderDAO.get_all_paginated()
        assert result["total"] == 50
        assert result["page"] == 1
        assert len(result["data"]) == 1

    def test_status_filter(self):
        """status 过滤"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self._mock_both([{"id": 1, "extra_params": ""}])
        result = OrderDAO.get_all_paginated(filters={"status": "进行中"})
        assert len(result["data"]) == 1

    def test_customer_name_filter(self):
        """customer_name 过滤"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self._mock_both([{"id": 1, "extra_params": ""}])
        result = OrderDAO.get_all_paginated(filters={"customer_name": "张三"})
        assert len(result["data"]) == 1

    def test_product_type_filter(self):
        """product_type 过滤"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self._mock_both([{"id": 1, "extra_params": ""}])
        result = OrderDAO.get_all_paginated(filters={"product_type": "不锈钢网带"})
        assert len(result["data"]) == 1

    def test_date_range_filter(self):
        """date_from + date_to 过滤"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self._mock_both([{"id": 1, "extra_params": ""}])
        result = OrderDAO.get_all_paginated(filters={
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
        })
        assert len(result["data"]) == 1

    def test_keyword_filter(self):
        """keyword 过滤"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self._mock_both([{"id": 1, "extra_params": ""}])
        result = OrderDAO.get_all_paginated(filters={"keyword": "测试"})
        assert len(result["data"]) == 1
        sql = self.mock_cursor.execute.call_args_list[0][0][0]
        assert "o.order_no LIKE" in sql

    def test_all_filters_combined(self):
        """全条件组合"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self._mock_both([{"id": 1, "extra_params": ""}])
        result = OrderDAO.get_all_paginated(filters={
            "status": "进行中",
            "customer_name": "张",
            "product_type": "网带",
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "keyword": "test",
        })
        assert len(result["data"]) == 1

    def test_page_2(self):
        """第2页"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self._mock_both([{"id": 21, "extra_params": ""}], total=100)
        result = OrderDAO.get_all_paginated(page=2, page_size=20)
        assert result["page"] == 2
        assert result["has_next"] is True
        assert result["has_prev"] is True

    def test_max_total_clamp(self):
        """max_total 保护"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self._mock_both([{"id": 1, "extra_params": ""}], total=50000)
        result = OrderDAO.get_all_paginated(max_total=1000)
        assert result["total"] == 1000

    def test_count_row_tuple_fallback(self):
        """count_row 是 tuple 时的 fallback"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = [{"id": 1, "extra_params": ""}]
        self.mock_cursor.fetchone.return_value = (50,)
        result = OrderDAO.get_all_paginated()
        assert result["total"] == 50

    def test_no_rows(self):
        """无结果"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = []
        self.mock_cursor.fetchone.return_value = {"COUNT(*)": 0}
        result = OrderDAO.get_all_paginated()
        assert result["total"] == 0
        assert result["data"] == []
        assert result["has_next"] is False


class TestArchiveOrders:
    """
    archive_orders (L966-1041, 当前 63%)

    Branch 矩阵:
      1. order_ids 指定, count > 0 → 正常归档
      2. order_ids 指定, count == 0 → 返回 skipped
      3. order_ids = None, 按 days 查, count > 0 → 按时间归档
      4. order_ids = None, count == 0 → 返回 skipped
      5. SQL 异常 → 回滚 + 返回 error
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self._patchers = []
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        yield
        for p in self._patchers:
            p.stop()

    def _patch_and_import(self):
        _patch(self._patchers, self.mock_conn)
        from models.order import OrderDAO
        return OrderDAO

    def test_by_ids_normal(self):
        """指定 order_ids, count > 0 → 更新"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.return_value = {"cnt": 5}
        self.mock_cursor.rowcount = 5
        result = OrderDAO.archive_orders(order_ids=[1, 2, 3])
        assert result["archived"] == 5
        self.mock_conn.commit.assert_called_once()

    def test_by_ids_zero_count(self):
        """指定 order_ids, count == 0 → 快速返回"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.return_value = {"cnt": 0}
        result = OrderDAO.archive_orders(order_ids=[999])
        assert result["archived"] == 0
        assert result["skipped"] == 0
        # 只有 COUNT 查询，没有 UPDATE
        assert self.mock_cursor.execute.call_count == 1

    def test_by_days_normal(self):
        """按 days 查, count > 0 → 按时间归档"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"cutoff_date": "2024-01-01"},
            {"cnt": 3},
        ]
        self.mock_cursor.rowcount = 3
        result = OrderDAO.archive_orders(days=365)
        assert result["archived"] == 3

    def test_by_days_zero_count(self):
        """按 days 查, count == 0 → 快速返回"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"cutoff_date": "2024-01-01"},
            {"cnt": 0},
        ]
        result = OrderDAO.archive_orders(days=365)
        assert result["archived"] == 0
        assert result["skipped"] == 0

    def test_exception(self):
        """SQL 异常 → 回滚 + 返回 error"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.return_value = {"cnt": 5}

        # 第1次 execute = COUNT; 第2次 execute = UPDATE → 抛异常
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Archive error")
            return MagicMock()

        self.mock_cursor.execute.side_effect = side_effect
        result = OrderDAO.archive_orders(order_ids=[1, 2])
        assert result["archived"] == 0
        assert "error" in result
        self.mock_conn.rollback.assert_called_once()

    def test_finally_closes_connection_on_error(self):
        """异常时 finally 依然关闭连接"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.return_value = {"cnt": 5}

        def side_effect(*args, **kwargs):
            raise Exception("Boom")

        self.mock_cursor.execute.side_effect = side_effect
        OrderDAO.archive_orders(order_ids=[1])
        self.mock_conn.close.assert_called_once()


class TestGetDashboardOrderStats:
    """
    get_dashboard_order_stats (L1131-1207, 当前 70%)

    Branch 矩阵:
      1. 正常返回完整统计
      2. 空数据 (total=0 → completionRate=0)
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self._patchers = []
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        yield
        for p in self._patchers:
            p.stop()

    def _patch_and_import(self):
        _patch(self._patchers, self.mock_conn)
        from models.order import OrderDAO
        return OrderDAO

    def test_normal(self):
        """正常返回完整统计"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        # 6 次 fetchone 调用
        self.mock_cursor.fetchone.side_effect = [
            {"total": 50},   # 0: totalOrders
            {"total": 10},   # 1: monthlyNew
            {"count": 20},   # 2: producingOrders
            {"count": 5},    # 3: readyToShip
            {"count": 3},    # 4: overdue
            {"total": 15},   # 5: completed
        ]
        self.mock_cursor.fetchall.side_effect = [
            [{"status": "待确认", "count": 10}, {"status": "进行中", "count": 20}],
        ]

        result = OrderDAO.get_dashboard_order_stats()
        assert result["totalOrders"] == 50
        assert result["monthlyNew"] == 10
        assert result["statusDistribution"] == {"待确认": 10, "进行中": 20}
        assert result["producingOrders"] == 20
        assert result["readyToShip"] == 5
        assert result["overdueOrders"] == 3
        assert result["completedCount"] == 15
        assert result["completionRate"] == 30.0  # 15/50*100

        self.mock_conn.close.assert_called_once()

    def test_empty(self):
        """空数据 → total=0 → completionRate=0"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"total": 0},   # totalOrders
            {"total": 0},   # monthlyNew
            {"count": 0},   # producingOrders
            {"count": 0},   # readyToShip
            {"count": 0},   # overdue
            {"total": 0},   # completed
        ]
        self.mock_cursor.fetchall.side_effect = [[]]

        result = OrderDAO.get_dashboard_order_stats()
        assert result["totalOrders"] == 0
        assert result["completionRate"] == 0.0

    def test_finally_closes_connection(self):
        """验证 finally 关闭连接"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"total": 10},
            {"total": 0},
            {"count": 0},
            {"count": 0},
            {"count": 0},
            {"total": 0},
        ]
        self.mock_cursor.fetchall.side_effect = [[]]
        OrderDAO.get_dashboard_order_stats()
        self.mock_conn.close.assert_called_once()
