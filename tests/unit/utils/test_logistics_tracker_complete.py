# -*- coding: utf-8 -*-
"""
utils/logistics_tracker.py 深度测试 - TrackingConfig + LogisticsTracker
"""
import sys, os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import json


class TestTrackingConfigProperties:
    """TrackingConfig 属性访问器测试"""

    def test_platform_default(self):
        from utils.logistics_tracker import TrackingConfig
        cfg = TrackingConfig()
        assert cfg.platform == "kuaidi100"  # 默认值

    def test_set_platform(self):
        from utils.logistics_tracker import TrackingConfig
        cfg = TrackingConfig()
        cfg.platform = "kdniao"
        assert cfg.platform == "kdniao"

    def test_kuaidi100_customer(self):
        from utils.logistics_tracker import TrackingConfig
        cfg = TrackingConfig()
        cfg.kuaidi100_customer = "TEST_CUST"
        assert cfg.kuaidi100_customer == "TEST_CUST"

    def test_kuaidi100_key(self):
        from utils.logistics_tracker import TrackingConfig
        cfg = TrackingConfig()
        cfg.kuaidi100_key = "test_key_123"
        assert cfg.kuaidi100_key == "test_key_123"

    def test_kdniao_config(self):
        from utils.logistics_tracker import TrackingConfig
        cfg = TrackingConfig()
        cfg.kdniao_ebusiness_id = "EB123"
        cfg.kdniao_api_key = "API_KEY_456"
        assert cfg.kdniao_ebusiness_id == "EB123"
        assert cfg.kdniao_api_key == "API_KEY_456"


class TestTrackingConfigMethods:
    """TrackingConfig 方法测试 - 使用独立实例避免单例状态污染"""

    def test_is_configured_kuaidi100_true(self):
        from utils.logistics_tracker import TrackingConfig
        # 强制重置单例
        TrackingConfig._instance = None
        cfg = TrackingConfig()
        cfg.kuaidi100_customer = "CUSTOMER"
        cfg.kuaidi100_key = "KEY123"
        assert cfg.is_configured() is True

    def test_is_configured_kuaidi100_false(self):
        from utils.logistics_tracker import TrackingConfig
        TrackingConfig._instance = None
        cfg = TrackingConfig()
        cfg.kuaidi100_customer = "CUSTOMER"
        cfg.kuaidi100_key = ""  # 缺少 key
        assert cfg.is_configured() is False

    def test_is_configured_kdniao_true(self):
        from utils.logistics_tracker import TrackingConfig
        TrackingConfig._instance = None
        cfg = TrackingConfig()
        cfg.platform = "kdniao"
        cfg.kdniao_ebusiness_id = "EB123"
        cfg.kdniao_api_key = "API_KEY"
        assert cfg.is_configured() is True

    def test_is_configured_unconfigured(self):
        from utils.logistics_tracker import TrackingConfig
        TrackingConfig._instance = None
        cfg = TrackingConfig()
        cfg.platform = "unknown"
        assert cfg.is_configured() is False

    def test_get_config_info_kuaidi100(self):
        from utils.logistics_tracker import TrackingConfig
        TrackingConfig._instance = None
        cfg = TrackingConfig()
        cfg.kuaidi100_customer = "TESTUSER"
        cfg.kuaidi100_key = "KEY123"
        info = cfg.get_config_info()
        assert info["platform"] == "kuaidi100"
        assert "****" in info["customer"]
        assert info["key"] == "已配置"

    def test_get_config_info_kdniao(self):
        from utils.logistics_tracker import TrackingConfig
        TrackingConfig._instance = None
        cfg = TrackingConfig()
        cfg.platform = "kdniao"
        cfg.kdniao_ebusiness_id = "EB123456"
        cfg.kdniao_api_key = "KEY"
        info = cfg.get_config_info()
        assert info["platform"] == "kdniao"
        assert "****" in info["ebusiness_id"]
        assert info["api_key"] == "已配置"


class TestTrackingConfigLoadSave:
    """TrackingConfig 配置加载/保存测试"""

    def test_save_and_load_json(self):
        from utils.logistics_tracker import TrackingConfig
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        try:
            cfg = TrackingConfig()
            cfg.set_config_file(path)
            cfg.kuaidi100_customer = "SAVE_TEST"
            cfg.kuaidi100_key = "KEY_SAVED"
            cfg.save()

            # 重新加载
            cfg2 = TrackingConfig()
            cfg2.set_config_file(path)
            cfg2.load()
            assert cfg2.kuaidi100_customer == "SAVE_TEST"
            assert cfg2.kuaidi100_key == "KEY_SAVED"
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        from utils.logistics_tracker import TrackingConfig
        cfg = TrackingConfig()
        cfg.set_config_file("/nonexistent/path/config.json")
        cfg.load()  # 不应抛异常


class TestKuaidi100TrackerQuery:
    """Kuaidi100Tracker.query 测试"""

    @pytest.fixture
    def configured_tracker(self):
        from utils.logistics_tracker import Kuaidi100Tracker, TrackingConfig
        cfg = TrackingConfig()
        cfg.kuaidi100_customer = "TEST_CUSTOMER"
        cfg.kuaidi100_key = "TEST_KEY"
        return Kuaidi100Tracker(cfg)

    def test_query_success(self, configured_tracker):
        with patch('utils.logistics_tracker.requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "result": True,
                "returnCode": "200",
                "state": "3",
                "data": [{"time": "2026-01-01 10:00", "context": "已签收"}]
            }
            mock_post.return_value = mock_resp

            result = configured_tracker.query("SF123456789")
            assert result["success"] is True
            assert result["state"] == "3"
            assert len(result["traces"]) == 1

    def test_query_failure(self, configured_tracker):
        with patch('utils.logistics_tracker.requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "result": False,
                "returnCode": "500",
                "message": "服务器错误"
            }
            mock_post.return_value = mock_resp

            result = configured_tracker.query("SF123456789")
            assert result["success"] is False
            assert "traces" in result

    def test_query_timeout(self, configured_tracker):
        import requests
        with patch('utils.logistics_tracker.requests.post') as mock_post:
            mock_post.side_effect = requests.Timeout("timeout")
            result = configured_tracker.query("SF123456789")
            assert result["success"] is False
            assert "超时" in result["message"]

    def test_query_unconfigured(self):
        from utils.logistics_tracker import Kuaidi100Tracker, TrackingConfig
        # 重置单例，防止其他测试污染
        TrackingConfig._instance = None
        cfg = TrackingConfig()
        # 确保未配置
        cfg.platform = "kuaidi100"
        cfg.kuaidi100_customer = ""
        cfg.kuaidi100_key = ""
        tracker = Kuaidi100Tracker(cfg)
        result = tracker.query("SF123456789")
        assert result["success"] is False
        assert "API未配置" in result["message"]


class TestKuaidi100TrackerSubscribe:
    """Kuaidi100Tracker.subscribe 测试"""

    @pytest.fixture
    def configured_tracker(self):
        from utils.logistics_tracker import Kuaidi100Tracker, TrackingConfig
        cfg = TrackingConfig()
        cfg.kuaidi100_customer = "TEST_CUSTOMER"
        cfg.kuaidi100_key = "TEST_KEY"
        cfg.kuaidi100_callback_url = "https://callback.example.com"
        return Kuaidi100Tracker(cfg)

    def test_subscribe_success(self, configured_tracker):
        with patch('utils.logistics_tracker.requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"result": True, "message": "订阅成功"}
            mock_post.return_value = mock_resp

            result = configured_tracker.subscribe("SF123456789", "顺丰速运")
            assert result["success"] is True
            assert "订阅成功" in result["message"]

    def test_subscribe_failure(self, configured_tracker):
        with patch('utils.logistics_tracker.requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"result": False, "returnCode": "500", "message": "订阅失败"}
            mock_post.return_value = mock_resp

            result = configured_tracker.subscribe("SF123456789", "顺丰速运")
            assert result["success"] is False
            assert "订阅失败" in result["message"]

    def test_subscribe_no_callback_url(self, configured_tracker):
        from utils.logistics_tracker import Kuaidi100Tracker, TrackingConfig
        cfg = TrackingConfig()
        cfg.kuaidi100_customer = "TEST"
        cfg.kuaidi100_key = "KEY"
        cfg.kuaidi100_callback_url = ""  # 无回调地址
        tracker = Kuaidi100Tracker(cfg)
        result = tracker.subscribe("SF123456789")
        assert result["success"] is False
        assert "回调地址" in result["message"]

    def test_subscribe_unconfigured(self):
        from utils.logistics_tracker import Kuaidi100Tracker, TrackingConfig
        cfg = TrackingConfig()  # 完全未配置
        tracker = Kuaidi100Tracker(cfg)
        result = tracker.subscribe("SF123456789")
        assert result["success"] is False


class TestLogisticsPureFunctions:
    """物流追踪纯函数测试"""

    def test_get_company_code_known(self):
        from utils.logistics_tracker import get_company_code
        assert get_company_code("顺丰速运", "kuaidi100") == "shunfeng"
        assert get_company_code("顺丰速运", "kdniao") == "SF"
        assert get_company_code("中通快递", "kuaidi100") == "zhongtong"
        assert get_company_code("德邦物流", "kdniao") == "DBL"

    def test_get_company_code_unknown(self):
        from utils.logistics_tracker import get_company_code
        assert get_company_code("未知物流公司", "kuaidi100") == ""

    def test_get_company_name_by_code(self):
        from utils.logistics_tracker import get_company_name_by_code
        assert get_company_name_by_code("shunfeng", "kuaidi100") == "顺丰速运"
        assert get_company_name_by_code("SF", "kdniao") == "顺丰速运"
        assert get_company_name_by_code("zhongtong", "kuaidi100") == "中通快递"

    def test_get_company_name_by_code_not_found(self):
        from utils.logistics_tracker import get_company_name_by_code
        assert get_company_name_by_code("UNKNOWN_CODE", "kuaidi100") == ""

    def test_state_text(self):
        from utils.logistics_tracker import state_text
        assert state_text("0") == "暂无轨迹"
        assert state_text("1") == "已揽收"
        assert state_text("2") == "运输中"
        assert state_text("3") == "已签收"
        assert state_text("4") == "问题件"
        assert state_text("5") == "转投"
        assert state_text("14") == "拒签"

    def test_state_text_unknown(self):
        from utils.logistics_tracker import state_text
        result = state_text("999")
        assert "未知状态" in result
        assert "999" in result


class TestLogisticsTrackerSingleton:
    """LogisticsTracker 实例测试"""

    def test_logistics_tracker_current_tracker_property(self):
        from utils.logistics_tracker import LogisticsTracker, Kuaidi100Tracker
        tracker = LogisticsTracker()
        assert isinstance(tracker.current_tracker, Kuaidi100Tracker)

    def test_logistics_tracker_query_delegates(self):
        from utils.logistics_tracker import LogisticsTracker
        with patch.object(LogisticsTracker, 'current_tracker') as mock_tracker:
            mock_instance = MagicMock()
            mock_tracker.return_value = mock_instance
            mock_instance.query.return_value = {"success": True, "state": "3", "traces": []}

            tracker = LogisticsTracker()
            result = tracker.query("SF123", "顺丰速运")

            assert result["success"] is True
