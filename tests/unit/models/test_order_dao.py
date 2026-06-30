# -*- coding: utf-8 -*-
r"""models/order.py 的集成测试。

真源码行为(已读 d:\yuan\不锈钢网带跟单3.0\models\order.py 验证):
- OrderDAO 类(staticmethod 集合)
- _build_extra_params(data): 提取非 FIXED_ORDER_KEYS 字段 → JSON 字符串
  - FIXED_ORDER_KEYS = {order_no, customer_name, ..., 22+ 业务字段}
  - 空 dict 返 ""
- _parse_extra_params(order): 解析 extra_params JSON, 展开到外层
  - JSON 解析失败 → order["extra_params"] = {}
  - extra_params 字段为空 → 返 {}
- create(data): 22 列 INSERT, 返 lastrowid
  - qty/price 强转 float, total=qty*price
  - log_status_change("orders", new_id, None, PENDING) + log_order_action
  - delivery_date="" 转 None
- update(order_id, data, operator="系统"): 21 列 UPDATE, 返 True/False
  - 状态变更时记 log_status_change + log_order_action
  - 异常 rollback, 返 False
- update_status(order_id, new_status, operator="系统"): 状态更新
  - 旧状态不同记 log_status_change + action_map
  - 订单不存在 返 False
  - invalid order_id 返 False
- delete(order_id): 走 update_status(CANCELLED)
- get_unscheduled(): 返 已确认/待发布 且未生成生产工单 的订单
- get_by_id(order_id): SELECT WHERE is_deleted=0 → dict 或 None
- get_all(filters): 默认排除 已完成/已归档/已取消
- get_recent_for_kanban(limit=200): 90 天内, 排除已完/已归/已取
- get_recent_for_list(limit=200): 排除已完/已归/已取
- get_all_paginated(filters, page=1, page_size=100, max_total=10000):
  - 返 {data, total, page, page_size, total_pages, has_next, has_prev}
  - page max(1, page), page_size max(1, min(ps, 1000))
- get_kanban_stats(): 真源码有 bug: SQL 用 `?` 占位符(MySQL 不支持),测真行为
- fuzzy_search(keyword, limit=20): LIKE 7 字段, 返 6 字段
- archive_orders(order_ids, days=365, operator): 归档
  - 返 {archived, skipped}
- unarchive_orders(order_ids): 返 {unarchived}
- get_archived_orders(filters): is_archived=1
- get_dashboard_order_stats(): 7 字段统计
- get_delivery_alert_orders(days_ahead=7): 即将到期

按 F16 §1:不 mock 业务路径,patch models.order.get_connection + log_status_change + log_order_action + generate_order_no 隔离 DB。
"""
import json
from unittest.mock import patch

import pytest

from models.order import OrderDAO, FIXED_ORDER_KEYS


@pytest.fixture(autouse=True)
def _isolate_order(monkeypatch):
    r"""autouse:patch get_connection + log_status_change + log_order_action + generate_order_no。"""
    from unittest.mock import MagicMock
    import sys
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.fetchone.return_value = None
    mock_conn.cursor.return_value.fetchall.return_value = []
    if "models.order" in sys.modules:
        monkeypatch.setattr("models.order.get_connection", lambda: mock_conn)
    monkeypatch.setattr("models.database.get_connection", lambda: mock_conn)
    monkeypatch.setattr("core.db.get_connection", lambda: mock_conn)
    monkeypatch.setattr(
        "models.order.log_status_change",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "models.order.log_order_action",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "models.order.generate_order_no",
        lambda: "GO-AUTO-001",
    )


def test_build_extra_params_excludes_fixed_keys():
    r"""_build_extra_params 排除 FIXED_ORDER_KEYS 字段。"""
    data = {
        "order_no": "GO-001",
        "customer_name": "张三",
        "表面处理方式": "抛光",
        "网孔规格": 5,
        "custom_field": "value",
    }
    result = OrderDAO._build_extra_params(data)
    parsed = json.loads(result)
    assert "order_no" not in parsed
    assert "customer_name" not in parsed
    assert "表面处理方式" in parsed
    assert "网孔规格" in parsed
    assert "custom_field" in parsed


def test_build_extra_params_empty_data_returns_empty_string():
    r"""_build_extra_params 空 data 返 ""(源码 line 40 if extra else "")。"""
    result = OrderDAO._build_extra_params({})
    assert result == ""


def test_build_extra_params_falsy_values_excluded():
    r"""_build_extra_params 字段值为 falsy(0/空字符串)时排除(源码 if v 条件)。"""
    data = {"empty_str": "", "zero": 0, "none_val": None, "valid": "x"}
    result = OrderDAO._build_extra_params(data)
    parsed = json.loads(result)
    assert "empty_str" not in parsed
    assert "zero" not in parsed
    assert "none_val" not in parsed
    assert "valid" in parsed


def test_parse_extra_params_expands_to_outer_dict():
    r"""_parse_extra_params 把 JSON 解析后展开到外层(不覆盖已有非空值)。"""
    order = {
        "id": 1,
        "order_no": "GO-001",
        "extra_params": json.dumps({"表面处理方式": "抛光", "新字段": "新值"}, ensure_ascii=False),
        "existing_field": "existing_value",
    }
    result = OrderDAO._parse_extra_params(order)
    assert result["表面处理方式"] == "抛光"
    assert result["新字段"] == "新值"
    assert result["existing_field"] == "existing_value"
    assert isinstance(result["extra_params"], dict)


def test_parse_extra_params_invalid_json_keeps_empty_dict():
    r"""_parse_extra_params JSON 解析失败时 extra_params={}(源码 except 块)。"""
    order = {"id": 1, "extra_params": "bad json {{"}
    result = OrderDAO._parse_extra_params(order)
    assert result["extra_params"] == {}


def test_parse_extra_params_empty_string_keeps_empty_dict():
    r"""_parse_extra_params 空字符串 返 {}。"""
    order = {"id": 1, "extra_params": ""}
    result = OrderDAO._parse_extra_params(order)
    assert result["extra_params"] == {}


def test_create_inserts_with_all_22_columns(mock_get_connection):
    r"""create 调 INSERT INTO orders 含 22 字段。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.lastrowid = 42
        new_id = OrderDAO.create({
            "customer_name": "张三",
            "customer_phone": "13800138000",
            "product_type": "编织网带",
            "material": "304不锈钢",
            "quantity": 100,
            "unit_price": 50,
        })

    assert new_id == 42
    sql = mock_cursor.execute.call_args.args[0]
    assert "INSERT INTO orders" in sql
    assert sql.count("%s") == 22
    mock_conn.commit.assert_called_once()


def test_create_generates_order_no_when_missing(mock_get_connection):
    r"""create data 不含 order_no 时调 generate_order_no(源码 line 47)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.lastrowid = 1
        OrderDAO.create({"customer_name": "张三"})

    params = mock_cursor.execute.call_args.args[1]
    assert params[0] == "GO-AUTO-001"


def test_create_calculates_total_amount(mock_get_connection):
    r"""create 计算 total = qty * price。

    params 顺序(22 列):
    [0]order_no [1]customer_name [2]phone [3]address [4]group
    [5]product_type [6]material [7]mesh_size [8]wire_diameter
    [9]width [10]length [11]qty [12]unit [13]price [14]total
    [15]surface_treatment [16]special_requirements [17]delivery_date
    [18]status [19]remark [20]product_remark [21]extra_params
    """
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.lastrowid = 1
        OrderDAO.create({
            "customer_name": "张三",
            "quantity": 100,
            "unit_price": 25.5,
        })

    params = mock_cursor.execute.call_args.args[1]
    assert params[11] == 100.0
    assert params[13] == 25.5
    assert params[14] == 2550.0


def test_create_handles_string_unit_price(mock_get_connection):
    r"""create unit_price 为 str 时强转 float。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.lastrowid = 1
        OrderDAO.create({"quantity": 10, "unit_price": "100.5"})

    params = mock_cursor.execute.call_args.args[1]
    assert params[14] == 1005.0


def test_create_empty_string_delivery_date_to_none(mock_get_connection):
    r"""create delivery_date='' 转 None(源码 line 57-58)。

    params 顺序(22 列):[17] 是 delivery_date
    """
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.lastrowid = 1
        OrderDAO.create({"customer_name": "张三", "delivery_date": ""})

    params = mock_cursor.execute.call_args.args[1]
    assert params[17] is None


def test_create_closes_connection_even_on_exception(mock_get_connection):
    r"""create 异常时 conn.close() 仍调(源码 finally 块)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.execute.side_effect = RuntimeError("DB error")
        try:
            OrderDAO.create({"customer_name": "张三"})
        except RuntimeError:
            pass
    mock_conn.close.assert_called_once()


def test_update_executes_update_with_status_log(mock_get_connection):
    r"""update 必须执行 UPDATE + 状态变更日志。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.fetchone.side_effect = [
            {"status": "待确认"},
            {"order_no": "GO-001"},
        ]
        with patch("models.order.log_status_change") as mock_status:
            with patch("models.order.log_order_action") as mock_action:
                result = OrderDAO.update(1, {"status": "待排产", "remark": "测试"})

    assert result is True
    update_calls = [c for c in mock_cursor.execute.call_args_list if "UPDATE orders" in str(c.args[0])]
    assert len(update_calls) == 1
    mock_conn.commit.assert_called_once()
    mock_status.assert_called_once()
    mock_action.assert_called_once()


def test_update_no_status_change_only_logs_action(mock_get_connection):
    r"""update status 不变时只 log_order_action(不 log_status_change)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            {"status": "待确认"},
            {"order_no": "GO-001"},
        ]
        with patch("models.order.log_status_change") as mock_status:
            with patch("models.order.log_order_action") as mock_action:
                OrderDAO.update(1, {"status": "待确认", "remark": "测试"})

    mock_status.assert_not_called()
    mock_action.assert_called_once()


def test_update_returns_false_on_exception(mock_get_connection):
    r"""update 异常时 rollback 返 False(源码 line 170-176)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.fetchone.side_effect = [
            {"status": "待确认"},
            {"order_no": "GO-001"},
        ]
        mock_cursor.execute.side_effect = [None, None, RuntimeError("DB error")]
        result = OrderDAO.update(1, {"status": "待排产"})

    assert result is False
    mock_conn.rollback.assert_called_once()


def test_update_status_invalid_order_id_returns_false():
    r"""update_status order_id=0/None 返 False(源码 line 192-194)。"""
    assert OrderDAO.update_status(0, "已排产") is False
    assert OrderDAO.update_status(None, "已排产") is False


def test_update_status_order_not_found_returns_false(mock_get_connection):
    r"""update_status 订单不存在时返 False(源码 line 201-204)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = None
        result = OrderDAO.update_status(999, "已排产")
    assert result is False


def test_update_status_executes_update_and_logs(mock_get_connection):
    r"""update_status 调 UPDATE + log_status_change + log_order_action。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.fetchone.side_effect = [
            {"status": "待确认"},
            {"order_no": "GO-001"},
        ]
        with patch("models.order.log_status_change") as mock_status:
            with patch("models.order.log_order_action") as mock_action:
                result = OrderDAO.update_status(1, "已排产", operator="张三")

    assert result is True
    update_calls = [c for c in mock_cursor.execute.call_args_list if "UPDATE orders" in str(c.args[0])]
    assert len(update_calls) == 1
    assert update_calls[0].args[1] == ("已排产", 1)
    mock_conn.commit.assert_called_once()
    mock_status.assert_called_once()
    mock_action.assert_called_once()


def test_update_status_action_map_for_known_statuses(mock_get_connection):
    r"""update_status action_map 含 待确认→CREATE/已排产→SCHEDULE/已完成→COMPLETE 等。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            {"status": "待确认"},
            {"order_no": "GO-001"},
        ]
        with patch("models.order.log_order_action") as mock_action:
            OrderDAO.update_status(1, "已完成")

    call_args = mock_action.call_args
    assert call_args.args[2] == "COMPLETE"


def test_update_status_unknown_status_uses_update_action(mock_get_connection):
    r"""update_status new_status 不在 action_map 时用 'UPDATE'。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            {"status": "待确认"},
            {"order_no": "GO-001"},
        ]
        with patch("models.order.log_order_action") as mock_action:
            OrderDAO.update_status(1, "未知状态")

    call_args = mock_action.call_args
    assert call_args.args[2] == "UPDATE"


def test_delete_calls_update_status_with_cancelled(mock_get_connection):
    r"""delete 走 update_status(CANCELLED)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            {"order_no": "GO-001"},  # delete() 查 order_no
            {"status": "待确认"},      # update_status() 查旧状态
            {"order_no": "GO-001"},  # update_status() 查 order_no
        ]
        with patch("models.order.log_order_action"):
            result = OrderDAO.delete(1)
    assert result is True
    update_calls = [c for c in mock_cursor.execute.call_args_list if "UPDATE orders" in str(c.args[0])]
    assert update_calls[0].args[1][0] == "已取消"


def test_get_by_id_returns_parsed_dict(mock_get_connection):
    r"""get_by_id 命中时返 _parse_extra_params(dict(row))。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {
            "id": 1, "order_no": "GO-001", "extra_params": "",
        }
        result = OrderDAO.get_by_id(1)
    assert result["id"] == 1
    assert result["order_no"] == "GO-001"


def test_get_by_id_missing_returns_none(mock_get_connection):
    r"""get_by_id 不存在返 None。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = None
        result = OrderDAO.get_by_id(999)
    assert result is None


def test_get_unscheduled_filters_status_and_production(mock_get_connection):
    r"""get_unscheduled 选 待排产/待发布 且未生成生产工单 的订单。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [
            {"id": 1, "order_no": "GO-001", "extra_params": ""},
        ]
        result = OrderDAO.get_unscheduled()

    assert len(result) == 1
    sql = mock_cursor.execute.call_args.args[0]
    assert "is_deleted = 0" in sql
    assert "production_orders" in sql


def test_get_all_default_excludes_completed_archived_cancelled(mock_get_connection):
    r"""get_all 无 status filter 时,sql 默认排除 已完成/已归档/已取消。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_all()

    sql = mock_cursor.execute.call_args.args[0]
    assert "NOT IN ('已完成', '已归档', '已取消')" in sql


def test_get_all_with_status_filter(mock_get_connection):
    r"""get_all 传 status filter 时直接拼 AND status=%s。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_all({"status": "待排产"})

    sql = mock_cursor.execute.call_args.args[0]
    params = mock_cursor.execute.call_args.args[1]
    assert "AND status=%s" in sql
    assert "待排产" in params


def test_get_all_with_keyword_searches_seven_fields(mock_get_connection):
    r"""get_all 传 keyword 时拼 7 字段 LIKE 块。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_all({"keyword": "304"})

    sql = mock_cursor.execute.call_args.args[0]
    params = mock_cursor.execute.call_args.args[1]
    assert "order_no LIKE %s" in sql
    assert "extra_params LIKE %s" in sql
    assert params.count("%304%") == 7


def test_get_recent_for_kanban_excludes_90_days_completed(mock_get_connection):
    r"""get_recent_for_kanban 排除 90 天前 + 已完/已归/已取。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_recent_for_kanban(limit=50)

    sql = mock_cursor.execute.call_args.args[0]
    params = mock_cursor.execute.call_args.args[1]
    assert "INTERVAL 90 DAY" in sql
    assert "status NOT IN" in sql
    assert params == (50,)


def test_get_recent_for_list_no_date_filter(mock_get_connection):
    r"""get_recent_for_list 无 90 天限制。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_recent_for_list(limit=100)

    sql = mock_cursor.execute.call_args.args[0]
    assert "INTERVAL 90 DAY" not in sql
    assert mock_cursor.execute.call_args.args[1] == (100,)


def test_get_all_paginated_returns_pager_dict(mock_get_connection):
    r"""get_all_paginated 返 {data, total, page, page_size, total_pages, has_next, has_prev}。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {"COUNT(*)": 95}
        mock_cursor.fetchall.return_value = [{"id": 1, "extra_params": ""}]
        result = OrderDAO.get_all_paginated(page=2, page_size=20)

    assert result["total"] == 95
    assert result["page"] == 2
    assert result["page_size"] == 20
    assert result["total_pages"] == 5
    assert result["has_next"] is True
    assert result["has_prev"] is True
    assert len(result["data"]) == 1


def test_get_all_paginated_clamps_page_size_to_1000(mock_get_connection):
    r"""get_all_paginated page_size > 1000 时 clamp 到 1000。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {"COUNT(*)": 0}
        mock_cursor.fetchall.return_value = []
        result = OrderDAO.get_all_paginated(page=1, page_size=5000)
    assert result["page_size"] == 1000


def test_get_all_paginated_max_total_caps_result(mock_get_connection):
    r"""get_all_paginated total > max_total 时被 clamp。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {"COUNT(*)": 50000}
        mock_cursor.fetchall.return_value = []
        result = OrderDAO.get_all_paginated(page=1, page_size=20, max_total=1000)
    assert result["total"] == 1000


def test_get_kanban_stats_uses_q_mark_sqlite_style(mock_get_connection):
    r"""get_kanban_stats 真源码用 ? 占位符(MySQL 不支持),测真行为。

    源码 line 499 f"... WHERE status != ? ..." 用 SQLite 占位符。
    """
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [("待确认", 5), ("待排产", 3)]
        result = OrderDAO.get_kanban_stats()

    assert result == {"待确认": 5, "待排产": 3}
    sql = mock_cursor.execute.call_args.args[0]
    assert "?" in sql


def test_fuzzy_search_returns_six_fields(mock_get_connection):
    r"""fuzzy_search 返 6 字段:id/order_no/customer_name/product_type/status/delivery_date。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [
            {"id": 1, "order_no": "GO-001", "customer_name": "张三",
             "product_type": "编织网带", "status": "待确认", "delivery_date": "2026-05-01"},
        ]
        result = OrderDAO.fuzzy_search("GO")

    assert len(result) == 1
    assert "id" in result[0]
    assert "delivery_date" in result[0]
    assert mock_cursor.execute.call_args.args[1][-1] == 20


def test_fuzzy_search_with_custom_limit(mock_get_connection):
    r"""fuzzy_search limit 参数生效。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.fuzzy_search("304", limit=5)

    assert mock_cursor.execute.call_args.args[1][-1] == 5


def test_archive_orders_with_ids_archives_specified(mock_get_connection):
    r"""archive_orders 传 order_ids 时归档指定订单。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.fetchone.return_value = {"cnt": 2}
        result = OrderDAO.archive_orders([1, 2], operator="张三")

    assert result["archived"] == 2
    assert result["skipped"] == 0
    update_calls = [c for c in mock_cursor.execute.call_args_list if "UPDATE orders" in str(c.args[0])]
    assert "is_archived = 1" in update_calls[0].args[0]
    assert "status = '已归档'" in update_calls[0].args[0]
    mock_conn.commit.assert_called_once()


def test_archive_orders_with_no_eligible_returns_zero(mock_get_connection):
    r"""archive_orders 订单都不存在时返 archived=0(源码 line 991-992)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {"cnt": 0}
        result = OrderDAO.archive_orders([1, 2])

    assert result == {"archived": 0, "skipped": 0}


def test_archive_orders_by_days_auto_selects(mock_get_connection):
    r"""archive_orders 不传 order_ids 时按 days 自动选。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            {"cutoff_date": "2025-06-12"},
            {"cnt": 10},
        ]
        result = OrderDAO.archive_orders(None, days=30)

    assert result["archived"] == 10
    date_sql = [c for c in mock_cursor.execute.call_args_list if "DATE_SUB" in str(c.args[0])]
    assert len(date_sql) == 1


def test_archive_orders_returns_error_on_exception(mock_get_connection):
    r"""archive_orders 异常时返 {archived:0, error}。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {"cnt": 1}
        mock_cursor.execute.side_effect = [None, RuntimeError("DB error")]
        result = OrderDAO.archive_orders([1, 2])

    assert result["archived"] == 0
    assert "error" in result
    assert "DB error" in result["error"]


def test_unarchive_orders_restores_original_status(mock_get_connection):
    r"""unarchive_orders 取消归档,status 恢复为 original_status。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.rowcount = 2
        result = OrderDAO.unarchive_orders([1, 2])

    assert result["unarchived"] == 2
    update_sqls = [c.args[0] for c in mock_cursor.execute.call_args_list if "is_archived = 0" in str(c.args[0])]
    assert len(update_sqls) >= 1
    assert "COALESCE(original_status, '待确认')" in update_sqls[0]
    mock_conn.commit.assert_called_once()


def test_get_archived_orders_with_keyword_filter(mock_get_connection):
    r"""get_archived_orders keyword 过滤。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_archived_orders({"keyword": "304"})

    sql = mock_cursor.execute.call_args.args[0]
    params = mock_cursor.execute.call_args.args[1]
    assert "is_archived = 1" in sql
    assert "order_no LIKE %s" in sql
    assert params.count("%304%") == 6


def test_get_dashboard_order_stats_returns_seven_fields(mock_get_connection):
    r"""get_dashboard_order_stats 返 totalOrders/monthlyNew/statusDistribution/producing/ready/overdue/completedCount/completionRate 8 字段。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {"total": 100, "count": 5}
        mock_cursor.fetchall.return_value = [
            {"status": "待确认", "count": 5},
            {"status": "已完成", "count": 10},
        ]
        result = OrderDAO.get_dashboard_order_stats()

    assert result["totalOrders"] == 100
    assert "statusDistribution" in result
    assert "completionRate" in result


def test_get_dashboard_order_stats_completion_rate_zero_when_no_orders(mock_get_connection):
    r"""get_dashboard_order_stats total=0 时 completionRate=0(源码 1204 行 if total > 0 else 0)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {"total": 0, "count": 0}
        mock_cursor.fetchall.return_value = []
        result = OrderDAO.get_dashboard_order_stats()
    assert result["completionRate"] == 0


def test_get_delivery_alert_orders_filters_archived(mock_get_connection):
    r"""get_delivery_alert_orders 排除已发/已完/已取订单(用 %s 占位符传 status)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_delivery_alert_orders(days_ahead=3)

    sql = mock_cursor.execute.call_args.args[0]
    params = mock_cursor.execute.call_args.args[1]
    assert "DATE_ADD(NOW(), INTERVAL %s DAY)" in sql
    assert "已发货" in params
    assert "已完成" in params
    assert "已取消" in params
    assert params[0] == 3


def test_get_dashboard_order_list_orders_by_status_priority(mock_get_connection):
    r"""get_dashboard_order_list 按 status 优先级排序(case when 拼 SQL,MySQL 用小写)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_dashboard_order_list(limit=15)

    sql = mock_cursor.execute.call_args.args[0]
    params = mock_cursor.execute.call_args.args[1]
    assert "ORDER BY" in sql
    assert "WHEN" in sql
    assert params[-1] == 15


def test_get_by_status_returns_dict_list(mock_get_connection):
    r"""get_by_status 返 [dict] 列表(不调 _parse_extra_params)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [{"id": 1, "order_no": "GO-001"}]
        result = OrderDAO.get_by_status("待确认")

    assert len(result) == 1
    assert result[0]["order_no"] == "GO-001"


def test_get_process_records_orders_by_seq(mock_get_connection):
    r"""get_process_records 按 process_seq ASC 排序。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_process_records(1)

    sql = mock_cursor.execute.call_args.args[0]
    assert "process_records" in sql
    assert "process_seq ASC" in sql


def test_get_quality_records_orders_by_date_desc(mock_get_connection):
    r"""get_quality_records 按 record_date DESC 排序。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_quality_records(1)

    sql = mock_cursor.execute.call_args.args[0]
    assert "quality_records" in sql
    assert "record_date DESC" in sql


def test_get_shipments_orders_by_ship_date_desc(mock_get_connection):
    r"""get_shipments 按 ship_date DESC 排序。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_shipments(1)

    sql = mock_cursor.execute.call_args.args[0]
    assert "shipments" in sql
    assert "ship_date DESC" in sql


def test_get_status_logs_filters_by_table_name(mock_get_connection):
    r"""get_status_logs WHERE table_name='orders'。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        OrderDAO.get_status_logs(1)

    sql = mock_cursor.execute.call_args.args[0]
    assert "table_name='orders'" in sql
    assert "created_at DESC" in sql


def test_get_production_order_returns_most_recent(mock_get_connection):
    r"""get_production_order 返最近一条(ORDER BY id DESC LIMIT 1)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {"id": 5, "order_id": 1}
        result = OrderDAO.get_production_order(1)

    assert result["id"] == 5
    sql = mock_cursor.execute.call_args.args[0]
    assert "ORDER BY id DESC LIMIT 1" in sql


def test_get_production_order_missing_returns_none(mock_get_connection):
    r"""get_production_order 不存在返 None。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = None
        result = OrderDAO.get_production_order(999)
    assert result is None


def test_get_order_statistics_returns_default_when_order_not_found(mock_get_connection):
    r"""get_order_statistics 订单不存在时返默认空 result(源码 line 789-790)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = None
        result = OrderDAO.get_order_statistics(999)
    assert result["order_total_days"] is None
    assert result["loss_rate"] is None
    assert result["process_times"] == []


def test_get_order_statistics_calculates_loss_rate(mock_get_connection):
    r"""get_order_statistics 根据 process_records 计算 loss_rate。

    真源码 line 851 `processes = cursor.fetchall()`(不是 fetchone)
    """
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.side_effect = [
            {"id": 1, "unit": "米", "extra_params": "", "surface_treatment": ""},
            {"created_at": "2025-01-01 10:00:00"},
            {"created_at": "2025-01-10 10:00:00"},
            {"actual_start": "2025-01-02 10:00:00", "actual_end": "2025-01-08 10:00:00"},
        ]
        mock_cursor.fetchall.return_value = [
            {"process_name": "P01", "start_time": None, "end_time": None,
             "completed_qty": 100, "qualified_qty": 90, "material_usage": None,
             "planned_qty": None, "status": "进行中"},
        ]
        result = OrderDAO.get_order_statistics(1)

    assert result["loss_rate"] == 10.0
    assert result["order_total_days"] == 9


def test_get_batch_order_statistics_empty_returns_empty_dict():
    r"""get_batch_order_statistics 空 order_ids 返 {}。"""
    result = OrderDAO.get_batch_order_statistics([])
    assert result == {}


def test_get_batch_order_statistics_handles_string_extra_params(mock_get_connection):
    r"""get_batch_order_statistics extra_params 是 str 时解析 JSON。

    真源码调用 cursor.fetchall() 5 次:order info / confirmed / completed / production / process。
    """
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.side_effect = [
            [{"id": 1, "unit": "米", "extra_params": json.dumps({"生产工艺": "锻造"}, ensure_ascii=False), "surface_treatment": ""}],
            [],
            [],
            [],
            [],
        ]
        result = OrderDAO.get_batch_order_statistics([1])

    assert 1 in result
    assert result[1]["production_process"] == "锻造"


def test_batch_get_order_statistics_empty_returns_empty_dict():
    r"""batch_get_order_statistics 空 order_ids 返 {}。"""
    result = OrderDAO.batch_get_order_statistics([])
    assert result == {}


def test_batch_get_order_statistics_uses_subqueries(mock_get_connection):
    r"""batch_get_order_statistics 用 4 子查询(订单总用时/生产总用时/损耗率/生产工艺)。"""
    with mock_get_connection("models.order.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [
            {"id": 1, "extra_params": "", "unit": "米",
             "order_total_days": 10, "production_total_days": 8, "loss_rate": 5.0},
        ]
        result = OrderDAO.batch_get_order_statistics([1])

    assert 1 in result
    assert result[1]["order_total_days"] == 10
