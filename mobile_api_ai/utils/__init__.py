# -*- coding: utf-8 -*-
"""
utils 包统一导出入口（2026-06-09 → 06-10 fix #2）

解决与项目根 utils/__init__.py 的命名冲突：
  - 项目根 utils/__init__.py: 导出 5 个 validator 类（OrderValidator 等）
  - 原 mobile_api_ai/utils/__init__.py: 仅导出 3 个 http_client 类

改造后：
  - 5 个 validator：re-export 自项目根 utils.validators
  - 3 个 http_client：re-export 自同包 mobile_api_ai.utils.http_client
  - 统一通过 `from utils import X` 或 `from mobile_api_ai.utils import X` 访问

设计原则：
  - 扩展 __path__：当 Python 将 utils 解析到此文件时，__path__
    仅包含 mobile_api_ai/utils/，子模块 import（如 from utils.validators
    import ...）找不到项目根的同名文件。通过将项目根的 utils/
    加入 __path__，让 Python 的模块搜索能 fallback 到项目根。
  - 公开 API 是两者的并集，向后兼容。
"""
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT_UTILS = os.path.join(_PROJECT_ROOT, 'utils')

# 扩展 __path__：当 Python 将此文件解析为 utils 包时，子模块搜索
# 会同时覆盖 mobile_api_ai/utils/（优先）和项目根 utils/（fallback）
if _ROOT_UTILS not in __path__:
    __path__.append(_ROOT_UTILS)

# ── 项目根 utils.validators（5 个 validator 类）──
from utils.validators import (  # noqa: E402
    CommonValidators,
    OrderValidator,
    ProcessValidator,
    InventoryValidator,
    FormValidator,
)

# ── mobile_api_ai 独有的 http_client（3 个类）──
from .http_client import (  # noqa: E402
    SyncBridgeClient,
    ContainerCenterClient,
    HttpClientError,
)

__all__ = [
    # 项目根 5 个 validator
    'CommonValidators',
    'OrderValidator',
    'ProcessValidator',
    'InventoryValidator',
    'FormValidator',
    # mobile_api_ai 独有的 3 个 http_client
    'SyncBridgeClient',
    'ContainerCenterClient',
    'HttpClientError',
]
