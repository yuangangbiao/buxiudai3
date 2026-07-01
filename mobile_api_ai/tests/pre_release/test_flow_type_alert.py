# -*- coding: utf-8 -*-
"""
T13 前测: 监控告警 5 中心埋点
"""
import sys
import unittest
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "mobile_api_ai"))

# 直接加载 flow_type_alert.py 绕过 services/__init__.py (后者触发 requests 链式 import)
spec = importlib.util.spec_from_file_location(
    "flow_type_alert",
    PROJECT_ROOT / "mobile_api_ai" / "services" / "flow_type_alert.py"
)
alert_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alert_module)
# 替换 _send_wechat_alert 避免真实 HTTP 调用
alert_module.FlowTypeAlertMonitor._send_wechat_alert = lambda self, msg: True


class TestAlertMonitorBasic(unittest.TestCase):
    """基础告警 (2 用例)"""

    def setUp(self):
        self.monitor = alert_module.get_monitor()
        self.monitor.clear_dedup_cache()
        self.monitor._alert_counts.clear()

    def test_same_flow_type_no_alert(self):
        """1. expected == actual → 不告警 (一致性)"""
        self.monitor.alert_flow_type_mismatch('center_a', 'ORD-001', 'outsource', 'outsource', 'mismatch')
        self.assertEqual(self.monitor.get_alert_counts().get('center_a', 0), 0)

    def test_different_flow_type_alerts(self):
        """2. expected != actual → 告警计数 +1"""
        self.monitor.alert_flow_type_mismatch('center_a', 'ORD-001', 'outsource', 'production', 'mismatch')
        self.assertEqual(self.monitor.get_alert_counts()['center_a'], 1)


class TestDeduplication(unittest.TestCase):
    """去重 (1 用例)"""

    def setUp(self):
        self.monitor = alert_module.get_monitor()
        self.monitor.clear_dedup_cache()
        self.monitor._alert_counts.clear()

    def test_5min_dedup_window(self):
        """3. 同一 (center, order_no, alert_type) 5 分钟内不重复"""
        self.monitor.alert_flow_type_mismatch('center_a', 'ORD-001', 'outsource', 'production', 'mismatch')
        self.assertEqual(self.monitor.get_alert_counts()['center_a'], 1)
        # 第二次同 key → 跳过
        self.monitor.alert_flow_type_mismatch('center_a', 'ORD-001', 'outsource', 'production', 'mismatch')
        self.assertEqual(self.monitor.get_alert_counts()['center_a'], 1)  # 仍 1
        # 不同 alert_type → 触发新告警
        self.monitor.alert_flow_type_mismatch('center_a', 'ORD-001', 'outsource', 'production', 'conflict')
        self.assertEqual(self.monitor.get_alert_counts()['center_a'], 2)


class TestFiveCenterCoverage(unittest.TestCase):
    """5 中心覆盖 (1 用例)"""

    def setUp(self):
        self.monitor = alert_module.get_monitor()
        self.monitor.clear_dedup_cache()
        self.monitor._alert_counts.clear()

    def test_all_5_centers_can_alert(self):
        """4. 5 中心 (dispatch_core/container_api/container_v5/mobile_dispatcher/mobile_sync) 都能告警"""
        alert_module.alert_dispatch_core('ORD-001', 'outsource', 'production')
        alert_module.alert_container_api('ORD-002', 'quality', 'production')
        alert_module.alert_container_v5('ORD-003', 'outsource', 'material_purchase')
        alert_module.alert_mobile_dispatcher('ORD-004', 'quality', 'production')
        alert_module.alert_mobile_sync('ORD-005', 'material_purchase', 'production')
        counts = self.monitor.get_alert_counts()
        # 5 中心各 1 次
        for center in ['dispatch_center', 'container_api', 'container_v5', 'mobile_dispatcher', 'mobile_sync']:
            self.assertEqual(counts.get(center, 0), 1, f"{center} 告警 1 次")


class TestReceiverConfig(unittest.TestCase):
    """接收人配置 (1 用例)"""

    def test_receiver_is_yuan_gang_biao(self):
        """5. 接收人 = 苑岗彪 (wechat_userid 占位)"""
        self.assertEqual(alert_module.ALERT_RECEIVER_USERID, 'yuan_gang_biao',
                         "接收人必须 = 苑岗彪")


if __name__ == "__main__":
    unittest.main()
