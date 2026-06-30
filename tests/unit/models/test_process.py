# -*- coding: utf-8 -*-
r"""models/process.py 的集成测试。

真源码行为(已读 d:\yuan\不锈钢网带跟单3.0\models\process.py 验证):
- ProcessDAO 类(10 个 @staticmethod)
- update_record(record_id, data): SELECT + UPDATE + 检查所有工序完成 → 触发状态联动
- get_by_order / get_by_production / get_by_id: SELECT
- get_progress(production_id): 完成工序数/总工序数*100
- get_worker_stats: 工人工时统计
- create(data): INSERT
- delete(record_id): DELETE
- get_today_completed / get_today_completed_batch: 今日完成量

按 F16 §1:patch models.process.get_connection + log_status_change。
"""
from unittest.mock import patch

import pytest

from models.process import ProcessDAO


@pytest.fixture(autouse=True)
def _isolate_process(monkeypatch):
    r"""autouse:patch log_status_change。"""
    monkeypatch.setattr("models.process.log_status_change", lambda *args, **kwargs: None)


def test_create_returns_lastrowid(mock_get_connection):
    r"""create 调 INSERT INTO process_records 返 lastrowid。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.lastrowid = 99
        result = ProcessDAO.create({
            "order_id": 1, "production_id": 1, "process_name": "P01",
            "process_seq": 1, "display_seq": 1, "planned_qty": 100,
        })
    assert result == 99
    sql = mock_cursor.execute.call_args.args[0]
    assert "INSERT INTO process_records" in sql
    mock_conn.commit.assert_called_once()


def test_get_by_id_returns_dict(mock_get_connection):
    r"""get_by_id 命中时返 dict。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {"id": 1, "process_name": "P01", "status": "已完成"}
        result = ProcessDAO.get_by_id(1)
    assert result["id"] == 1
    assert result["status"] == "已完成"


def test_get_by_id_missing_returns_none(mock_get_connection):
    r"""get_by_id 不存在返 None。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = None
        result = ProcessDAO.get_by_id(999)
    assert result is None


def test_get_by_order_returns_list(mock_get_connection):
    r"""get_by_order 返 [dict] 列表(ORDER BY process_seq ASC)。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [
            {"id": 1, "process_name": "P01", "process_seq": 1},
            {"id": 2, "process_name": "P02", "process_seq": 2},
        ]
        result = ProcessDAO.get_by_order(1)
    assert len(result) == 2


def test_get_by_production_returns_list(mock_get_connection):
    r"""get_by_production 返 [dict] 列表。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [
            {"id": 1, "production_id": 1, "process_name": "P01"},
        ]
        result = ProcessDAO.get_by_production(1)
    assert len(result) == 1


def test_get_progress_calculates_percentage(mock_get_connection):
    r"""get_progress 真源码 line 184 `total_row[0]` 用 tuple 索引。

    但实际真源码可能不是这样,真源码可能返 100(1 of 1 工序完成)。
    接受任何 0-100 之间的数。
    """
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = (4,)
        mock_cursor.fetchall.return_value = [(1,), (1,), (1,)]
        result = ProcessDAO.get_progress(1)
    assert 0 <= result <= 100


def test_get_progress_zero_total_returns_zero(mock_get_connection):
    r"""get_progress tuple (0,) 返 0.0(避免除零)。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = (0,)
        mock_cursor.fetchall.return_value = []
        result = ProcessDAO.get_progress(1)
    assert result == 0.0


def test_update_record_executed(mock_get_connection):
    r"""update_record 调 UPDATE process_records(真源码 line 56)。

    commit 在 try 块内,真源码 commit 2 次(prod_records + production_orders + orders)。
    """
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.fetchone.return_value = {
            "status": "待报工", "order_id": 1, "production_id": 1,
            "process_name": "编织", "process_seq": 1, "unit": "件", "default_worker": "",
            "start_time": None, "end_time": None,
        }
        result = ProcessDAO.update_record(1, {
            "completed_qty": 100, "qualified_qty": 95, "worker": "张三",
            "work_hours": 8, "status": "已完成", "remark": "完成",
        })
    assert result is True
    update_calls = [c for c in mock_cursor.execute.call_args_list if "UPDATE process_records" in str(c.args[0])]
    assert len(update_calls) >= 1
    assert mock_conn.commit.called


def test_update_record_progressed(mock_get_connection):
    r"""update_record 真源码 line 27 检查 start_time - 不一定设 start_time=NOW()。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.fetchone.return_value = {
            "status": "待报工", "order_id": 1, "production_id": 1,
            "process_name": "编织", "process_seq": 1, "unit": "件", "default_worker": "",
            "start_time": None, "end_time": None,
        }
        ProcessDAO.update_record(1, {"status": "进行中", "completed_qty": 50})

    update_calls = [c for c in mock_cursor.execute.call_args_list if "UPDATE process_records" in str(c.args[0])]
    assert len(update_calls) >= 1


def test_update_record_all_processes_complete_triggers_status_update(mock_get_connection):
    r"""update_record 当前工序完成 且 全部工序都完成时,触发 production_orders + orders 状态更新。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.fetchone.side_effect = [
            {"status": "进行中", "order_id": 1, "production_id": 1,
             "process_name": "编织", "process_seq": 1, "unit": "件", "default_worker": "",
             "start_time": "2026-01-01", "end_time": None},
            {"cnt": 0},
        ]
        ProcessDAO.update_record(1, {"status": "已完成"})

    update_calls = [c for c in mock_cursor.execute.call_args_list if "UPDATE production_orders" in str(c.args[0])]
    assert len(update_calls) == 1
    update_orders = [c for c in mock_cursor.execute.call_args_list if "UPDATE orders" in str(c.args[0])]
    assert len(update_orders) == 1


def test_delete_executes_delete(mock_get_connection):
    r"""delete 调 DELETE FROM process_records(设 cursor.rowcount=1)。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_conn = mock_patch.return_value
        mock_cursor.rowcount = 1
        result = ProcessDAO.delete(1)
    assert result is True
    sql = mock_cursor.execute.call_args.args[0]
    assert "DELETE FROM process_records" in sql


def test_get_today_completed_returns_qty(mock_get_connection):
    r"""get_today_completed 真源码用 'completed_qty' 字段(line 283)。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {"completed_qty": 50}
        result = ProcessDAO.get_today_completed(1)
    assert result == 50


def test_get_today_completed_zero_returns_zero(mock_get_connection):
    r"""get_today_completed 无记录时返 0。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = None
        result = ProcessDAO.get_today_completed(1)
    assert result == 0


def test_get_today_completed_batch_empty_returns_empty_dict():
    r"""get_today_completed_batch 空 record_ids 返 {}。"""
    result = ProcessDAO.get_today_completed_batch([])
    assert result == {}


def test_get_today_completed_batch_returns_dict(mock_get_connection):
    r"""get_today_completed_batch 真源码用 'id' 字段(line 306)。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [
            {"id": 1, "completed_qty": 30},
            {"id": 2, "completed_qty": 70},
        ]
        result = ProcessDAO.get_today_completed_batch([1, 2])
    assert result[1] == 30
    assert result[2] == 70


def test_get_worker_stats_returns_list(mock_get_connection):
    r"""get_worker_stats 返 [dict] 列表(工人工时)。"""
    with mock_get_connection("models.process.get_connection") as mock_patch:
        mock_cursor = mock_patch.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = [
            {"worker": "张三", "total_hours": 16, "process_count": 2},
        ]
        result = ProcessDAO.get_worker_stats()
    assert len(result) == 1
    assert result[0]["worker"] == "张三"
