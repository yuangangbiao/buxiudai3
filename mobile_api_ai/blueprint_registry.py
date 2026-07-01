# -*- coding: utf-8 -*-
"""Blueprint 自动注册模块
使用声明式配置实现 Flask Blueprint 统一注册，新增模块只需在列表中添加条目即可。
"""
import logging
from importlib import import_module

logger = logging.getLogger(__name__)

BLUEPRINT_ENTRIES = [
    # (module_path, bp_attr_name, url_prefix_override)
    # url_prefix_override=None 表示使用 Blueprint 构造函数自带的 url_prefix
    ('face_checkin', 'bp', None),
    ('dispatch_center', 'dispatch_center_bp', None),
    ('container_dashboard', 'container_dashboard_bp', '/container'),
    ('schedule_flow', 'schedule_bp', None),
    ('config_center', 'config_center_bp', None),
    ('data_collector_api', 'data_collector_bp', None),
    ('mobile_api_ai.api.auth', 'bp', None),
    ('mobile_api_ai.api.process', 'bp', None),
    ('mobile_api_ai.api.quality', 'bp', None),
    ('mobile_api_ai.api.approval', 'bp', None),
    ('mobile_api_ai.api.message', 'bp', None),
    ('mobile_api_ai.api.stats', 'bp', None),
    ('mobile_api_ai.api.scan', 'bp', None),
    ('mobile_api_ai.api.ai', 'bp', None),
    ('mobile_api_ai.api.cost', 'bp', None),
    ('mobile_api_ai.api.reports', 'bp', None),
]


def register_all_blueprints(app):
    """自动注册所有声明的 Blueprint 到 Flask 应用"""
    for module_path, bp_name, url_prefix in BLUEPRINT_ENTRIES:
        try:
            module = import_module(module_path)
            bp = getattr(module, bp_name)
            if url_prefix:
                app.register_blueprint(bp, url_prefix=url_prefix)
            else:
                app.register_blueprint(bp)
            display_path = url_prefix or getattr(bp, 'url_prefix', '/')
            logger.info("[注册] %s ← %s (%s)", bp_name, module_path, display_path)
        except Exception as e:
            logger.warning("[注册] %s 注册失败: %s", bp_name, e)
