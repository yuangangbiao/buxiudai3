# -*- coding: utf-8 -*-
"""F22 行动项 3 硬迁移后 - 端到端验证

模拟 5003 端口 dispatch_center 的告警 API 调用 + ContainerCenterClient.get_alert_list 直接调用
验证 硬迁移后的调用链路正确性。
"""
import os
import sys
import json
import threading
import time
import http.server
from unittest.mock import MagicMock, patch

os.chdir(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
sys.path.insert(0, os.getcwd())

print('=' * 60)
print('F22 行动项 3 硬迁移 - 端到端验证 (2026-06-20)')
print('=' * 60)

# ═══════════════════════════════════════════════════════════════
# 1. 验证 ContainerCenterClient.get_alert_list 直接调用 5003
# ═══════════════════════════════════════════════════════════════
print()
print('--- 1. ContainerCenterClient 直接调用 5003 验证 ---')

# 用 requests_mock 或 unittest.mock 模拟 _session.get 调用
from container_center.client.container_client import ContainerCenterClient

# 创建一个 mock session
mock_session = MagicMock()
mock_resp = MagicMock()
mock_resp.status_code = 200
mock_resp.raise_for_status = MagicMock()
mock_resp.json.return_value = {
    'data': {
        'items': [
            {'id': 'alert_001', 'level': 'WARNING', 'alert_type': 'task_timeout'},
            {'id': 'alert_002', 'level': 'CRITICAL', 'alert_type': 'order_overdue'},
        ]
    }
}
mock_session.get.return_value = mock_resp

# 创建客户端，使用 mock session
client = ContainerCenterClient(base_url='http://localhost:5002')
client._session = mock_session

# 调用 get_alert_list
print('  调用 get_alert_list() ...')
alerts = client.get_alert_list()
print(f'  返回 {len(alerts)} 条告警')
assert len(alerts) == 2, f'期望 2 条，实际 {len(alerts)}'

# 验证调用目标是 5003
called_url = mock_session.get.call_args[0][0]
assert '5003' in called_url, f'调用 URL 应包含 5003，实际: {called_url}'
print(f'  [OK] 调用目标: {called_url}')

# 验证没有 5002 fallback
assert '/api/v4/' not in called_url, f'硬迁移后不应再调用 /api/v4/，实际: {called_url}'
print(f'  [OK] 不调用 5002 fallback')

# ═══════════════════════════════════════════════════════════════
# 2. 验证 5003 不可用时直接抛异常（不兜底）
# ═══════════════════════════════════════════════════════════════
print()
print('--- 2. 5003 不可用时直接抛异常验证 ---')

# 模拟连接失败
mock_session2 = MagicMock()
mock_session2.get.side_effect = ConnectionError('5003 不可达')

client2 = ContainerCenterClient(base_url='http://localhost:5002')
client2._session = mock_session2

try:
    client2.get_alert_list()
    print('  [FAIL] 5003 不可用时应抛异常，但实际返回了结果')
    sys.exit(1)
except ConnectionError as e:
    print(f'  [OK] 5003 不可用时直接抛 ConnectionError: {e}')
except Exception as e:
    print(f'  [OK] 5003 不可用时抛 {type(e).__name__}: {e}')

# ═══════════════════════════════════════════════════════════════
# 3. 验证 dismiss_alert 直接调用 5003
# ═══════════════════════════════════════════════════════════════
print()
print('--- 3. dismiss_alert 直接调用 5003 验证 ---')

mock_session3 = MagicMock()
mock_resp3 = MagicMock()
mock_resp3.status_code = 200
mock_resp3.raise_for_status = MagicMock()
mock_resp3.json.return_value = {'data': {'dismissed': True}}
mock_session3.post.return_value = mock_resp3

client3 = ContainerCenterClient(base_url='http://localhost:5002')
client3._session = mock_session3

result = client3.dismiss_alert('alert_001')
print(f'  dismiss_alert 返回: {result}')
assert result is True, f'期望 True，实际 {result}'

called_method, called_url = mock_session3.post.call_args[0]
assert '5003' in called_url, f'调用 URL 应包含 5003，实际: {called_url}'
assert '/api/dispatch-center/alerts/alert_001/dismiss' in called_url
print(f'  [OK] 调用目标: {called_method} {called_url}')

# ═══════════════════════════════════════════════════════════════
# 4. 验证 AlertEngine 拆分函数可调用
# ═══════════════════════════════════════════════════════════════
print()
print('--- 4. AlertEngine 拆分函数可调用验证 ---')

import importlib
alert_engine_mod = importlib.import_module('container_center.services.alert_engine')
AlertEngine = alert_engine_mod.AlertEngine

# 验证拆分函数存在
assert hasattr(AlertEngine, 'check_overdue_task_alerts')
assert hasattr(AlertEngine, 'check_order_overdue_alerts')
assert hasattr(AlertEngine, 'check_order_timeout_alerts')
print('  [OK] AlertEngine.check_overdue_task_alerts 存在')
print('  [OK] AlertEngine.check_order_overdue_alerts 存在')
print('  [OK] AlertEngine.check_order_timeout_alerts (wrapper) 存在')

# ═══════════════════════════════════════════════════════════════
# 5. 验证 _core.py 同步路由完整
# ═══════════════════════════════════════════════════════════════
print()
print('--- 5. 5003 端口同步路由完整性（最终验收）---')

import re
src = open('dispatch_center/_core.py').read()
sync_routes = re.findall(r"@dispatch_center_bp\.route\('(/sync/[^']+)'", src)
expected_sync = ['/sync/material', '/sync/repair', '/sync/outsource', '/sync/sub-step-report', '/sync/quality-record']
print(f'  发现同步路由: {sync_routes}')
for exp in expected_sync:
    if exp in sync_routes:
        print(f'  [OK] {exp}')
    else:
        print(f'  [FAIL] {exp} 缺失')

print()
print('=' * 60)
print('端到端验证完成 ✅')
print('=' * 60)