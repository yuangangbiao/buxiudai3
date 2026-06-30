# -*- coding: utf-8 -*-
"""InventoryDAO 深度测试 — 覆盖 create / warning_only / search_by_material / get_records else 分支等 missing 行"""
from unittest.mock import patch, MagicMock
import pytest


# ============================================================
# test_create — 覆盖 inventory.py 第 14-37 行
# ============================================================

class TestInventoryDAOCreate:
    """create 方法测试"""

    def test_create_success(self, mock_db):
        """正常创建库存条目，返回 lastrowid"""
        conn, cursor = mock_db
        cursor.lastrowid = 42
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.create({
                "material_name": "不锈钢丝",
                "material_type": "304",
                "specification": "1.0mm",
                "quantity": 100,
                "unit": "kg",
                "unit_price": 25.0,
                "warehouse": "主仓库",
                "warning_qty": 10,
                "remark": "测试创建"
            })
        assert result == 42
        # 验证 SQL 执行
        sql = cursor.execute.call_args[0][0]
        assert "INSERT INTO inventory" in sql
        # 验证 conn.commit 被调用
        conn.commit.assert_called_once()
        # 验证 cursor.close 被调用
        cursor.close.assert_called_once()
        # 验证 conn.close 被调用
        conn.close.assert_called_once()

    def test_create_default_values(self, mock_db):
        """创建库存条目使用默认值"""
        conn, cursor = mock_db
        cursor.lastrowid = 99
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.create({
                "material_name": "测试材料"
            })
        assert result == 99
        # 获取 SQL 参数
        args = cursor.execute.call_args[0][1]
        assert args[0] == "测试材料"
        assert args[1] == ""  # material_type 默认
        assert args[2] == ""  # specification 默认
        assert args[3] == 0.0  # quantity 默认
        assert args[4] == "kg"  # unit 默认
        assert args[5] == 0.0  # unit_price 默认
        assert args[6] == "主仓库"  # warehouse 默认
        assert args[7] == 50.0  # warning_qty 默认（STOCK_WARNING_THRESHOLD=50）
        assert args[8] == ""  # remark 默认
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    def test_create_rollback_on_exception(self, mock_db):
        """数据库异常时回滚"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("DB Error")
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            with pytest.raises(Exception):
                InventoryDAO.create({
                    "material_name": "错误材料"
                })
        # 异常下 conn.commit 不会被调用
        conn.commit.assert_not_called()
        # finally 块确保 conn.close 被调用
        conn.close.assert_called_once()

    def test_create_empty_data(self, mock_db):
        """传空 dict 全部用默认值"""
        conn, cursor = mock_db
        cursor.lastrowid = 0
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.create({})
        assert result == 0
        args = cursor.execute.call_args[0][1]
        assert args[0] == ""  # material_name
        assert args[8] == ""  # remark


# ============================================================
# test_get_all — 覆盖第 138 行 warning_only 分支
# ============================================================

class TestInventoryDAOGetAll:
    """get_all 方法测试"""

    def test_get_all_no_filters(self, mock_db):
        """不传 filters，返回全部"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [
            {"id": 1, "material_name": "丝", "quantity": 100},
            {"id": 2, "material_name": "带", "quantity": 50},
        ]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_all()
        assert len(result) == 2
        # SQL 不包含 WHERE 过滤条件
        sql = cursor.execute.call_args[0][0]
        assert "WHERE 1=1" in sql
        assert "AND" not in sql or "ORDER BY" in sql.split("AND")[-1]
        conn.close.assert_called_once()

    def test_get_all_with_material_type(self, mock_db):
        """按物料类型过滤"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"id": 1, "material_name": "304丝"}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_all(filters={"material_type": "304"})
        assert len(result) == 1
        sql, params = cursor.execute.call_args[0]
        assert "material_type=%s" in sql
        assert "304" in params
        # 确认没有 warning 条件
        assert "quantity <= warning_qty" not in sql

    def test_get_all_skip_all_type(self, mock_db):
        """material_type='全部' 时跳过 type 过滤"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"id": 1}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_all(filters={"material_type": "全部"})
        sql = cursor.execute.call_args[0][0]
        assert "material_type=%s" not in sql

    def test_get_all_with_keyword(self, mock_db):
        """按 keyword 模糊搜索"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"id": 1}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_all(filters={"keyword": "不锈钢"})
        sql, params = cursor.execute.call_args[0]
        assert "LIKE %s" in sql
        assert "%不锈钢%" in params

    def test_get_all_with_warning_only(self, mock_db):
        """warning_only=True 分支 — 覆盖第 138 行"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = []
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_all(filters={"warning_only": True})
        sql = cursor.execute.call_args[0][0]
        assert "quantity <= warning_qty" in sql
        assert result == []

    def test_get_all_combined_filters(self, mock_db):
        """多条件组合：material_type + keyword + warning_only"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"id": 1}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_all(filters={
                "material_type": "304",
                "keyword": "丝",
                "warning_only": True
            })
        sql, params = cursor.execute.call_args[0]
        assert "material_type=%s" in sql
        assert "LIKE %s" in sql
        assert "quantity <= warning_qty" in sql
        assert len(result) == 1
        conn.close.assert_called_once()

    def test_get_all_empty_results(self, mock_db):
        """无结果返回空列表"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = []
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_all(filters={"material_type": "NONEXIST"})
        assert result == []

    def test_get_all_exception_closes_conn(self, mock_db):
        """异常时 finally 关闭连接"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Query Error")
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            with pytest.raises(Exception):
                InventoryDAO.get_all()
        conn.close.assert_called_once()


# ============================================================
# test_get_records — 覆盖第 166-175 行（inv_id=None 分支）
# ============================================================

class TestInventoryDAOGetRecords:
    """get_records 方法测试"""

    def test_get_records_with_inv_id(self, mock_db):
        """指定 inv_id 时走 JOIN 过滤查询"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"id": 1, "material_name": "丝", "record_type": "入库"}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_records(inv_id=5)
        sql, params = cursor.execute.call_args[0]
        assert "inventory_id=%s" in sql
        assert 5 in params
        assert len(result) == 1

    def test_get_records_without_inv_id(self, mock_db):
        """不传 inv_id 时查所有记录 — 覆盖第 166-175 行"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [
            {"id": 1, "material_name": "丝", "record_type": "入库"},
            {"id": 2, "material_name": "带", "record_type": "出库"},
        ]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_records()
        sql, params = cursor.execute.call_args[0]
        # SQL 不应包含 inventory_id 过滤
        assert "inventory_id=%s" not in sql
        assert "inventory_id=?" not in sql
        # 应该有 LIMIT
        assert "LIMIT" in sql
        assert 50 in params  # 默认 limit
        assert len(result) == 2
        conn.close.assert_called_once()

    def test_get_records_custom_limit(self, mock_db):
        """自定义 limit"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = []
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_records(inv_id=1, limit=10)
        _, params = cursor.execute.call_args[0]
        assert 10 in params
        assert result == []

    def test_get_records_empty(self, mock_db):
        """无记录返回空列表"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = []
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_records()
        assert result == []


# ============================================================
# test_search_by_material — 覆盖第 248-268 行
# ============================================================

class TestInventoryDAOSearchByMaterial:
    """search_by_material 方法测试"""

    def test_search_by_material_name_only(self, mock_db):
        """仅按物料名称搜索"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [
            {"material_name": "不锈钢丝", "current_qty": 100, "unit": "kg", "warehouse": "主仓库", "remark": ""}
        ]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.search_by_material(material_name="不锈钢")
        sql, params = cursor.execute.call_args[0]
        assert "material_name LIKE %s" in sql
        assert "%不锈钢%" in params
        assert "specification LIKE %s" not in sql
        assert "unit=%s" not in sql
        assert len(result) == 1
        assert result[0]["material_name"] == "不锈钢丝"

    def test_search_by_material_with_spec(self, mock_db):
        """按名称+规格搜索"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"material_name": "1.0mm丝", "current_qty": 50}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.search_by_material(material_name="丝", spec="1.0mm")
        sql, params = cursor.execute.call_args[0]
        assert "material_name LIKE %s" in sql
        assert "specification LIKE %s" in sql
        assert "unit=%s" not in sql
        assert len(result) == 1

    def test_search_by_material_full_params(self, mock_db):
        """按名称+规格+单位同时搜索"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"material_name": "304丝", "current_qty": 200}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.search_by_material(material_name="丝", spec="1.0", unit="kg")
        sql, params = cursor.execute.call_args[0]
        assert "material_name LIKE %s" in sql
        assert "specification LIKE %s" in sql
        assert "unit=%s" in sql
        assert "kg" in params

    def test_search_by_material_with_spec_only(self, mock_db):
        """仅传 spec（material_name 为空字符串），应跳过 name 条件"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"material_name": "带", "current_qty": 30}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            # material_name 默认值 ""，bool("") == False，所以跳过 name 条件
            result = InventoryDAO.search_by_material(material_name="", spec="5mm")
        sql = cursor.execute.call_args[0][0]
        assert "material_name LIKE %s" not in sql
        assert "specification LIKE %s" in sql

    def test_search_by_material_no_match(self, mock_db):
        """无匹配返回空列表"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = []
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.search_by_material(material_name="不存在")
        assert result == []

    def test_search_by_material_empty_name(self, mock_db):
        """空字符串 material_name（不传过滤条件时）返回全量"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"material_name": "全部物料", "current_qty": 999}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.search_by_material(material_name="")
        sql = cursor.execute.call_args[0][0]
        assert "WHERE 1=1" in sql
        # 不应有额外 AND 条件
        assert "AND material_name" not in sql
        assert len(result) == 1

    def test_search_by_material_with_unit_only(self, mock_db):
        """仅传 unit"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = []
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.search_by_material(material_name="", unit="kg")
        sql = cursor.execute.call_args[0][0]
        assert "AND material_name" not in sql
        assert "AND specification LIKE" not in sql
        assert "unit=%s" in sql


# ============================================================
# test_stock_out — 覆盖第 104-105 行库存不足分支
# ============================================================

class TestInventoryDAOStockOut:
    """stock_out 方法测试 — 补全库存不足路径"""

    def test_stock_out_success(self, mock_db):
        """正常出库"""
        conn, cursor = mock_db
        # fetchone 返回当前库存
        cursor.fetchone.side_effect = [
            (100.0,),   # SELECT quantity
            None,       # 后续 fetchone 不需要
        ]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.stock_out(inv_id=1, qty=30, operator="张三", remark="领料")
        assert result is True
        # 验证 UPDATE 执行
        update_sql = None
        for call in cursor.execute.call_args_list:
            if "UPDATE inventory" in call[0][0]:
                update_sql = call[0][0]
                break
        assert update_sql is not None
        # 验证 INSERT 记录
        insert_sql = None
        for call in cursor.execute.call_args_list:
            if "INSERT INTO inventory_records" in call[0][0]:
                insert_sql = call[0]
                break
        assert insert_sql is not None
        assert "出库" in str(insert_sql)
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    def test_stock_out_insufficient(self, mock_db):
        """库存不足时返回 False — 覆盖第 104-105 行"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = (10.0,)  # 仅 10，出库 30 不够
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.stock_out(inv_id=1, qty=30)
        assert result is False
        # 库存不足时不应执行 UPDATE
        update_calls = [c for c in cursor.execute.call_args_list if "UPDATE inventory" in c[0][0]]
        assert len(update_calls) == 0
        # 也不应 INSERT 记录
        insert_calls = [c for c in cursor.execute.call_args_list if "INSERT" in c[0][0]]
        assert len(insert_calls) == 0
        conn.close.assert_called_once()


# ============================================================
# test_utils — 覆盖 update / get_warning_items / get_dashboard_overview / get_low_inventory_alerts 的 finally 和边界
# ============================================================

class TestInventoryDAOUtils:
    """其他方法的边界测试"""

    def test_update_success(self, mock_db):
        """正常更新"""
        conn, cursor = mock_db
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.update(inv_id=1, data={"material_name": "新名称"})
        assert result is True
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    def test_update_exception_closes_conn(self, mock_db):
        """update 异常时关闭连接"""
        conn, cursor = mock_db
        cursor.execute.side_effect = Exception("Update Error")
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            with pytest.raises(Exception):
                InventoryDAO.update(inv_id=1, data={"material_name": "x"})
        conn.close.assert_called_once()

    def test_stock_in_success(self, mock_db):
        """正常入库"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = (50.0,)
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.stock_in(inv_id=1, qty=20, operator="李四")
        assert result is True
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

    def test_stock_in_no_existing_row(self, mock_db):
        """入库时物料不存在（fetchone 返回 None）"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = None  # 物料不存在
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.stock_in(inv_id=999, qty=20)
        assert result is True
        # before_qty 应为 0
        conn.close.assert_called_once()

    def test_stock_in_default_order_id(self, mock_db):
        """stock_in 不传 order_id 使用 None"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = (100.0,)
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.stock_in(inv_id=1, qty=10)
        assert result is True
        conn.close.assert_called_once()

    def test_get_warning_items(self, mock_db):
        """获取预警项"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"id": 1, "quantity": 5, "warning_qty": 10}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_warning_items()
        assert len(result) == 1
        conn.close.assert_called_once()

    def test_get_warning_items_empty(self, mock_db):
        """无预警项"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = []
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_warning_items()
        assert result == []

    def test_get_dashboard_overview(self, mock_db):
        """获取大屏概览"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [
            {"material_name": "丝", "quantity": 100, "unit": "kg", "safe_stock": 10}
        ]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_dashboard_overview()
        assert len(result) == 1
        assert result[0]["safe_stock"] == 10
        conn.close.assert_called_once()

    def test_get_low_inventory_alerts(self, mock_db):
        """获取低库存告警"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"material_name": "丝", "quantity": 3, "warning_qty": 10}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_low_inventory_alerts(limit=5)
        sql, params = cursor.execute.call_args[0]
        assert "LIMIT" in sql
        assert 5 in params
        assert len(result) == 1
        conn.close.assert_called_once()

    def test_get_low_inventory_alerts_default_limit(self, mock_db):
        """使用默认 limit=3"""
        conn, cursor = mock_db
        cursor.fetchall.return_value = []
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_low_inventory_alerts()
        _, params = cursor.execute.call_args[0]
        assert 3 in params
        assert result == []

    def test_stock_out_exception(self, mock_db):
        """stock_out 异常时关闭连接"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = (100.0,)
        # 第1-2次 execute （SELECT/INSERT）正常，其余抛异常
        # stock_out 流程：SELECT → close → conn.cursor (新cursor) → UPDATE → close → conn.cursor → INSERT
        # 每个 cursor.execute 调用都会走 side_effect
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            sql = args[0][0] if args and isinstance(args[0], (list, tuple)) else str(args[0])
            if "UPDATE" in sql:
                raise Exception("Update Error")
            return None

        cursor.execute.side_effect = side_effect
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            with pytest.raises(Exception):
                InventoryDAO.stock_out(inv_id=1, qty=10)
        conn.close.assert_called_once()

    def test_stock_in_exception(self, mock_db):
        """stock_in 异常时关闭连接"""
        conn, cursor = mock_db
        cursor.fetchone.return_value = (50.0,)
        cursor.execute.side_effect = Exception("Insert Error")
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            with pytest.raises(Exception):
                InventoryDAO.stock_in(inv_id=1, qty=10)
        conn.close.assert_called_once()
