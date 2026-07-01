# -*- coding: utf-8 -*-
"""统一 8008 同步调用 — 唯一入口"""
import os, urllib.request, json as _json, logging

logger = logging.getLogger(__name__)

SYNC_BRIDGE_URL = os.getenv('SYNC_BRIDGE_URL', 'http://127.0.0.1:8008')


def send(endpoint: str, payload: dict, timeout: float = 5) -> bool:
    """向 8008 发送同步通知，返回是否成功"""
    try:
        url = f'{SYNC_BRIDGE_URL}/api/sync/{endpoint}'
        data = _json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception as e:
        logger.debug('[SyncBridge] 通知失败: %s %s', endpoint, e)
        return False
