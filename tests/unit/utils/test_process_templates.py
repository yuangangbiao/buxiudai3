# -*- coding: utf-8 -*-
"""测试 process_templates.py - 工序模板管理（12.12% → ~95%）"""
import sys, os, json, pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


def make_mock_cursor(rows=None, rowcount=1):
    """创建 mock cursor"""
    cursor = MagicMock()
    if rows is not None:
        cursor.fetchall.return_value = rows
    else:
        cursor.fetchall.return_value = []
    cursor.fetchone.return_value = rows[0] if rows else None
    cursor.rowcount = rowcount
    return cursor


class TestGetAllProcessTemplates:
    def test_empty_db(self):
        """数据库无模板时返回空字典"""
        from utils.process_templates import get_all_process_templates
        with patch('utils.process_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = make_mock_cursor([])
            mock_conn.cursor.return_value = mock_cursor

            result = get_all_process_templates()
            assert result == {}

    def test_with_templates(self):
        """正常返回所有模板"""
        from utils.process_templates import get_all_process_templates
        with patch('utils.process_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            rows = [
                {'name': '模板A', 'data_json': json.dumps([{'工序名': '裁切'}], ensure_ascii=False)},
                {'name': '模板B', 'data_json': json.dumps([{'工序名': '焊接'}], ensure_ascii=False)},
            ]
            mock_cursor = make_mock_cursor(rows)
            mock_conn.cursor.return_value = mock_cursor

            result = get_all_process_templates()
            assert '模板A' in result
            assert '模板B' in result
            assert result['模板A'] == [{'工序名': '裁切'}]

    def test_null_data_json(self):
        """data_json 为 NULL 时返回空列表"""
        from utils.process_templates import get_all_process_templates
        with patch('utils.process_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            rows = [{'name': '空模板', 'data_json': None}]
            mock_cursor = make_mock_cursor(rows)
            mock_conn.cursor.return_value = mock_cursor

            result = get_all_process_templates()
            assert result['空模板'] == []


class TestSaveProcessTemplates:
    def test_save_success(self):
        """保存所有模板成功"""
        from utils.process_templates import save_process_templates
        with patch('utils.process_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = make_mock_cursor()
            mock_conn.cursor.return_value = mock_cursor

            ok, msg = save_process_templates({'T1': [{'a': 1}]})
            assert ok is True
            assert '已保存' in msg
            mock_conn.commit.assert_called_once()

    def test_save_exception(self):
        """保存异常返回错误信息"""
        from utils.process_templates import save_process_templates
        with patch('utils.process_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("DB down")
            mock_conn.cursor.return_value = mock_cursor

            ok, msg = save_process_templates({'T1': []})
            assert ok is False
            assert 'DB down' in str(msg)


class TestAddProcessTemplate:
    def test_add_success(self):
        """添加新模板"""
        from utils.process_templates import add_process_template
        with patch('utils.process_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = make_mock_cursor()
            mock_conn.cursor.return_value = mock_cursor

            ok, msg = add_process_template('新模板', [{'工序': '测试'}])
            assert ok is True
            assert '已添加' in msg
            mock_conn.commit.assert_called_once()

    def test_add_duplicate(self):
        """添加重复模板返回已存在"""
        from utils.process_templates import add_process_template
        with patch('utils.process_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Duplicate entry")
            mock_conn.cursor.return_value = mock_cursor

            ok, msg = add_process_template('已存在', [])
            assert ok is False
            assert '已存在' in msg


class TestDeleteProcessTemplate:
    def test_delete(self):
        """删除模板"""
        from utils.process_templates import delete_process_template
        with patch('utils.process_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = make_mock_cursor(rowcount=1)
            mock_conn.cursor.return_value = mock_cursor

            ok, msg = delete_process_template('模板A')
            assert ok is True
            assert '已删除' in msg
            mock_conn.commit.assert_called_once()


class TestRenameProcessTemplate:
    def test_rename(self):
        """重命名模板"""
        from utils.process_templates import rename_process_template
        with patch('utils.process_templates.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = make_mock_cursor()
            mock_conn.cursor.return_value = mock_cursor

            ok, msg = rename_process_template('旧名', '新名')
            assert ok is True
            assert '重命名成功' in msg
            mock_conn.commit.assert_called_once()
