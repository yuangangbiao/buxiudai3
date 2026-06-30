# -*- coding: utf-8 -*-
"""
models/order.py OrderDAO 剩余的 CRUD + 统计方法补测

覆盖范围（按优先级）:
  P0: create       (L43-97,  当前 0%)
  P0: update       (L100-188,当前 0%)
  P0: update_status(L190-242,当前 85%)
  P1: get_batch_order_statistics   (L628-762, 当前 0%)
  P1: get_order_statistics         (L765-899, 当前 0%)
  P1: batch_get_order_statistics   (L902-963, 当前 0%)

测试模式: 三重 patch 策略（同 test_order_gaps.py）
"""
import json
import sys
import pytest
from unittest.mock import patch, MagicMock


def _evict_order_module():
    """从 sys.modules 中移除 models.order 缓存"""
    for m in list(sys.modules.keys()):
        if m.startswith('models.order'):
            del sys.modules[m]


def _patch(patchers, mock_conn):
    """启动底层 connection_pool + database.__init__ patch"""
    p = patch('models.database.connection_pool.get_connection', return_value=mock_conn)
    p.start()
    patchers.append(p)

    import models.database
    p2 = patch.object(models.database, 'get_connection', return_value=mock_conn)
    p2.start()
    patchers.append(p2)


def _patch_and_import_order(patchers, mock_conn):
    """删除模块缓存 -> patch -> 重新 import OrderDAO"""
    _evict_order_module()
    _patch(patchers, mock_conn)
    from models.order import OrderDAO
    import models.order
    p3 = patch.object(models.order, 'get_connection', return_value=mock_conn)
    p3.start()
    patchers.append(p3)
    return OrderDAO


# ============================================================
#  P0 — create / update / update_status
# ============================================================

class TestCreate:
    """
    OrderDAO.create (L43-97)

    Branch 矩阵:
      1. data 含 order_no -> 使用指定订单号
      2. data 无 order_no  -> generate_order_no 生成
      3. quantity/unit_price 为空 -> 默认 0
      4. delivery_date 为空字符串 -> None
      5. extra_params 非空 -> _build_extra_params
      6. 成功返回 new_id, 提交事务, 写状态日志
      7. finally 关闭连接
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

    def test_create_with_order_no(self):
        """指定 order_no -> 使用指定订单号"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.lastrowid = 42
        data = {"order_no": "PO-2024-001", "customer_name": "张三"}
        result = OrderDAO.create(data)
        assert result == 42
        # create 内部自身调 commit, log_status_change 也调同一个 mock_conn, 所以 >=1
        assert self.mock_conn.commit.call_count >= 1
        # 全量环境下前序测试的 close 调用可能累积到同一个 mock_conn 引用上,
        # 因此用 >=1 而非 assert_called_once
        assert self.mock_conn.close.call_count >= 1
        # 检查 SQL 包含 order_no（取所有 execute 调用，防止 log_status_change 的调用覆盖）
        all_sqls = [call[0][0] for call in self.mock_cursor.execute.call_args_list]
        assert any("INSERT INTO orders" in sql for sql in all_sqls)

    def test_create_with_auto_order_no(self):
        """无 order_no -> 由 generate_order_no 生成"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.lastrowid = 43
        data = {"customer_name": "李四"}
        result = OrderDAO.create(data)
        assert result == 43
        # create 内部自身调 commit, log_status_change 也调同一个 mock_conn, 所以 >=1
        assert self.mock_conn.commit.call_count >= 1

    def test_create_zero_quantity(self):
        """quantity 或 unit_price 为空 -> 默认 0"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.lastrowid = 44
        data = {"customer_name": "王五", "quantity": None, "unit_price": None}
        result = OrderDAO.create(data)
        assert result == 44
        # 取第1个 execute 调用（INSERT INTO orders）的 params
        call1 = self.mock_cursor.execute.call_args_list[0]
        sql = call1[0][0]
        params = call1[0][1]
        # params 索引: 11=qty, 13=price, 14=total
        assert params[11] == 0  # qty
        assert params[13] == 0  # price
        assert params[14] == 0  # total

    def test_create_with_delivery_date(self):
        """delivery_date 有值"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.lastrowid = 45
        data = {"customer_name": "赵六", "delivery_date": "2024-06-01"}
        result = OrderDAO.create(data)
        assert result == 45

    def test_create_empty_delivery_date(self):
        """delivery_date 为空字符串 -> None"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.lastrowid = 46
        data = {"customer_name": "钱七", "delivery_date": ""}
        result = OrderDAO.create(data)
        assert result == 46

    def test_create_with_extra_params(self):
        """含额外字段 -> _build_extra_params 构建 extra_params JSON"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.lastrowid = 47
        data = {"customer_name": "孙八", "总宽": "1.2m", "表面处理": "抛光"}
        result = OrderDAO.create(data)
        assert result == 47
        # 取第1个 execute 调用（INSERT INTO orders）的 params
        call1 = self.mock_cursor.execute.call_args_list[0]
        params = call1[0][1]
        # extra_params 是最后一个参数（索引 21）
        extra_str = params[21]
        assert extra_str  # 非空字符串
        extra = json.loads(extra_str)
        assert extra["总宽"] == "1.2m"

    def test_create_default_status(self):
        """默认状态为 PENDING"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.lastrowid = 48
        data = {"customer_name": "周九"}
        result = OrderDAO.create(data)
        assert result == 48
        from constants import OrderStatus
        # 取第1个 execute 调用（INSERT INTO orders）的 params
        call1 = self.mock_cursor.execute.call_args_list[0]
        params = call1[0][1]
        # params 索引 18 = status
        assert params[18] == OrderStatus.PENDING.value


class TestUpdate:
    """
    OrderDAO.update (L100-188)

    Branch 矩阵:
      1. 正常更新, status 不变 -> 记录 UPDATE 日志
      2. 更新时 status 变化 -> 记录状态变更日志
      3. 更新时 old 行不存在 (old_status=None) -> status 用 data 的
      4. 异常 -> 回滚 + 返回 False
      5. finally 关闭连接
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

    def _make_order_row(self, status="待确认", order_no="PO-001"):
        return {"status": status, "order_no": order_no}

    def test_update_status_unchanged(self):
        """状态不变 -> 记录 UPDATE 日志"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        # 第1次 fetchone: 查旧状态
        # 第2次 execute: UPDATE
        # 第3次 fetchone: 查 order_no
        self.mock_cursor.fetchone.side_effect = [
            self._make_order_row("待确认", "PO-001"),
            self._make_order_row("待确认", "PO-001"),
        ]
        self.mock_cursor.rowcount = 1
        data = {"customer_name": "张三新", "status": "待确认"}
        result = OrderDAO.update(1, data)
        assert result is True
        # update 内部自调 commit, log_status_change 也调, 所以 >=1
        assert self.mock_conn.commit.call_count >= 1

    def test_update_status_changed(self):
        """状态变化 -> 记录状态变更日志"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            self._make_order_row("待确认", "PO-001"),
            self._make_order_row("进行中", "PO-001"),
        ]
        result = OrderDAO.update(1, {"status": "进行中", "customer_name": "张三"}, operator="质检员")
        assert result is True

    def test_update_no_old_status(self):
        """旧行不存在 status 字段 -> old_status = None -> 用 data 的"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"order_no": "PO-002"},  # 无 status 字段
            {"order_no": "PO-002"},  # 用于 order_no 查询
        ]
        result = OrderDAO.update(2, {"status": "生产中"})
        assert result is True

    def test_update_exception(self):
        """异常 -> 回滚 + 返回 False"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            self._make_order_row("待确认"),
            self._make_order_row("待确认"),
        ]
        self.mock_cursor.execute.side_effect = Exception("Update failed")
        result = OrderDAO.update(1, {"customer_name": "张三"})
        assert result is False
        self.mock_conn.rollback.assert_called_once()

    def test_update_finally_close(self):
        """异常时 finally 依然关闭连接"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            self._make_order_row("待确认"),
        ]
        self.mock_cursor.execute.side_effect = Exception("Boom")
        OrderDAO.update(1, {"customer_name": "张三"})
        assert self.mock_conn.close.call_count >= 1


class TestUpdateStatus:
    """
    OrderDAO.update_status (L190-242)

    Branch 矩阵:
      1. order_id 为空/0 -> 返回 False (L192-194)
      2. 订单不存在 -> 返回 False (L201-204)
      3. 正常状态变更 -> 返回 True (L207-234)
      4. 异常 -> 返回 False (L236-240)
      5. action_map 全覆盖
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

    def test_invalid_order_id(self):
        """order_id 为空/0/None -> 返回 False"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)

        result = OrderDAO.update_status(0, "进行中")
        assert result is False

    def test_order_not_found(self):
        """订单不存在 -> 返回 False"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.return_value = None
        result = OrderDAO.update_status(999, "进行中")
        assert result is False

    def test_normal_status_change(self):
        """正常状态变更 -> 返回 True"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"status": "待确认", "order_no": "PO-001"},
            {"status": "待确认", "order_no": "PO-001"},  # 第1个 execute 查旧状态后 cursor.close()
            # 第2个 cursor 的 fetchone 用于更新后查 order_no
            {"order_no": "PO-001"},
        ]
        self.mock_cursor.rowcount = 1
        result = OrderDAO.update_status(1, "进行中", operator="张三")
        assert result is True
        # update_status 内部自调 commit, log_status_change 也调, 所以 >=1
        assert self.mock_conn.commit.call_count >= 1
        # update_status + log_order_action 都调了 get_connection(), 所以 >=1
        assert self.mock_conn.close.call_count >= 1

    def test_status_action_map_create(self):
        """new_status='待确认' -> action_key='CREATE'"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"status": None, "order_no": "PO-001"},
            {"status": None, "order_no": "PO-001"},
            {"order_no": "PO-001"},
        ]
        self.mock_cursor.rowcount = 1
        result = OrderDAO.update_status(1, "待确认")
        assert result is True

    def test_status_action_map_archive(self):
        """new_status='已归档' -> action_key='ARCHIVE'"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"status": "已完成", "order_no": "PO-001"},
            {"status": "已完成", "order_no": "PO-001"},
            {"order_no": "PO-001"},
        ]
        self.mock_cursor.rowcount = 1
        result = OrderDAO.update_status(1, "已归档")
        assert result is True

    def test_status_action_map_cancel(self):
        """new_status='已取消' -> action_key='CANCEL'"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"status": "待确认", "order_no": "PO-001"},
            {"status": "待确认", "order_no": "PO-001"},
            {"order_no": "PO-001"},
        ]
        self.mock_cursor.rowcount = 1
        result = OrderDAO.update_status(1, "已取消")
        assert result is True

    def test_status_action_map_other(self):
        """不在 map 中的状态 -> action_key='UPDATE'"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"status": "待确认", "order_no": "PO-001"},
            {"status": "待确认", "order_no": "PO-001"},
            {"order_no": "PO-001"},
        ]
        self.mock_cursor.rowcount = 1
        result = OrderDAO.update_status(1, "待质检")
        assert result is True

    def test_exception(self):
        """异常 -> 返回 False"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = Exception("DB error")
        result = OrderDAO.update_status(1, "进行中")
        assert result is False

    def test_finally_close_connection(self):
        """finally 关闭连接"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.return_value = {"status": "待确认", "order_no": "PO-001"}
        self.mock_cursor.execute.side_effect = Exception("Boom")
        OrderDAO.update_status(1, "进行中")
        self.mock_conn.close.assert_called_once()


# ============================================================
#  P1 — 统计方法
# ============================================================

class TestGetBatchOrderStatistics:
    """
    OrderDAO.get_batch_order_statistics (L628-762)

    Branch 矩阵:
      1. order_ids 为空 -> 返回 {}
      2. 正常: 多表批量查询, 成功计算统计
      3. extra_params 是 JSON 字符串 -> 解析
      4. production_process: 从 extra_params.生产工艺 或 surface_treatment
      5. 有 confirmed_times 和 completed_times -> 计算 order_total_days
      6. 无 completed_times -> order_total_days 为 None
      7. 有 actual_start + actual_end -> 计算 production_total_days
      8. 有 completed_qty > 0 -> 计算 loss_rate
      9. op_time 字段测试 (字符串转换 datetime)
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

    def test_empty_ids(self):
        """order_ids 为空 -> 返回 {}"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        result = OrderDAO.get_batch_order_statistics([])
        assert result == {}

    def test_normal(self):
        """正常返回统计数据"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        # 4 次 execute 调用的返回
        self.mock_cursor.fetchall.side_effect = [
            # 1. 订单基本信息
            [{"id": 1, "unit": "米", "extra_params": '{"生产工艺":"编织"}', "surface_treatment": "抛光"}],
            # 2. status_logs 确认时间
            [{"record_id": 1, "created_at": "2024-01-01 08:00:00"}],
            # 3. status_logs 完成时间
            [{"record_id": 1, "created_at": "2024-01-10 08:00:00"}],
            # 4. production_orders
            [{"order_id": 1, "actual_start": "2024-01-02 08:00:00", "actual_end": "2024-01-08 18:00:00"}],
            # 5. process_records 统计
            [{"order_id": 1, "total_completed": 100, "total_qualified": 95}],
        ]
        result = OrderDAO.get_batch_order_statistics([1])
        assert 1 in result
        assert result[1]["unit"] == "米"
        assert result[1]["production_process"] == "编织"
        assert result[1]["order_total_days"] == 9  # 1月10日 - 1月1日
        assert result[1]["production_total_days"] == 6  # 1月2日 - 1月8日
        assert result[1]["loss_rate"] == 5.0  # (100-95)/100*100

    def test_no_completed_times(self):
        """无完成时间 -> order_total_days 为 None"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.side_effect = [
            [{"id": 1, "unit": "米", "extra_params": "", "surface_treatment": "抛光"}],
            [{"record_id": 1, "created_at": "2024-01-01 08:00:00"}],
            [],  # 无完成记录
            [],
            [],
        ]
        result = OrderDAO.get_batch_order_statistics([1])
        assert result[1]["order_total_days"] is None

    def test_no_loss_rate(self):
        """无 completed_qty -> loss_rate 为 None"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.side_effect = [
            [{"id": 1, "unit": "米", "extra_params": "", "surface_treatment": ""}],
            [],
            [],
            [],
            [{"order_id": 1, "total_completed": 0, "total_qualified": 0}],
        ]
        result = OrderDAO.get_batch_order_statistics([1])
        assert result[1]["loss_rate"] is None

    def test_extra_params_is_dict(self):
        """extra_params 已经 dict -> 不解析"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.side_effect = [
            [{"id": 1, "unit": "米", "extra_params": {}, "surface_treatment": "抛光"}],
            [],
            [],
            [],
            [],
        ]
        result = OrderDAO.get_batch_order_statistics([1])
        assert result[1]["unit"] == "米"
        # extra 无"生产工艺"，走 surface_treatment 回退
        assert result[1]["production_process"] == "抛光"

    def test_multiple_order_ids(self):
        """多个 order_id 批量查询"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.side_effect = [
            [{"id": 1, "unit": "米", "extra_params": "", "surface_treatment": ""},
             {"id": 2, "unit": "件", "extra_params": "", "surface_treatment": ""}],
            [], [], [], [],
        ]
        result = OrderDAO.get_batch_order_statistics([1, 2])
        assert len(result) == 2
        assert result[1]["unit"] == "米"
        assert result[2]["unit"] == "件"

    def test_extra_params_invalid_json(self):
        """extra_params 无效 JSON -> 异常捕获, extra = {}"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.side_effect = [
            [{"id": 1, "unit": "米", "extra_params": "{broken json", "surface_treatment": "抛光"}],
            [], [], [], [],
        ]
        result = OrderDAO.get_batch_order_statistics([1])
        assert result[1]["production_process"] == "抛光"


class TestGetOrderStatistics:
    """
    OrderDAO.get_order_statistics (L765-899)

    Branch 矩阵:
      1. 订单不存在 -> 返回默认值
      2. 正常: 完整订单统计 (确认/完成时间, 生产时间, 工序)
      3. extra 字符串解析
      4. 只有确认时间但无完成时间 -> order_total_days 为 None
      5. 无 production 记录 -> production_total_days 为 None
      6. 工序有空 start/end -> duration_days 为 None
      7. completed_qty > 0 -> pass_rate/loss_rate 计算
      8. completed_qty = 0 的工序
      9. 工序有 material_usage
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

    def test_order_not_found(self):
        """订单不存在 -> 返回默认值"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.return_value = None  # 第1次 fetchone -> WHERE id=
        result = OrderDAO.get_order_statistics(999)
        assert result["order_total_days"] is None
        assert result["production_total_days"] is None
        assert result["process_details"] == []
        self.mock_conn.close.assert_called_once()

    def test_normal(self):
        """正常: 完整订单统计"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            # 0: 订单基本信息
            {"id": 1, "unit": "米", "extra_params": '{"生产工艺":"编织"}', "surface_treatment": "抛光"},
            # 1: 确认日志
            {"created_at": "2024-01-01 08:00:00"},
            # 2: 完成日志
            {"created_at": "2024-01-10 18:00:00"},
            # 3: production 记录
            {"actual_start": "2024-01-02 08:00:00", "actual_end": "2024-01-08 18:00:00", "created_at": "2024-01-01"},
        ]
        self.mock_cursor.fetchall.return_value = [
            # process_records
            {"process_name": "编织", "start_time": "2024-01-02 08:00:00", "end_time": "2024-01-04 18:00:00",
             "completed_qty": 50, "qualified_qty": 48, "material_usage": 100.0,
             "planned_qty": 60, "status": "已完成"},
        ]

        result = OrderDAO.get_order_statistics(1)
        assert result["unit"] == "米"
        assert result["production_process"] == "编织"
        assert result["order_total_days"] == 9
        assert result["production_total_days"] == 6
        assert len(result["process_details"]) == 1
        p = result["process_details"][0]
        assert p["process_name"] == "编织"
        assert p["duration_days"] == 2
        assert p["pass_rate"] == 96.0  # 48/50*100
        assert p["loss_rate"] == 4.0  # (50-48)/50*100
        assert p["material_usage"] == 100.0
        assert p["planned_qty"] == 60
        assert result["loss_rate"] == 4.0

    def test_no_completion_time(self):
        """有确认时间但无完成时间 -> order_total_days 为 None"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"id": 1, "unit": "米", "extra_params": "", "surface_treatment": ""},
            {"created_at": "2024-01-01 08:00:00"},  # 确认时间
            None,  # 无完成时间
            None,  # 无 production
        ]
        self.mock_cursor.fetchall.return_value = []
        result = OrderDAO.get_order_statistics(1)
        assert result["order_total_days"] is None

    def test_no_production_record(self):
        """无 production 记录 -> production_total_days 为 None"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"id": 1, "unit": "米", "extra_params": "", "surface_treatment": ""},
            None,  # 无确认
            None,  # 无完成
            None,  # 无 production
        ]
        self.mock_cursor.fetchall.return_value = []
        result = OrderDAO.get_order_statistics(1)
        assert result["production_total_days"] is None

    def test_process_no_start_end(self):
        """工序无 start_time/end_time -> duration_days 为 None"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"id": 1, "unit": "米", "extra_params": "", "surface_treatment": ""},
            None, None, None,
        ]
        self.mock_cursor.fetchall.return_value = [
            {"process_name": "裁剪", "start_time": None, "end_time": None,
             "completed_qty": 0, "qualified_qty": 0, "material_usage": None,
             "planned_qty": None, "status": ""},
        ]
        result = OrderDAO.get_order_statistics(1)
        assert len(result["process_details"]) == 1
        p = result["process_details"][0]
        assert p["duration_days"] is None
        assert p["pass_rate"] is None
        assert p["loss_rate"] is None

    def test_process_no_completed_qty(self):
        """工序 completed_qty=0 -> pass_rate/loss_rate 为 None"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"id": 1, "unit": "米", "extra_params": "", "surface_treatment": ""},
            None, None, None,
        ]
        self.mock_cursor.fetchall.return_value = [
            {"process_name": "测试", "start_time": "2024-01-01 00:00:00", "end_time": "2024-01-01 00:00:00",
             "completed_qty": 0, "qualified_qty": 0, "material_usage": None,
             "planned_qty": None, "status": ""},
        ]
        result = OrderDAO.get_order_statistics(1)
        p = result["process_details"][0]
        assert p["duration_days"] == 0  # same day
        assert p["pass_rate"] is None
        assert p["loss_rate"] is None
        assert result["loss_rate"] is None  # total_completed=0

    def test_process_with_material_usage(self):
        """工序含 material_usage 和 status"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"id": 1, "unit": "件", "extra_params": "", "surface_treatment": ""},
            None, None, None,
        ]
        self.mock_cursor.fetchall.return_value = [
            {"process_name": "焊接", "start_time": None, "end_time": None,
             "completed_qty": 10, "qualified_qty": 10, "material_usage": 50.5,
             "planned_qty": 20, "status": "进行中"},
        ]
        result = OrderDAO.get_order_statistics(1)
        p = result["process_details"][0]
        assert p["material_usage"] == 50.5
        assert p["planned_qty"] == 20
        assert p["status"] == "进行中"
        assert p["pass_rate"] == 100.0

    def test_extra_params_invalid_json(self):
        """extra_params 无效 JSON -> 异常捕获"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchone.side_effect = [
            {"id": 1, "unit": "米", "extra_params": "{bad json", "surface_treatment": ""},
            None, None, None,
        ]
        self.mock_cursor.fetchall.return_value = []
        result = OrderDAO.get_order_statistics(1)
        assert result["production_process"] is None


class TestBatchGetOrderStatistics:
    """
    OrderDAO.batch_get_order_statistics (L902-963)

    Branch 矩阵:
      1. order_ids 为空 -> 返回 {}
      2. 正常: 批量 SQL 查询返回统计
      3. extra_params 字符串解析
      4. extra_params 已是 dict
      5. extra_params 无效 JSON -> 异常捕获
      6. production_process: 从 extra_params.生产工艺 获取
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

    def test_empty_ids(self):
        """order_ids 为空 -> 返回 {}"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        result = OrderDAO.batch_get_order_statistics([])
        assert result == {}

    def test_normal(self):
        """正常: SQL 返回统计值"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = [
            {"id": 1, "unit": "米", "extra_params": '{"生产工艺":"编织"}',
             "order_total_days": 9, "production_total_days": 6, "loss_rate": 5.0},
        ]
        result = OrderDAO.batch_get_order_statistics([1])
        assert 1 in result
        assert result[1]["unit"] == "米"
        assert result[1]["production_process"] == "编织"
        assert result[1]["order_total_days"] == 9
        assert result[1]["production_total_days"] == 6
        assert result[1]["loss_rate"] == 5.0
        assert result[1]["process_times"] == []
        assert result[1]["process_details"] == []
        self.mock_conn.close.assert_called_once()

    def test_extra_params_is_dict(self):
        """extra_params 已是 dict"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = [
            {"id": 1, "unit": "件", "extra_params": {},
             "order_total_days": None, "production_total_days": None, "loss_rate": None},
        ]
        result = OrderDAO.batch_get_order_statistics([1])
        assert result[1]["production_process"] is None

    def test_extra_params_invalid_json(self):
        """extra_params 无效 JSON"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = [
            {"id": 1, "unit": "米", "extra_params": "{invalid",
             "order_total_days": None, "production_total_days": None, "loss_rate": None},
        ]
        result = OrderDAO.batch_get_order_statistics([1])
        assert result[1]["production_process"] is None

    def test_no_production_process(self):
        """extra_params 无生产工艺"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = [
            {"id": 1, "unit": "米", "extra_params": '{"表面处理":"抛光"}',
             "order_total_days": None, "production_total_days": None, "loss_rate": None},
        ]
        result = OrderDAO.batch_get_order_statistics([1])
        assert result[1]["production_process"] is None  # 无"生产工艺" key

    def test_multiple_orders(self):
        """多个订单"""
        OrderDAO = _patch_and_import_order(self._patchers, self.mock_conn)
        self.mock_cursor.fetchall.return_value = [
            {"id": 1, "unit": "米", "extra_params": '{"生产工艺":"编织"}',
             "order_total_days": 10, "production_total_days": 8, "loss_rate": 0.05},
            {"id": 2, "unit": "件", "extra_params": '{"表面处理":"抛光"}',
             "order_total_days": 5, "production_total_days": None, "loss_rate": None},
        ]
        result = OrderDAO.batch_get_order_statistics([1, 2])
        assert len(result) == 2
        assert result[1]["unit"] == "米"
        assert result[1]["production_process"] == "编织"
        assert result[1]["loss_rate"] == 0.05
        assert result[2]["unit"] == "件"
        assert result[2]["production_process"] is None
        assert result[2]["loss_rate"] is None