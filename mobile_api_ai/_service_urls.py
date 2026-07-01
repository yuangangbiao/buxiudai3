# -*- coding: utf-8 -*-
"""
服务 URL 集中访问入口

迁移背景（2026-06-09）：
    原位于 mobile_api_ai/constants.py（与项目根 constants.py 同名，pytest import 解析冲突）。
    移动到独立模块 _service_urls.py 以彻底消除文件名冲突。

使用方式：
    from _service_urls import ServiceURLs       # 相对导入（mobile_api_ai/ 内）
    from ._service_urls import ServiceURLs      # 相对导入（mobile_api_ai/ 子包内）
    from mobile_api_ai._service_urls import ServiceURLs  # 绝对导入（跨包）
"""
import os

from core.config import SERVICE_URLS as _CORE_SERVICE_URLS


class ServiceURLs:
    """服务URL常量（基于 core.config.SERVICE_URLS 的统一访问入口）"""
    CONTAINER_CENTER_URL = _CORE_SERVICE_URLS.get('container_center', 'http://127.0.0.1:5002')
    DISPATCH_CENTER_URL = _CORE_SERVICE_URLS.get('dispatch_center', 'http://127.0.0.1:5003')
    SYNC_BRIDGE_URL = _CORE_SERVICE_URLS.get('sync_bridge', 'http://127.0.0.1:5005')
    WECHAT_CLOUD_HOST_URL = _CORE_SERVICE_URLS.get('wechat_cloud', 'http://127.0.0.1:5006')
    WECHAT_SERVER_URL = _CORE_SERVICE_URLS.get('mobile_api', 'http://127.0.0.1:5003')
    MAIN_SOFTWARE_CALLBACK_URL = os.getenv('MAIN_SOFTWARE_CALLBACK_URL', 'http://127.0.0.1:5002/api/callback')
