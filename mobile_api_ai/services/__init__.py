# -*- coding: utf-8 -*-
"""
services 包统一导出入口（2026-06-09 → 06-10 fix #2）

解决与项目根 services/__init__.py 的命名冲突：
  - 项目根 services/__init__.py: 导出 3 个业务服务
    （AuditService, OrderService, WeChatReportService）
  - 原 mobile_api_ai/services/__init__.py: 导出 6 个 API 服务
    （WeChatNotifier, SessionManager, CostService, StatsEngine, ReportScheduler + 帮助函数）

改造后：
  - 3 个项目根服务：re-export 自项目根 services
  - 6 个 mobile_api_ai 独有的 API 服务：保留自 mobile_api_ai/services
  - 统一通过 `from services import X` 访问

设计原则（与 utils __init__ shim 一致）：
  - 扩展 __path__：当 Python 将 services 解析到此文件时，__path__
    仅包含 mobile_api_ai/services/，子模块 import（如 from services.audit_service
    import ...）找不到项目根的同名文件。通过将项目根的 services/
    加入 __path__，让 Python 的模块搜索能 fallback 到项目根。
  - 公开 API 是两者的并集，向后兼容。
"""
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT_SERVICES = os.path.join(_PROJECT_ROOT, 'services')

# 扩展 __path__：当 Python 将此文件解析为 services 包时，子模块搜索
# 会同时覆盖 mobile_api_ai/services/（优先）和项目根 services/（fallback）
if _ROOT_SERVICES not in __path__:
    __path__.append(_ROOT_SERVICES)

# ── 项目根 services（3 个业务服务）──
from services.audit_service import AuditService, audit_log  # noqa: E402
from services.order_service import OrderService  # noqa: E402
from services.wechat_report_service import WeChatReportService  # noqa: E402

# ── mobile_api_ai 独有的 API 服务（6 个）──
from .notifier import WeChatNotifier, get_notifier, wechat_notifier  # noqa: E402
from .session import SessionManager, get_session_manager  # noqa: E402
from .cost_service import CostService  # noqa: E402
from .stats_engine import StatsEngine  # noqa: E402
from .scheduler import ReportScheduler, get_scheduler, start_scheduler  # noqa: E402

__all__ = [
    # 项目根 3 个业务服务
    'AuditService',
    'audit_log',
    'OrderService',
    'WeChatReportService',
    # mobile_api_ai 独有的 6 个 API 服务
    'WeChatNotifier',
    'get_notifier',
    'wechat_notifier',
    'SessionManager',
    'get_session_manager',
    'CostService',
    'StatsEngine',
    'ReportScheduler',
    'get_scheduler',
    'start_scheduler',
]
