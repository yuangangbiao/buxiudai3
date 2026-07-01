# -*- coding: utf-8 -*-
"""调度中心模块

[v3.7.6 修复 2026-06-25] 用 try/except 包装所有 _core 导入
原因: _core.py 有外部依赖（如 template_engine），测试环境中可能缺失
      包装后即使 _core 加载失败，子模块（_dlq_retry, _metrics, publisher）
      仍可独立使用
"""
import logging
import sys
import os

logger = logging.getLogger(__name__)

# 项目根目录自动加入 sys.path（让 dispatch_center 顶级包导入工作）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
_PROJECT_PARENT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_MOBILE_API_AI = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _MOBILE_API_AI not in sys.path:
    sys.path.insert(0, _MOBILE_API_AI)


try:
    # [v3.7.6] 相对导入 + try/except 包装
    from ._core import *  # noqa: F401 F403
except ImportError as e:
    logger.warning(f'[v3.7.6] _core.py 加载失败（{e}），子模块仍可独立使用')


# 明确重导出被外部直接引用的符号
try:
    from ._core import (  # noqa: F401
        dispatch_center_bp,
        DispatchContext,
        DispatchDataCache,
        _dispatch_cache,
        _scheduler_manager,
        _ALERT_ENGINE_INTERVAL,
        on_quality_record_completed,
        start_background_scheduler,
        start_outbox_worker,
    )
except ImportError:
    pass


# 从 _constants.py 导出常量
try:
    from ._constants import (  # noqa: F401
        STATUS_KEY_TO_MYSQL,
        DISPATCH_RULES_DEFAULT,
        FLOW_MATCHING_RULES_DEFAULT,
        PRODUCT_TYPE_NAMES,
        PROCESS_FLOW_TEMPLATES,
        PROCESS_TEMPLATE_DEFAULTS,
        CONFIRMATION_REQUIRED_STEPS,
        CONFIRMATION_REPLY_KEYWORDS,
        DISPATCH_DOC_ID,
        DISPATCH_DOC_TYPE,
        CUSTOMER_GROUP_CACHE_TTL,
        OPERATOR_CACHE_TTL,
        WORK_ORDER_CACHE_TTL,
    )
except ImportError:
    pass


# v3.7.6 显式重导出 publisher
from .publisher import (  # noqa: F401
    BasePublisher,
    ReportPublisher,
    MaterialPublisher,
    QualityPublisher,
    TaskRecallPublisher,
    get_publisher,
    get_integration,  # 兼容
)