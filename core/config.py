# -*- coding: utf-8 -*-
"""
统一配置模块 — 薄壳 facade

所有公开符号从子模块导入后 re-export，调用方无需改 import。
内部实现拆分:
  - _config_infra.py   — 路径/环境/数据库/超时/调度配置
  - _config_domain.py  — 材质/产品/工序/订单状态/业务阈值
  - _config_ui.py      — API密钥/字体/布局/窗口/颜色/遗留配置
  - _config_funcs.py   — 工具函数/Redis 事件总线
"""
from core._config_infra import *
from core._config_domain import *
from core._config_ui import *
from core._config_funcs import *

# import * 不导出 _ 前缀名，显式补洞
from core._config_infra import _env_loaded
