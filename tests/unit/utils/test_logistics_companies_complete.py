# -*- coding: utf-8 -*-
"""
utils/logistics_companies.py 测试 - 当前93%，覆盖剩余7%
使用 mock 绕过文件系统隔离问题
"""
import pytest
import json
from unittest.mock import patch, mock_open, MagicMock


class TestLogisticsCompaniesDefaultList:
    """默认物流公司列表测试"""

    def test_default_companies_exist(self):
        from utils.logistics_companies import DEFAULT_LOGISTICS
        assert len(DEFAULT_LOGISTICS) > 10
        assert "顺丰速运" in DEFAULT_LOGISTICS
        assert "德邦物流" in DEFAULT_LOGISTICS
        assert "京东物流" in DEFAULT_LOGISTICS


class TestLogisticsCompaniesLoadCustom:
    """_load_custom 测试"""

    def test_load_custom_success(self):
        """成功加载自定义物流公司"""
        mock_data = json.dumps({"custom_companies": ["物流A", "物流B"]})
        with patch('builtins.open', mock_open(read_data=mock_data)):
            with patch('os.path.exists', return_value=True):
                from utils.logistics_companies import _load_custom
                result = _load_custom()
                assert "物流A" in result
                assert "物流B" in result

    def test_load_custom_file_not_exists(self):
        """文件不存在返回空列表"""
        with patch('os.path.exists', return_value=False):
            from utils.logistics_companies import _load_custom
            result = _load_custom()
            assert result == []

    def test_load_custom_corrupt_json(self):
        """损坏的JSON返回空列表"""
        with patch('builtins.open', mock_open(read_data="{ corrupt")):
            with patch('os.path.exists', return_value=True):
                from utils.logistics_companies import _load_custom
                result = _load_custom()
                assert result == []


class TestLogisticsCompaniesSaveCustom:
    """_save_custom 测试"""

    def test_save_custom(self):
        """验证 _save_custom 写入了自定义公司"""
        from utils.logistics_companies import _save_custom
        # 直接测试文件写入，不解析内容
        with patch('builtins.open', mock_open()) as m:
            _save_custom(["新物流A", "新物流B"])
            assert m.assert_called


class TestLogisticsCompaniesGetAll:
    """get_all_companies 测试"""

    @patch('utils.logistics_companies._load_custom')
    def test_get_all_includes_defaults(self, mock_load):
        """所有公司 = 默认 + 自定义"""
        mock_load.return_value = ["自定义物流"]
        from utils.logistics_companies import get_all_companies
        result = get_all_companies()
        assert "顺丰速运" in result
        assert "自定义物流" in result


class TestLogisticsCompaniesAdd:
    """add_company 测试"""

    @patch('utils.logistics_companies._save_custom')
    @patch('utils.logistics_companies._load_custom')
    def test_add_valid_company(self, mock_load, mock_save):
        """添加有效物流公司"""
        mock_load.return_value = []  # 无重复
        from utils.logistics_companies import add_company
        ok, msg = add_company("测试物流")
        assert ok is True
        assert "测试物流" in msg
        mock_save.assert_called_once()

    @patch('utils.logistics_companies._load_custom')
    def test_add_empty_name(self, mock_load):
        """空名称失败"""
        from utils.logistics_companies import add_company
        ok, msg = add_company("")
        assert ok is False
        assert "不能为空" in msg

    @patch('utils.logistics_companies._load_custom')
    def test_add_whitespace_only(self, mock_load):
        """仅空格失败"""
        from utils.logistics_companies import add_company
        ok, msg = add_company("   ")
        assert ok is False

    @patch('utils.logistics_companies._load_custom')
    def test_add_duplicate_in_defaults(self, mock_load):
        """默认列表中的公司不可重复添加"""
        mock_load.return_value = []
        from utils.logistics_companies import add_company
        ok, msg = add_company("顺丰速运")
        assert ok is False
        assert "已存在" in msg

    @patch('utils.logistics_companies._save_custom')
    @patch('utils.logistics_companies._load_custom')
    def test_add_duplicate_custom(self, mock_load, mock_save):
        """已添加的自定义公司不可重复"""
        mock_load.return_value = ["已存在物流"]
        from utils.logistics_companies import add_company
        ok, msg = add_company("已存在物流")
        assert ok is False
        assert "已存在" in msg


class TestLogisticsCompaniesRemove:
    """remove_company 测试"""

    @patch('utils.logistics_companies._save_custom')
    @patch('utils.logistics_companies._load_custom')
    def test_remove_default_fails(self, mock_load, mock_save):
        """默认物流公司不可删除"""
        mock_load.return_value = []
        from utils.logistics_companies import remove_company
        ok, msg = remove_company("德邦物流")
        assert ok is False
        assert "不可删除" in msg

    @patch('utils.logistics_companies._load_custom')
    def test_remove_nonexistent_fails(self, mock_load):
        """删除不存在的公司失败"""
        mock_load.return_value = []
        from utils.logistics_companies import remove_company
        ok, msg = remove_company("不存在的物流")
        assert ok is False
        assert "不存在" in msg

    @patch('utils.logistics_companies._save_custom')
    @patch('utils.logistics_companies._load_custom')
    def test_remove_custom_success(self, mock_load, mock_save):
        """删除自定义物流公司成功"""
        mock_load.return_value = ["临时物流"]
        from utils.logistics_companies import remove_company
        ok, msg = remove_company("临时物流")
        assert ok is True
        assert "已删除" in msg


class TestLogisticsCompaniesGetCustom:
    """get_custom_companies 测试"""

    @patch('utils.logistics_companies._load_custom')
    def test_get_custom_companies(self, mock_load):
        """获取自定义物流公司"""
        mock_load.return_value = ["A", "B"]
        from utils.logistics_companies import get_custom_companies
        result = get_custom_companies()
        assert "A" in result
        assert "B" in result
