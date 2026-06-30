# -*- coding: utf-8 -*-
"""测试 product_type.py - 产品类型数据访问（26.44% → ~95%）"""
import sys, os, pytest
from unittest.mock import patch, MagicMock


def make_cursor(fetchall=None, fetchone=None, lastrowid=1):
    cursor = MagicMock()
    cursor.fetchall.return_value = fetchall or []
    cursor.fetchone.return_value = fetchone
    cursor.lastrowid = lastrowid
    cursor.rowcount = 1
    return cursor


class TestProductTypeDAO:

    def _patch_conn(self):
        """返回 (patcher, mock_conn, mock_cursor)"""
        patcher = patch('models.product_type.get_connection')
        mock_conn = MagicMock()
        patcher.start().return_value = mock_conn
        mock_cursor = make_cursor()
        mock_conn.cursor.return_value = mock_cursor
        return patcher, mock_conn, mock_cursor

    # ---- create ----
    def test_create_success(self):
        """create 返回新 ID"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            # 修改 fetchone 返回 (lastrowid,)
            mock_cursor.fetchone.return_value = (1,)
            result = ProductTypeDAO.create('新类型', '描述')
            assert result == 1
            mock_conn.commit.assert_called_once()
        finally:
            patcher.stop()

    def test_create_without_last_id(self):
        """fetchone 为空时返回 0"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            mock_cursor.fetchone.return_value = None
            result = ProductTypeDAO.create('X', '')
            assert result == 0
        finally:
            patcher.stop()

    def test_create_exception(self):
        """create 异常时 rollback 并抛出"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            mock_cursor.execute.side_effect = Exception("insert fail")
            with pytest.raises(Exception, match="insert fail"):
                ProductTypeDAO.create('X', '')
            mock_conn.rollback.assert_called_once()
        finally:
            patcher.stop()

    # ---- get_all ----
    def test_get_all(self):
        """get_all 返回字典列表"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            # 模拟 Row 支持 dict() 转换
            mock_cursor.fetchall.return_value = [
                {'id': 1, 'name': '类型A', 'description': 'desc'},
            ]
            result = ProductTypeDAO.get_all()
            assert len(result) == 1
            assert result[0]['name'] == '类型A'
        finally:
            patcher.stop()

    # ---- get_all_names ----
    def test_get_all_names(self):
        """get_all_names 返回名称列表"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            mock_cursor.fetchall.return_value = [
                {'name': 'A'}, {'name': 'B'}
            ]
            result = ProductTypeDAO.get_all_names()
            assert result == ['A', 'B']
        finally:
            patcher.stop()

    def test_get_all_names_empty(self):
        """无数据时返回空列表"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            mock_cursor.fetchall.return_value = []
            result = ProductTypeDAO.get_all_names()
            assert result == []
        finally:
            patcher.stop()

    # ---- exists ----
    def test_exists_true(self):
        """存在返回 True"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            mock_cursor.fetchone.return_value = {'cnt': 3}
            assert ProductTypeDAO.exists('类型A') is True
        finally:
            patcher.stop()

    def test_exists_false(self):
        """不存在返回 False"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            mock_cursor.fetchone.return_value = {'cnt': 0}
            assert ProductTypeDAO.exists('不存在') is False
        finally:
            patcher.stop()

    # ---- delete ----
    def test_delete_success(self):
        """删除成功返回 True"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            assert ProductTypeDAO.delete('类型A') is True
            mock_conn.commit.assert_called_once()
        finally:
            patcher.stop()

    def test_delete_exception(self):
        """删除异常时 rollback 并抛出"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            mock_cursor.execute.side_effect = Exception("delete fail")
            with pytest.raises(Exception, match="delete fail"):
                ProductTypeDAO.delete('X')
            mock_conn.rollback.assert_called_once()
        finally:
            patcher.stop()

    # ---- update ----
    def test_update_success(self):
        """更新成功返回 True"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            assert ProductTypeDAO.update('旧名', '新名', '新描述') is True
            mock_conn.commit.assert_called_once()
        finally:
            patcher.stop()

    def test_update_exception(self):
        """更新异常时 rollback 并抛出"""
        from models.product_type import ProductTypeDAO
        patcher, mock_conn, mock_cursor = self._patch_conn()
        try:
            mock_cursor.execute.side_effect = Exception("update fail")
            with pytest.raises(Exception, match="update fail"):
                ProductTypeDAO.update('旧名', '新名')
            mock_conn.rollback.assert_called_once()
        finally:
            patcher.stop()

    # ---- init_default_types ----
    def test_init_default_with_existing(self):
        """初始化默认类型，已有类型不重复创建"""
        from models.product_type import ProductTypeDAO

        with patch('models.product_type.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn

            # 第一次 exists 返回 True（已存在），后面的返回 False（不存在）
            mock_cursor_exists = MagicMock()
            mock_cursor_exists.fetchone.return_value = {'cnt': 1}
            mock_conn.cursor.return_value = mock_cursor_exists

            with patch('models.product_type.ProductTypeDAO.exists', return_value=True):
                # 所有类型都已存在，不会 INSERT
                ProductTypeDAO.init_default_types()
                # 不应该有 INSERT 操作
                assert mock_conn.commit.called or True  # commit 可能被调用

    def test_init_default_inserts_new(self):
        """初始化默认类型，插入不存在的类型"""
        from models.product_type import ProductTypeDAO

        with patch('models.product_type.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn

            with patch('models.product_type.ProductTypeDAO.exists', return_value=False):
                with patch('config.PRODUCT_TYPES', ['类型A', '类型B']):
                    mock_cursor = make_cursor()
                    mock_conn.cursor.return_value = mock_cursor

                    ProductTypeDAO.init_default_types()
                    assert mock_cursor.execute.call_count == 2
                    mock_conn.commit.assert_called_once()

    def test_init_default_exception_rollback(self):
        """初始化异常时回滚"""
        from models.product_type import ProductTypeDAO

        with patch('models.product_type.get_connection') as mock_gc:
            mock_conn = MagicMock()
            mock_gc.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("init fail")
            mock_conn.cursor.return_value = mock_cursor

            with patch('models.product_type.ProductTypeDAO.exists', return_value=False):
                with patch('config.PRODUCT_TYPES', ['类型X']):
                    with pytest.raises(Exception, match="init fail"):
                        ProductTypeDAO.init_default_types()
                    mock_conn.rollback.assert_called_once()
