# -*- coding: utf-8 -*-
"""
生产工单数据模型单元测试 (ProductionDAO) — 全覆盖
"""
import pytest
from unittest.mock import MagicMock, patch, call


# ── 辅助函数 ──────────────────────────────────────────────

def _build_order_row(**overrides):
    """构建模拟的订单查询行"""
    row = {
        "id": 1, "order_no": "PO-20260601-001", "customer_name": "测试客户",
        "customer_group": "", "product_type": "冷冻网带", "mesh_size": "10x10",
        "material": "304", "width": 1000, "length": 2000, "quantity": 50,
        "delivery_date": "2026-07-01", "status": "待排产",
        "extra_params": None, "unit": "件",
    }
    row.update(overrides)
    return row


def _build_prod_row(**overrides):
    """构建模拟的生产工单行"""
    row = {
        "id": 1, "order_id": 1, "order_no": "PO-20260601-001",
        "priority": 5, "plan_start": "2026-06-05", "plan_end": "2026-06-15",
        "assigned_to": "张三", "status": "待生产", "remark": "加急",
        "actual_start": None, "created_at": "2026-06-01",
    }
    row.update(overrides)
    return row


def _make_cursor_and_conn():
    """创建独立的 cursor + conn mock 对"""
    cursor = MagicMock()
    cursor.close.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.close.return_value = None
    return cursor, conn


def _ci(fetchone_value=None, lastrowid=None):
    """创建独立 cursor mock，可选设置 fetchone 或 lastrowid"""
    c, _ = _make_cursor_and_conn()
    if fetchone_value is not None:
        c.fetchone.return_value = fetchone_value
    if lastrowid is not None:
        c.lastrowid = lastrowid
    return c


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_deps():
    """全局 mock 所有外部依赖，各 mock 通过 mock_deps.xxx 访问"""
    class _Mocks:
        pass
    m = _Mocks()
    m.get_connection = patch("models.production.get_connection").start()
    m.log = patch("models.production.log").start()
    m.log_step = patch("models.production.log_step").start()
    m.log_sql = patch("models.production.log_sql").start()
    m.log_error = patch("models.production.log_error").start()
    m.log_status_change = patch("models.production.log_status_change").start()
    yield m
    patch.stopall()


@pytest.fixture
def conn(mock_deps):
    """获取 mock 连接 (get_connection 的 return_value)"""
    return mock_deps.get_connection.return_value


@pytest.fixture
def dao():
    from models.production import ProductionDAO
    return ProductionDAO


class TestCreate:
    """ProductionDAO.create — 为订单创建生产工单"""

    # ── 辅助构造 ──

    def _setup_create_flow(self, conn, order_row=None, extra_row=None, prod_id=1,
                            process_count=1):
        """以 side_effect 方式设置 create 方法所需的全部 cursor，返回 (prod_id, process_cursors)
        
        注意: extra_row=None 时不会设置 fetchone.return_value（_ci 行为），
             此时需确保调用方自行设置 extra_params 的返回值为 falsy。
        """
        """以 side_effect 方式设置 create 方法所需的全部 cursor，返回 (prod_id, process_cursors)"""
        if order_row is None:
            order_row = _build_order_row()
        cursors = []
        # cursor 1: 查询订单
        cursors.append(_ci(fetchone_value=order_row))
        # cursor 2: 插入 production_orders
        cursors.append(_ci(lastrowid=prod_id))
        # cursor 3: 查询 extra_params
        cursors.append(_ci(fetchone_value=extra_row))
        # cursor 4..N: 插入工序（每个工序一个 cursor）
        process_cursors = []
        for _ in range(process_count):
            process_cursors.append(_ci())
            cursors.append(process_cursors[-1])
        # cursor N+1: 更新订单状态
        cursors.append(_ci())
        conn.cursor.side_effect = cursors
        return prod_id, process_cursors

    def test_create_success(self, dao, conn):
        """正常创建：含完整流程 6 个步骤"""
        prod_id, _ = self._setup_create_flow(conn, prod_id=42, process_count=1)

        with patch("models.process_calc_rule.ProcessCalcEngine.generate_processes_from_order",
                   return_value=[{"process_name": "编织", "process_code": "BZ",
                                  "process_seq": 1, "display_seq": 1, "planned_qty": 50,
                                  "default_worker": "李四", "unit": "件"}]):

            result = dao.create(1, {"priority": 3, "plan_start": "2026-06-05",
                                    "plan_end": "2026-06-15", "assigned_to": "张三",
                                    "remark": "加急"})

        assert result == 42
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    def test_create_order_not_found(self, dao, conn):
        """订单不存在时抛出 ValueError"""
        cursor, _ = _make_cursor_and_conn()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = None

        with pytest.raises(ValueError, match="订单 1 不存在"):
            dao.create(1, {})

        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    def test_create_with_extra_params(self, dao, conn):
        """扩展参数为有效 JSON dict"""
        prod_id, _ = self._setup_create_flow(
            conn, extra_row={"extra_params": '{"线径": 1.2, "材质": "316"}'},
            prod_id=3, process_count=0
        )
        with patch("models.process_calc_rule.ProcessCalcEngine.generate_processes_from_order",
                   return_value=[]):
            result = dao.create(1, {"priority": 5})

        assert result == 3
        conn.commit.assert_called_once()

    def test_create_extra_params_already_dict(self, dao, conn):
        """extra_params 字段已经是 dict（非字符串）"""
        prod_id, _ = self._setup_create_flow(
            conn, extra_row={"extra_params": {"线径": 1.2}},
            prod_id=4, process_count=0
        )
        with patch("models.process_calc_rule.ProcessCalcEngine.generate_processes_from_order",
                   return_value=[]):
            result = dao.create(1, {"priority": 5})

        assert result == 4
        conn.commit.assert_called_once()

    def test_create_extra_params_invalid_json(self, dao, conn):
        """extra_params 无效 JSON 时静默捕获异常"""
        prod_id, _ = self._setup_create_flow(
            conn, extra_row={"extra_params": "{{invalid_json}}"},
            prod_id=5, process_count=0
        )
        with patch("models.process_calc_rule.ProcessCalcEngine.generate_processes_from_order",
                   return_value=[]):
            result = dao.create(1, {"priority": 5})

        assert result == 5

    def test_create_extra_params_null(self, dao, conn):
        """extra_row['extra_params'] 为 None → 触发 else 分支 log（行83）"""
        prod_id, _ = self._setup_create_flow(
            conn, extra_row={"extra_params": None},
            prod_id=9, process_count=0
        )
        with patch("models.process_calc_rule.ProcessCalcEngine.generate_processes_from_order",
                   return_value=[]):
            result = dao.create(1, {"priority": 5})

        assert result == 9
        conn.commit.assert_called_once()
        from models.production import log
        log.assert_any_call("排产", "扩展参数", "⚠️ 无扩展参数，计算公式可能结果为0")

    def test_create_extra_params_empty_string(self, dao, conn):
        """extra_row['extra_params'] 为空字符串 → 触发 else 分支 log（行83）"""
        prod_id, _ = self._setup_create_flow(
            conn, extra_row={"extra_params": ""},
            prod_id=10, process_count=0
        )
        with patch("models.process_calc_rule.ProcessCalcEngine.generate_processes_from_order",
                   return_value=[]):
            result = dao.create(1, {"priority": 5})

        assert result == 10
        conn.commit.assert_called_once()
        from models.production import log
        log.assert_any_call("排产", "扩展参数", "⚠️ 无扩展参数，计算公式可能结果为0")

    def test_create_exception_rollback(self, dao, conn):
        """数据库异常时 rollback 并重新抛出"""
        # create 方法在异常前需要3次 cursor: 查询订单 / 插入 / 查询extra_params
        c1 = _ci(fetchone_value=_build_order_row())
        c2 = _ci(lastrowid=1)
        c3 = _ci(fetchone_value=None)
        conn.cursor.side_effect = [c1, c2, c3]

        with patch("models.process_calc_rule.ProcessCalcEngine.generate_processes_from_order",
                   side_effect=RuntimeError("生成工序失败")):
            with pytest.raises(RuntimeError, match="生成工序失败"):
                dao.create(1, {"priority": 5})

        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    def test_create_default_values(self, dao, conn):
        """未提供可选字段时使用默认值"""
        prod_id, _ = self._setup_create_flow(conn, prod_id=6, process_count=0)
        with patch("models.process_calc_rule.ProcessCalcEngine.generate_processes_from_order",
                   return_value=[]):
            result = dao.create(1, {})

        assert result == 6
        conn.commit.assert_called_once()

    def test_create_quantity_none(self, dao, conn):
        """quantity 为 None 时默认 0，product_type 为 None 时默认空字符串"""
        order_row = _build_order_row(quantity=None, product_type=None)
        prod_id, _ = self._setup_create_flow(conn, order_row=order_row, prod_id=7, process_count=0)
        with patch("models.process_calc_rule.ProcessCalcEngine.generate_processes_from_order",
                   return_value=[]):
            result = dao.create(1, {})

        assert result == 7


class TestUpdate:
    """ProductionDAO.update"""

    def test_update_success(self, dao, conn):
        """正常更新工单（状态不变）"""
        cursor, _ = _make_cursor_and_conn()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = {"status": "待生产"}

        result = dao.update(1, {"priority": 3, "remark": "修改备注"})

        assert result is True
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    def test_update_with_status_change(self, dao, conn):
        """更新状态（不同状态）触发 log_status_change"""
        cursor, _ = _make_cursor_and_conn()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = {"status": "待生产"}

        result = dao.update(1, {"status": "生产中"})

        assert result is True
        from models.production import log_status_change
        log_status_change.assert_called_once_with("production_orders", 1, "待生产", "生产中")

    def test_update_same_status(self, dao, conn):
        """更新时状态相同，不触发 log_status_change"""
        cursor, _ = _make_cursor_and_conn()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = {"status": "待生产"}

        result = dao.update(1, {"status": "待生产"})

        assert result is True
        from models.production import log_status_change
        log_status_change.assert_not_called()

    def test_update_no_old_status(self, dao, conn):
        """工单不存在时 old_status 为 None"""
        cursor, _ = _make_cursor_and_conn()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = None

        result = dao.update(999, {"status": "生产中"})

        assert result is True

    def test_update_no_data_status(self, dao, conn):
        """data 中无 status 字段则沿用 old_status"""
        cursor, _ = _make_cursor_and_conn()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = {"status": "待生产"}

        result = dao.update(1, {"priority": 1})

        assert result is True

    def test_update_default_values(self, dao, conn):
        """data 中未提供字段使用默认值"""
        cursor, _ = _make_cursor_and_conn()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = {"status": "待生产"}

        result = dao.update(1, {})

        assert result is True


class TestUpdateStatus:
    """ProductionDAO.update_status"""

    @pytest.fixture(autouse=True)
    def setup_sync_mocks(self):
        with patch("os.environ.get", return_value="http://sync:5008"):
            yield

    def test_update_status_in_progress_enum(self, dao, conn):
        """传入 ProductionStatus.IN_PROGRESS.value → 触发 if 分支 actual_start=NOW()（行179-186）"""
        c1 = _ci(fetchone_value={"status": "待生产", "order_id": 1})
        c2 = _ci()  # UPDATE production_orders（if 分支，含 actual_start=NOW()）
        c3 = _ci()  # UPDATE orders（STATUS_ORDERS_MAP 映射到 OrderStatus.PRODUCTION）
        c4 = _ci(fetchone_value={"order_no": "PO-20260601-001"})
        conn.cursor.side_effect = [c1, c2, c3, c4]

        from models.production import ProductionStatus
        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            result = dao.update_status(1, ProductionStatus.IN_PROGRESS.value, "系统")

        assert result is True
        conn.commit.assert_called_once()
        conn.close.assert_called_once()
        # 验证 UPDATE 使用了 actual_start=NOW()（if 分支 vs. else 分支的区别）
        actual_start_calls = [c for c in c2.execute.call_args_list
                              if "actual_start=NOW()" in str(c)]
        assert len(actual_start_calls) == 1
        mock_post.assert_called_once()

    def test_update_to_in_progress(self, dao, conn):
        """更新状态（值传递后会走实际的映射逻辑）
        注意: "进行中" 是前端传值，不是枚举值，
             会走到 else 分支，且 STATUS_ORDERS_MAP.get("进行中") 为 None，
             因此 UPDATE orders 被跳过，sync 块需要第 3 个 cursor。
        """
        c1 = _ci(fetchone_value={"status": "待生产", "order_id": 1})
        c2 = _ci()  # UPDATE production_orders（else 分支）
        c3 = _ci(fetchone_value={"order_no": "PO-20260601-001"})
        conn.cursor.side_effect = [c1, c2, c3]

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            result = dao.update_status(1, "进行中", "系统")

        assert result is True
        conn.commit.assert_called_once()
        conn.close.assert_called_once()
        mock_post.assert_called_once()

    def test_update_to_completed(self, dao, conn):
        """更新为完成（非进行中，走 else 分支）"""
        c1 = _ci(fetchone_value={"status": "进行中", "order_id": 1})
        c2 = _ci()  # UPDATE production_orders
        c3 = _ci()  # UPDATE orders
        c4 = _ci(fetchone_value={"order_no": "PO-20260601-001"})
        conn.cursor.side_effect = [c1, c2, c3, c4]

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            result = dao.update_status(1, "报工完成", "系统")

        assert result is True

    def test_update_no_order_id(self, dao, conn):
        """工单无 order_id 时不更新订单状态"""
        c1 = _ci(fetchone_value={"status": "待生产", "order_id": None})
        c2 = _ci()  # UPDATE production_orders（if 分支）
        conn.cursor.side_effect = [c1, c2]

        with patch("requests.post") as mock_post:
            result = dao.update_status(1, "进行中")

        assert result is True
        # order_id=None 跳过了订单状态更新和 sync 块

    def test_update_no_old_record(self, dao, conn):
        """工单不存在时 old 为 None"""
        c1 = _ci(fetchone_value=None)
        c2 = _ci()  # UPDATE production_orders（else 分支）
        conn.cursor.side_effect = [c1, c2]

        result = dao.update_status(999, "进行中")

        assert result is True

    def test_update_order_status_not_mapped(self, dao, conn):
        """new_status 不在 STATUS_ORDERS_MAP 中时不更新订单状态
        注意: "未知状态" 是真值，且 order_id=1，sync 条件满足，
             因此需要第 3 个 cursor 用于 sync 块内查询。
        """
        c1 = _ci(fetchone_value={"status": "待生产", "order_id": 1})
        c2 = _ci()  # UPDATE production_orders（else 分支）
        c3 = _ci(fetchone_value={"order_no": None})  # sync 块内查询
        conn.cursor.side_effect = [c1, c2, c3]

        result = dao.update_status(1, "未知状态")

        assert result is True

    def test_update_sync_exception_silent(self, dao, conn):
        """sync 桥接失败时静默捕获
        注意: "进行中" 走 else 分支，STATUS_ORDERS_MAP.get("进行中")=None 跳过 UPDATE orders，
             sync 条件满足，需要第 3 个 cursor。
        """
        c1 = _ci(fetchone_value={"status": "待生产", "order_id": 1})
        c2 = _ci()  # UPDATE production_orders（else 分支）
        c3 = _ci(fetchone_value={"order_no": "PO-20260601-001"})  # sync 块内查询
        conn.cursor.side_effect = [c1, c2, c3]

        with patch("requests.post", side_effect=Exception("连接失败")):
            result = dao.update_status(1, "进行中")

        assert result is True

    def test_update_sync_no_order_no(self, dao, conn):
        """查询 order_no 为空时不触发 sync
        注意: "进行中" != ProductionStatus.IN_PROGRESS.value ("IN_PROGRESS")，
             且 STATUS_ORDERS_MAP.get("进行中") 返回 None，
             因此 UPDATE orders 被跳过，sync 块需要第 3 个 cursor。
        """
        c1 = _ci(fetchone_value={"status": "待生产", "order_id": 1})
        c2 = _ci()  # UPDATE production_orders（else 分支）
        c3 = _ci(fetchone_value={"order_no": None})  # sync 块内查询
        conn.cursor.side_effect = [c1, c2, c3]

        with patch("requests.post") as mock_post:
            result = dao.update_status(1, "进行中")

        assert result is True
        mock_post.assert_not_called()


class TestConfirmSchedule:
    """ProductionDAO.confirm_schedule"""

    def test_confirm_schedule_success(self, dao, conn):
        """正常确认排产（order_id 非空 → 4个 cursor）"""
        c1 = _ci(fetchone_value={"status": "待生产", "order_id": 1})
        c2 = _ci()  # UPDATE production_orders
        c3 = _ci()  # UPDATE orders
        c4 = _ci(fetchone_value={"order_no": "PO-20260601-001"})
        conn.cursor.side_effect = [c1, c2, c3, c4]

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            result = dao.confirm_schedule(1, "2026-06-05", "2026-06-15")

        assert result is True
        conn.commit.assert_called_once()

    def test_confirm_schedule_no_old(self, dao, conn):
        """工单不存在时 old 为 None（order_id 为 None → 3个 cursor）"""
        c1 = _ci(fetchone_value=None)
        c2 = _ci()  # UPDATE production_orders
        c3 = _ci(fetchone_value={"order_no": None})  # sync 块内查询 order_no
        conn.cursor.side_effect = [c1, c2, c3]

        with patch("requests.post") as mock_post:
            result = dao.confirm_schedule(999, "2026-06-05", "2026-06-15")

        assert result is True

    def test_confirm_schedule_no_order_id(self, dao, conn):
        """order_id 为 None 时不更新订单状态（3个 cursor）"""
        c1 = _ci(fetchone_value={"status": "待生产", "order_id": None})
        c2 = _ci()  # UPDATE production_orders
        c3 = _ci(fetchone_value={"order_no": "PO-20260601-001"})  # sync 块内查询
        conn.cursor.side_effect = [c1, c2, c3]

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            result = dao.confirm_schedule(1, "2026-06-05", "2026-06-15")

        assert result is True

    def test_confirm_schedule_same_status(self, dao, conn):
        """状态相同不触发 log_status_change（order_id 非空 → 4个 cursor）"""
        c1 = _ci(fetchone_value={"status": "生产中", "order_id": 1})
        c2 = _ci()  # UPDATE production_orders
        c3 = _ci()  # UPDATE orders
        c4 = _ci(fetchone_value={"order_no": "PO-20260601-001"})
        conn.cursor.side_effect = [c1, c2, c3, c4]

        with patch("requests.post") as mock_post:
            mock_post.return_value.ok = True
            result = dao.confirm_schedule(1, "2026-06-05", "2026-06-15")

        assert result is True
        from models.production import log_status_change
        log_status_change.assert_not_called()

    def test_confirm_schedule_sync_exception(self, dao, conn):
        """sync 桥接异常静默（4个 cursor）"""
        c1 = _ci(fetchone_value={"status": "待生产", "order_id": 1})
        c2 = _ci()  # UPDATE production_orders
        c3 = _ci()  # UPDATE orders
        c4 = _ci(fetchone_value={"order_no": "PO-20260601-001"})
        conn.cursor.side_effect = [c1, c2, c3, c4]

        with patch("requests.post", side_effect=Exception("超时")):
            result = dao.confirm_schedule(1, "2026-06-05", "2026-06-15")

        assert result is True

    def test_confirm_schedule_sync_no_order_no(self, dao, conn):
        """查询 order_no 为空时不触发 sync（4个 cursor）"""
        c1 = _ci(fetchone_value={"status": "待生产", "order_id": 1})
        c2 = _ci()  # UPDATE production_orders
        c3 = _ci()  # UPDATE orders
        c4 = _ci(fetchone_value={"order_no": None})
        conn.cursor.side_effect = [c1, c2, c3, c4]

        with patch("requests.post") as mock_post:
            result = dao.confirm_schedule(1, "2026-06-05", "2026-06-15")

        assert result is True
        mock_post.assert_not_called()


class TestGetAllWithOrder:
    """ProductionDAO.get_all_with_order"""

    def test_get_all_no_filters(self, dao, conn):
        """无过滤条件"""
        c1 = _ci()
        c1.fetchall.return_value = [_build_prod_row(id=1), _build_prod_row(id=2)]
        conn.cursor.side_effect = [c1]

        result = dao.get_all_with_order()

        assert len(result) == 2
        assert result[0]["id"] == 1
        conn.close.assert_called_once()

    def test_get_all_empty(self, dao, conn):
        """空结果集"""
        c1 = _ci()
        c1.fetchall.return_value = []
        conn.cursor.side_effect = [c1]

        result = dao.get_all_with_order()

        assert result == []

    def test_get_all_filter_status_str(self, dao, conn):
        """按字符串状态过滤"""
        c1 = _ci()
        c1.fetchall.return_value = [_build_prod_row(status="待生产")]
        conn.cursor.side_effect = [c1]

        result = dao.get_all_with_order({"status": "待生产"})

        assert len(result) == 1

    def test_get_all_filter_status_list(self, dao, conn):
        """按列表状态过滤"""
        c1 = _ci()
        c1.fetchall.return_value = [_build_prod_row(status="待生产")]
        conn.cursor.side_effect = [c1]

        result = dao.get_all_with_order({"status": ["待生产", "进行中"]})

        assert len(result) == 1

    def test_get_all_filter_status_list_empty(self, dao, conn):
        """状态列表为空"""
        c1 = _ci()
        c1.fetchall.return_value = []
        conn.cursor.side_effect = [c1]

        result = dao.get_all_with_order({"status": []})

        assert result == []

    def test_get_all_filter_keyword(self, dao, conn):
        """按关键词搜索"""
        c1 = _ci()
        c1.fetchall.return_value = [_build_prod_row()]
        conn.cursor.side_effect = [c1]

        result = dao.get_all_with_order({"keyword": "测试"})

        assert len(result) == 1

    def test_get_all_filter_keyword_empty(self, dao, conn):
        """空关键词"""
        c1 = _ci()
        c1.fetchall.return_value = [_build_prod_row()]
        conn.cursor.side_effect = [c1]

        result = dao.get_all_with_order({"keyword": ""})

        assert len(result) == 1

    def test_get_all_sort_reverse(self, dao, conn):
        """降序排序"""
        c1 = _ci()
        c1.fetchall.return_value = []
        conn.cursor.side_effect = [c1]

        result = dao.get_all_with_order({"sort_col": "po.created_at", "sort_reverse": True})

        assert result == []

    def test_get_all_filters_none(self, dao, conn):
        """filters 为 None"""
        c1 = _ci()
        c1.fetchall.return_value = [_build_prod_row()]
        conn.cursor.side_effect = [c1]

        result = dao.get_all_with_order(None)

        assert len(result) == 1


class TestGetById:
    """ProductionDAO.get_by_id"""

    def test_get_by_id_found(self, dao, conn):
        """工单存在"""
        cursor, _ = _make_cursor_and_conn()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = _build_prod_row()

        result = dao.get_by_id(1)

        assert result is not None
        assert result["id"] == 1

    def test_get_by_id_not_found(self, dao, conn):
        """工单不存在"""
        cursor, _ = _make_cursor_and_conn()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = None

        result = dao.get_by_id(999)

        assert result is None


class TestGetByOrderId:
    """ProductionDAO.get_by_order_id"""

    def test_get_by_order_id_found(self, dao, conn):
        """订单存在"""
        cursor, _ = _make_cursor_and_conn()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = _build_prod_row()

        result = dao.get_by_order_id(1)

        assert result is not None
        assert result["id"] == 1

    def test_get_by_order_id_not_found(self, dao, conn):
        """订单不存在"""
        cursor, _ = _make_cursor_and_conn()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = None

        result = dao.get_by_order_id(999)

        assert result is None


class TestGetByOrderIds:
    """ProductionDAO.get_by_order_ids"""

    def test_get_by_order_ids_found(self, dao, conn):
        """批量查询返回多个结果"""
        c1 = _ci()
        c1.fetchall.return_value = [
            _build_prod_row(order_id=1),
            _build_prod_row(id=2, order_id=2),
        ]
        conn.cursor.side_effect = [c1]

        result = dao.get_by_order_ids([1, 2])

        assert len(result) == 2
        assert result[1]["order_id"] == 1
        assert result[2]["order_id"] == 2

    def test_get_by_order_ids_empty_input(self, dao, conn):
        """空列表直接返回 {}"""
        result = dao.get_by_order_ids([])

        assert result == {}

    def test_get_by_order_ids_no_results(self, dao, conn):
        """无匹配结果"""
        c1 = _ci()
        c1.fetchall.return_value = []
        conn.cursor.side_effect = [c1]

        result = dao.get_by_order_ids([999])

        assert result == {}

    def test_get_by_order_ids_single(self, dao, conn):
        """单个 order_id"""
        c1 = _ci()
        c1.fetchall.return_value = [_build_prod_row(order_id=1)]
        conn.cursor.side_effect = [c1]

        result = dao.get_by_order_ids([1])

        assert len(result) == 1
        assert result[1]["id"] == 1


class TestGetDashboardProductionList:
    """ProductionDAO.get_dashboard_production_list"""

    def test_get_dashboard_list(self, dao, conn):
        """正常获取大屏生产列表"""
        c1 = _ci()
        c1.fetchall.return_value = [
            _build_prod_row(id=1, prod_id=1, priority=3),
            _build_prod_row(id=2, prod_id=2, priority=5),
        ]
        conn.cursor.side_effect = [c1]

        result = dao.get_dashboard_production_list(20)

        assert len(result) == 2
        assert result[0]["prod_id"] == 1

    def test_get_dashboard_list_empty(self, dao, conn):
        """无数据"""
        c1 = _ci()
        c1.fetchall.return_value = []
        conn.cursor.side_effect = [c1]

        result = dao.get_dashboard_production_list(10)

        assert result == []

    def test_get_dashboard_default_limit(self, dao, conn):
        """默认 limit"""
        c1 = _ci()
        c1.fetchall.return_value = [_build_prod_row()]
        conn.cursor.side_effect = [c1]

        result = dao.get_dashboard_production_list()

        assert len(result) == 1
