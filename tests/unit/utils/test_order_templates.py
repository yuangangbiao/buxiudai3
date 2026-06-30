# -*- coding: utf-8 -*-
"""
测试 utils/order_templates.py - 订单模板和自定义参数管理
覆盖目标：20% → 100%
"""
import sys, os, json, pytest
from unittest.mock import patch, MagicMock


def make_mock_cursor(rows=None, rowcount=1):
    cursor = MagicMock()
    if rows is not None:
        cursor.fetchall.return_value = rows
    else:
        cursor.fetchall.return_value = []
    cursor.fetchone.return_value = rows[0] if rows else None
    cursor.rowcount = rowcount
    return cursor


# ══════════════════════════════════════════════════════════════
# 1. DIM_FIELDS / MATERIAL_FIELDS / SURFACE_FIELD 数据完整性
# ══════════════════════════════════════════════════════════════

class TestDataConstants:
    """常量数据完整性测试"""

    def test_dim_fields_structure(self):
        from utils.order_templates import DIM_FIELDS
        assert len(DIM_FIELDS) == 42
        required_fields = ['总宽', '网带宽度', '钢丝直径', '总长度']
        for req in required_fields:
            assert any(f['key'] == req and f.get('required') for f in DIM_FIELDS), \
                f"必需字段 {req} 应标记 required"

    def test_dim_fields_groups(self):
        from utils.order_templates import DIM_FIELDS
        groups = {f['group'] for f in DIM_FIELDS}
        assert '宽度类' in groups
        assert '厚度/直径' in groups
        assert '间距类' in groups
        assert '长度类' in groups
        assert '数量类' in groups

    def test_material_fields_structure(self):
        from utils.order_templates import MATERIAL_FIELDS
        assert len(MATERIAL_FIELDS) == 10
        for f in MATERIAL_FIELDS:
            assert f['type'] == 'dropdown'
            assert f['group'] == '材质类'

    def test_surface_field(self):
        from utils.order_templates import SURFACE_FIELD
        assert len(SURFACE_FIELD) == 1
        assert SURFACE_FIELD[0]['key'] == '表面处理'

    def test_surface_opts(self):
        from utils.order_templates import SURFACE_OPTS
        assert '无处理' in SURFACE_OPTS
        assert '镀锌' in SURFACE_OPTS
        assert '其他' in SURFACE_OPTS
        assert len(SURFACE_OPTS) == 8

    def test_material_opts(self):
        from utils.order_templates import MATERIAL_OPTS
        assert '304不锈钢' in MATERIAL_OPTS
        assert '其他' in MATERIAL_OPTS
        assert len(MATERIAL_OPTS) == 10


# ══════════════════════════════════════════════════════════════
# 2. 纯函数（无 DB 依赖）
# ══════════════════════════════════════════════════════════════

class TestPureFunctions:
    """无需 mock 的纯函数"""

    def test_get_common_fields(self):
        from utils.order_templates import get_common_fields
        fields = get_common_fields()
        assert len(fields) == 8
        keys = [f['key'] for f in fields]
        assert 'customer_name' in keys
        assert 'quantity' in keys
        assert 'material' in keys
        # 验证 customer_name 和 quantity 为 required
        customer = next(f for f in fields if f['key'] == 'customer_name')
        assert customer['required'] is True
        qty = next(f for f in fields if f['key'] == 'quantity')
        assert qty['required'] is True

    def test_get_remark_fields(self):
        from utils.order_templates import get_remark_fields
        fields = get_remark_fields()
        assert len(fields) == 2
        assert fields[0]['key'] == 'remark'
        assert fields[1]['key'] == 'product_remark'

    def test_get_all_product_types(self):
        """get_all_product_types 依赖 DB，单独测"""
        pass  # 见 TestDatabaseFunctions

    def test_get_custom_material_params(self):
        """get_custom_material_params 依赖 get_custom_params"""
        pass  # 见 TestCustomParams

    def test_get_custom_all_params(self):
        from utils.order_templates import get_custom_all_params, get_custom_params
        # 验证 get_custom_all_params 调用 get_custom_params
        with patch('utils.order_templates.get_custom_params', return_value=[{'key': '测试'}]) as mock_gp:
            result = get_custom_all_params()
        assert result == [{'key': '测试'}]
        mock_gp.assert_called_once()

    def test_get_custom_dim_params(self):
        from utils.order_templates import get_custom_dim_params, get_custom_params
        with patch('utils.order_templates.get_custom_params', return_value=[{'key': '测试'}]) as mock_gp:
            result = get_custom_dim_params()
        assert result == [{'key': '测试'}]
        mock_gp.assert_called_once()


# ══════════════════════════════════════════════════════════════
# 3. get_surface_field（依赖 get_surface_treatment_options）
# ══════════════════════════════════════════════════════════════

class TestGetSurfaceField:
    """通过 mock custom_types.get_surface_treatment_options"""

    def test_returns_options(self):
        from utils.order_templates import get_surface_field
        with patch('utils.custom_types.get_surface_treatment_options',
                   return_value=['镀锌', '抛光']):
            result = get_surface_field()
        assert len(result) == 1
        assert result[0]['key'] == '表面处理'
        assert result[0]['type'] == 'combo_editable'
        assert result[0]['options'] == ['镀锌', '抛光']

    def test_no_options(self):
        from utils.order_templates import get_surface_field
        with patch('utils.custom_types.get_surface_treatment_options',
                   return_value=[]):
            result = get_surface_field()
        assert result[0]['options'] == []


# ══════════════════════════════════════════════════════════════
# 4. get_preset_fields（无 DB 依赖，纯函数）
# ══════════════════════════════════════════════════════════════

class TestGetPresetFields:
    """预置字段配置"""

    def test_eyeglass_net(self):
        from utils.order_templates import get_preset_fields, DIM_FIELDS
        result = get_preset_fields('眼镜网带')
        assert len(result['dim_fields']) == 4
        keys = [f['key'] for f in result['dim_fields']]
        assert '总宽' in keys
        assert '钢丝直径' in keys
        assert '加强筋数量' in keys
        assert '节距' in keys

    def test_herringbone_net(self):
        from utils.order_templates import get_preset_fields
        result = get_preset_fields('人字形网带')
        keys = [f['key'] for f in result['dim_fields']]
        assert '总宽' in keys
        assert '钢丝直径' in keys
        assert '目数' in keys
        assert '总长度' in keys

    def test_unknown_type(self):
        from utils.order_templates import get_preset_fields, DIM_FIELDS, MATERIAL_FIELDS
        result = get_preset_fields('未知类型')
        assert len(result['dim_fields']) == 5
        assert result['dim_fields'] == DIM_FIELDS[:5]
        assert result['mat_fields'] == MATERIAL_FIELDS


# ══════════════════════════════════════════════════════════════
# 5. DB 操作函数（模板管理）
# ══════════════════════════════════════════════════════════════

class TestTemplateDatabaseFunctions:
    """mock _get_db 测试模板 CRUD"""

    def make_db_mocks(self, cursor):
        """创建 mock 的 _get_db 调用"""
        patcher = patch('utils.order_templates._get_db')
        mock_get_db = patcher.start()
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        return patcher, mock_conn, cursor

    # ─── get_template_names ───

    def test_get_template_names_empty(self):
        from utils.order_templates import get_template_names
        cursor = make_mock_cursor([])
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            result = get_template_names('眼镜网带')
            assert result == []
            mock_conn.close.assert_called_once()
        finally:
            patcher.stop()

    def test_get_template_names_with_rows(self):
        from utils.order_templates import get_template_names
        rows = [{'template_name': '默认'}, {'template_name': '定制'}]
        cursor = make_mock_cursor(rows)
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            result = get_template_names('眼镜网带')
            assert result == ['默认', '定制']
            mock_conn.close.assert_called_once()
        finally:
            patcher.stop()

    def test_get_template_names_dict_rows(self):
        """测试 rows[0] 是 dict 的分支"""
        from utils.order_templates import get_template_names
        rows = [{'template_name': '标准'}]
        cursor = make_mock_cursor(rows)
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            result = get_template_names('眼镜网带')
            assert result == ['标准']
        finally:
            patcher.stop()

    def test_get_template_names_tuple_rows(self):
        """测试 rows[0] 不是 dict 的分支（tuples）"""
        from utils.order_templates import get_template_names
        rows = [
            ('默认',),
            ('定制',),
        ]
        cursor = make_mock_cursor(rows)
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            result = get_template_names('眼镜网带')
            assert result == ['默认', '定制']
        finally:
            patcher.stop()

    # ─── get_template ───

    def test_get_template_not_found(self):
        from utils.order_templates import get_template
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            result = get_template('眼镜网带', '不存在')
            assert result == {}
            mock_conn.close.assert_called_once()
        finally:
            patcher.stop()

    def test_get_template_with_json(self):
        from utils.order_templates import get_template
        row = {
            'values_json': json.dumps({'总宽': 1000, '钢丝直径': 2.5}),
            'order_json': json.dumps(['d1', 'd2']),
        }
        cursor = MagicMock()
        cursor.fetchone.return_value = row
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            result = get_template('眼镜网带', '默认')
            assert result['values'] == {'总宽': 1000, '钢丝直径': 2.5}
            assert result['order'] == ['d1', 'd2']
            mock_conn.close.assert_called_once()
        finally:
            patcher.stop()

    def test_get_template_null_json(self):
        """values_json 和 order_json 为空时返回空 dict"""
        from utils.order_templates import get_template
        row = {'values_json': None, 'order_json': None}
        cursor = MagicMock()
        cursor.fetchone.return_value = row
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            result = get_template('眼镜网带', '空模板')
            assert result['values'] == {}
            assert result['order'] == {}
        finally:
            patcher.stop()

    # ─── save_template ───

    def test_save_template_empty_name(self):
        from utils.order_templates import save_template
        ok, msg = save_template('眼镜网带', '  ', {'总宽': 100})
        assert ok is False
        assert '不能为空' in msg

    def test_save_template_success(self):
        from utils.order_templates import save_template
        cursor = MagicMock()
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            ok, msg = save_template('眼镜网带', '新模板', {'总宽': 100})
            assert ok is True
            assert '已保存' in msg
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()
        finally:
            patcher.stop()

    def test_save_template_duplicate(self):
        from utils.order_templates import save_template
        cursor = MagicMock()
        cursor.execute.side_effect = Exception('Duplicate')
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            ok, msg = save_template('眼镜网带', '已存在', {'总宽': 100})
            assert ok is False
            assert '已存在' in msg
            mock_conn.close.assert_called_once()
        finally:
            patcher.stop()

    def test_save_template_with_order(self):
        from utils.order_templates import save_template
        cursor = MagicMock()
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            ok, msg = save_template('眼镜网带', '带顺序', {}, {'d1': 1})
            assert ok is True
            assert '已保存' in msg
        finally:
            patcher.stop()

    # ─── rename_template ───

    def test_rename_template_empty_name(self):
        from utils.order_templates import rename_template
        ok, msg = rename_template('眼镜网带', '旧名', '  ')
        assert ok is False
        assert '不能为空' in msg

    def test_rename_template_success(self):
        from utils.order_templates import rename_template
        cursor = MagicMock()
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            ok, msg = rename_template('眼镜网带', '旧名', '新名')
            assert ok is True
            assert '重命名成功' in msg
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()
        finally:
            patcher.stop()

    # ─── delete_template ───

    def test_delete_template_success(self):
        from utils.order_templates import delete_template
        cursor = MagicMock()
        patcher, mock_conn, _ = self.make_db_mocks(cursor)
        try:
            ok, msg = delete_template('眼镜网带', '旧模板')
            assert ok is True
            assert '已删除' in msg
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()
        finally:
            patcher.stop()


# ══════════════════════════════════════════════════════════════
# 6. 自定义参数管理
# ══════════════════════════════════════════════════════════════

class TestCustomParams:
    """自定义参数 CRUD"""

    # ─── get_custom_params ───

    def test_get_custom_params_no_data(self):
        from utils.order_templates import get_custom_params
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        patcher = patch('utils.order_templates._get_db')
        mock_get_db = patcher.start()
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            result = get_custom_params()
            assert result == []
        finally:
            patcher.stop()

    def test_get_custom_params_with_data(self):
        from utils.order_templates import get_custom_params
        params = [{'key': '总宽', 'label': '总宽'}]
        cursor = MagicMock()
        cursor.fetchone.return_value = {'params_json': json.dumps(params)}
        patcher = patch('utils.order_templates._get_db')
        mock_get_db = patcher.start()
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            result = get_custom_params()
            assert result == params
        finally:
            patcher.stop()

    def test_get_custom_params_dict_row(self):
        """row 是 dict 的分支"""
        from utils.order_templates import get_custom_params
        params = [{'key': '测试'}]
        cursor = MagicMock()
        cursor.fetchone.return_value = {'params_json': json.dumps(params)}
        patcher = patch('utils.order_templates._get_db')
        mock_get_db = patcher.start()
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            result = get_custom_params()
            assert result == params
        finally:
            patcher.stop()

    def test_get_custom_params_empty_json(self):
        """params_json 为空字符串"""
        from utils.order_templates import get_custom_params
        cursor = MagicMock()
        cursor.fetchone.return_value = {'params_json': ''}
        patcher = patch('utils.order_templates._get_db')
        mock_get_db = patcher.start()
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            result = get_custom_params()
            assert result == []
        finally:
            patcher.stop()

    def test_get_custom_params_with_row_as_tuple(self):
        """兼容非 dict 返回格式"""
        from utils.order_templates import get_custom_params
        params = [{'key': '测试'}]
        cursor = MagicMock()
        cursor.fetchone.return_value = (json.dumps(params),)
        patcher = patch('utils.order_templates._get_db')
        mock_get_db = patcher.start()
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            result = get_custom_params()
            assert result == params
        finally:
            patcher.stop()

    # ─── get_custom_material_params ───

    def test_get_custom_material_params_empty(self):
        from utils.order_templates import get_custom_material_params
        with patch('utils.order_templates.get_custom_params',
                   return_value=[]):
            result = get_custom_material_params()
            assert result == []

    def test_get_custom_material_params_dict_items(self):
        from utils.order_templates import get_custom_material_params
        params = [{'key': '特殊钢丝'}, {'key': '合金'}]
        with patch('utils.order_templates.get_custom_params',
                   return_value=params):
            result = get_custom_material_params()
            assert result == ['特殊钢丝', '合金']

    def test_get_custom_material_params_string_items(self):
        from utils.order_templates import get_custom_material_params
        params = ['特殊钢丝', '合金']
        with patch('utils.order_templates.get_custom_params',
                   return_value=params):
            result = get_custom_material_params()
            assert result == ['特殊钢丝', '合金']

    def test_get_custom_material_params_skip_empty_key(self):
        from utils.order_templates import get_custom_material_params
        params = [{'key': ''}, {'key': '合金'}]
        with patch('utils.order_templates.get_custom_params',
                   return_value=params):
            result = get_custom_material_params()
            assert result == ['合金']

    def test_get_custom_material_params_skip_other_type(self):
        from utils.order_templates import get_custom_material_params
        params = [{'key': '合金'}, 123, None]
        with patch('utils.order_templates.get_custom_params',
                   return_value=params):
            result = get_custom_material_params()
            assert result == ['合金']

    # ─── save_custom_params ───

    def test_save_custom_params_update(self):
        """已有记录时 UPDATE"""
        from utils.order_templates import save_custom_params
        params = [{'key': '总宽'}]
        cursor = MagicMock()
        cursor.fetchone.return_value = [1]  # 有 id
        patcher = patch('utils.order_templates._get_db')
        mock_get_db = patcher.start()
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            ok, msg = save_custom_params(params)
            assert ok is True
            assert '已保存' in msg
            # 应调用 UPDATE
            update_calls = [c for c in cursor.execute.call_args_list
                          if 'UPDATE' in str(c)]
            assert len(update_calls) >= 1
            mock_conn.commit.assert_called_once()
        finally:
            patcher.stop()

    def test_save_custom_params_insert(self):
        """无记录时 INSERT"""
        from utils.order_templates import save_custom_params
        params = [{'key': '总宽'}]
        cursor = MagicMock()
        cursor.fetchone.return_value = None  # 无记录
        patcher = patch('utils.order_templates._get_db')
        mock_get_db = patcher.start()
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            ok, msg = save_custom_params(params)
            assert ok is True
            # 应调用 INSERT
            insert_calls = [c for c in cursor.execute.call_args_list
                          if 'INSERT' in str(c)]
            assert len(insert_calls) >= 1
            mock_conn.commit.assert_called_once()
        finally:
            patcher.stop()


# ══════════════════════════════════════════════════════════════
# 7. get_all_product_types
# ══════════════════════════════════════════════════════════════

class TestGetAllProductTypes:
    """产品类型查询"""

    def test_empty(self):
        from utils.order_templates import get_all_product_types
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        patcher = patch('utils.order_templates._get_db')
        mock_get_db = patcher.start()
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            result = get_all_product_types()
            assert result == []
        finally:
            patcher.stop()

    def test_with_types(self):
        from utils.order_templates import get_all_product_types
        rows = [{'name': '眼镜网带'}, {'name': '人字形网带'}]
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        patcher = patch('utils.order_templates._get_db')
        mock_get_db = patcher.start()
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            result = get_all_product_types()
            assert result == ['眼镜网带', '人字形网带']
        finally:
            patcher.stop()

    def test_tuple_rows(self):
        """兼容 tuple 返回"""
        from utils.order_templates import get_all_product_types
        rows = [('眼镜网带',), ('人字形网带',)]
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        patcher = patch('utils.order_templates._get_db')
        mock_get_db = patcher.start()
        mock_conn = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            result = get_all_product_types()
            assert result == ['眼镜网带', '人字形网带']
        finally:
            patcher.stop()


# ══════════════════════════════════════════════════════════════
# 8. init_preset_data
# ══════════════════════════════════════════════════════════════

class TestInitPresetData:
    """初始化预设数据"""

    def test_init_when_empty(self):
        from utils.order_templates import init_preset_data
        cursor = MagicMock()
        cursor.fetchone.return_value = [0]  # COUNT = 0
        patcher = patch('models.database.get_connection')
        mock_gc = patcher.start()
        mock_conn = MagicMock()
        mock_gc.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            init_preset_data()
            # 应插入 6 个产品类型
            insert_count = sum(1 for c in cursor.execute.call_args_list
                             if 'INSERT INTO product_types' in str(c))
            assert insert_count == 6
            mock_conn.commit.assert_called_once()
        finally:
            patcher.stop()

    def test_init_when_not_empty(self):
        from utils.order_templates import init_preset_data
        cursor = MagicMock()
        cursor.fetchone.return_value = [10]  # COUNT > 0
        patcher = patch('models.database.get_connection')
        mock_gc = patcher.start()
        mock_conn = MagicMock()
        mock_gc.return_value = mock_conn
        mock_conn.cursor.return_value = cursor
        try:
            init_preset_data()
            # 不应有 INSERT
            insert_calls = [c for c in cursor.execute.call_args_list
                          if 'INSERT INTO product_types' in str(c)]
            assert len(insert_calls) == 0
        finally:
            patcher.stop()


# ══════════════════════════════════════════════════════════════
# 9. _get_db 覆盖（L111-113）
# ══════════════════════════════════════════════════════════════

class TestGetDb:
    """测试 _get_db 函数"""

    def test_get_db_returns_connection(self):
        from utils.order_templates import _get_db
        with patch('models.database.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            result = _get_db()
            assert result is mock_conn
            mock_gc.assert_called_once()
