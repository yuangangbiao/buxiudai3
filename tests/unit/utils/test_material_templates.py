# -*- coding: utf-8 -*-
"""测试 material_templates.py - 物料备料模板管理（13.24% → ~95%）"""
import sys, os, json, pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


def make_mock_cursor(rows=None, rowcount=1):
    cursor = MagicMock()
    if rows is not None:
        cursor.fetchall.return_value = rows
        cursor.fetchone.return_value = rows[0] if rows else None
    else:
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = None
    cursor.rowcount = rowcount
    return cursor


class TestGetAllTemplates:
    def test_empty(self):
        """无模板返回空列表"""
        from utils.material_templates import get_all_templates
        with patch('utils.material_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = make_mock_cursor([])
            mock_conn.cursor.return_value = mock_cursor
            assert get_all_templates() == []

    def test_with_data(self):
        """正常返回模板列表"""
        from utils.material_templates import get_all_templates
        with patch('utils.material_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            rows = [{
                'name': '模板A',
                'description': '描述',
                'materials_json': json.dumps([{'物料': '不锈钢丝'}], ensure_ascii=False),
                'created_at': '2025-01-01',
                'updated_at': '2025-01-02',
            }]
            mock_cursor = make_mock_cursor(rows)
            mock_conn.cursor.return_value = mock_cursor

            result = get_all_templates()
            assert len(result) == 1
            assert result[0]['name'] == '模板A'
            assert result[0]['materials'] == [{'物料': '不锈钢丝'}]

    def test_null_materials_json(self):
        """materials_json 为 NULL 时返回空列表"""
        from utils.material_templates import get_all_templates
        with patch('utils.material_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            rows = [{'name': '空', 'description': '', 'materials_json': None,
                     'created_at': '', 'updated_at': ''}]
            mock_cursor = make_mock_cursor(rows)
            mock_conn.cursor.return_value = mock_cursor
            result = get_all_templates()
            assert result[0]['materials'] == []


class TestGetTemplate:
    def test_found(self):
        """查找到指定模板"""
        from utils.material_templates import get_template
        with patch('utils.material_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            rows = [{'name': 'T1', 'description': 'desc', 'materials_json': '[]',
                     'created_at': '', 'updated_at': ''}]
            mock_cursor = make_mock_cursor(rows)
            mock_conn.cursor.return_value = mock_cursor
            result = get_template('T1')
            assert result is not None
            assert result['name'] == 'T1'

    def test_not_found(self):
        """找不到模板返回 None"""
        from utils.material_templates import get_template
        with patch('utils.material_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = make_mock_cursor([])
            mock_conn.cursor.return_value = mock_cursor
            assert get_template('不存在') is None


class TestSaveTemplate:
    def test_save_new(self):
        """保存新模板"""
        from utils.material_templates import save_template
        with patch('utils.material_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = make_mock_cursor()
            mock_conn.cursor.return_value = mock_cursor

            ok, msg = save_template('新模板', [{'物料': '钢带'}], '描述文本')
            assert ok is True
            assert '已保存' in msg
            mock_conn.commit.assert_called_once()

    def test_save_duplicate(self):
        """保存重复模板"""
        from utils.material_templates import save_template
        with patch('utils.material_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Duplicate")
            mock_conn.cursor.return_value = mock_cursor

            ok, msg = save_template('已存在', [])
            assert ok is False
            assert '已存在' in msg


class TestDeleteTemplate:
    def test_delete(self):
        """删除模板"""
        from utils.material_templates import delete_template
        with patch('utils.material_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = make_mock_cursor(rowcount=1)
            mock_conn.cursor.return_value = mock_cursor

            ok, msg = delete_template('模板A')
            assert ok is True
            assert '已删除' in msg
            mock_conn.commit.assert_called_once()


class TestRenameTemplate:
    def test_rename(self):
        """重命名模板"""
        from utils.material_templates import rename_template
        with patch('utils.material_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = make_mock_cursor()
            mock_conn.cursor.return_value = mock_cursor

            ok, msg = rename_template('旧名', '新名')
            assert ok is True
            assert '重命名成功' in msg
            mock_conn.commit.assert_called_once()


class TestGetTemplateNames:
    def test_names(self):
        """获取所有模板名称"""
        from utils.material_templates import get_template_names
        with patch('utils.material_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            rows = [{'name': 'A'}, {'name': 'B'}]
            mock_cursor = make_mock_cursor(rows)
            mock_conn.cursor.return_value = mock_cursor
            assert get_template_names() == ['A', 'B']
