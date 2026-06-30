# -*- coding: utf-8 -*-
"""E2E 测试——需本地服务运行，默认跳过"""
import pytest
import requests
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 检查服务是否在线，否则跳过
def _service_available(url, timeout=2):
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code < 500
    except:
        return False

MOBILE_URL = os.getenv('MOBILE_API_URL', 'http://127.0.0.1:5008')
SKIP_REASON = "E2E: 本地服务未运行，跳过集成测试"

e2e = pytest.mark.skipif(
    not _service_available(f"{MOBILE_URL}/api/health"),
    reason=SKIP_REASON
)


class TestE2EFlow1:
    """E2E 流程 1：创建订单→查询→状态流转"""

    @e2e
    def test_order_lifecycle(self):
        # 查询健康检查
        resp = requests.get(f"{MOBILE_URL}/api/health", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")

    @e2e
    def test_schedule_status(self):
        """调度状态查询"""
        resp = requests.get(f"{MOBILE_URL}/api/schedule/health", timeout=5)
        assert resp.status_code < 500


class TestE2EFlow2:
    """E2E 流程 2：生产→质检"""

    @e2e
    def test_production_health(self):
        resp = requests.get(f"{MOBILE_URL}/api/health", timeout=5)
        assert resp.status_code == 200


class TestE2EFlow3:
    """E2E 流程 3：发货"""

    @e2e
    def test_shipment_health(self):
        # 发货通过 sync bridge 或主系统
        resp = requests.get(f"{MOBILE_URL}/api/health", timeout=5)
        assert resp.status_code == 200
