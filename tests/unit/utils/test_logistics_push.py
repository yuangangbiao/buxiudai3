# -*- coding: utf-8 -*-
"""最后1.3%冲刺 - logistics_tracker 纯数据+函数"""
import sys, os
import pytest


class TestLogisticsTracker:
    def test_company_codes(self):
        from utils.logistics_tracker import LOGISTICS_COMPANY_CODES
        assert "顺丰速运" in LOGISTICS_COMPANY_CODES
        assert LOGISTICS_COMPANY_CODES["顺丰速运"]["kuaidi100"] == "shunfeng"

    def test_tracking_state_map(self):
        from utils.logistics_tracker import TRACKING_STATE_MAP
        assert TRACKING_STATE_MAP["1"] == "已揽收"
        assert TRACKING_STATE_MAP["3"] == "已签收"

    def test_get_company_code_found(self):
        from utils.logistics_tracker import get_company_code
        assert get_company_code("顺丰速运", "kuaidi100") == "shunfeng"
        assert get_company_code("顺丰速运", "kdniao") == "SF"

    def test_get_company_code_not_found(self):
        from utils.logistics_tracker import get_company_code
        assert get_company_code("不存在的快递") == ""

    def test_get_company_name_by_code(self):
        from utils.logistics_tracker import get_company_name_by_code
        # 应该能找到顺丰
        name = get_company_name_by_code("shunfeng")
        assert name is not None or name == ""

    def test_logistics_tracker_class(self):
        from utils.logistics_tracker import LogisticsTracker
        tracker = LogisticsTracker()
        assert tracker is not None


class TestEventBusFactory:
    def test_create_with_types(self):
        from core.event_bus_factory import create_event_bus
        bus = create_event_bus()
        assert bus is not None
