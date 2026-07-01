# -*- coding: utf-8 -*-
"""
兼容层：mobile_api_ai/config/ 命名空间。

在 pytest 及某些入口点，Python 的绝对导入 `from config import X`
会被解析到本目录（因为 mobile_api_ai/ 在 sys.path 中靠前）。

本文件将所有必要的配置符号从核心模块 core.config 重新导出，
使 `from config import PROCESSES` 等语句能正常工作。

关键依赖关系：
  core.config
    └── from core._config_domain import *  → PROCESSES, PRODUCT_TYPES ...
    └── from core._config_ui     import *  → STOCK_WARNING_THRESHOLD, CONTAINER_CENTER_URL ...
  上述模块均不依赖 models/*，因此不会产生循环导入。

同时保留从 core._config_funcs 导入的 Config（供 app.py 使用）。
"""
from core._config_funcs import Config  # noqa: F401

from core.config import *  # noqa: F403,F401
