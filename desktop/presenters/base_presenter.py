# -*- coding: utf-8 -*-
"""基础 Presenter — MVP 模式通用基类"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BasePresenter:
    """MVP Presenter 基类，提供通用的 view/service 绑定与错误处理。

    Attributes:
        view: 关联的视图对象（可选），用于 UI 交互（如 show_error）。
        service: 关联的服务层对象（可选），用于业务逻辑委托。
    """

    def __init__(self, view: Optional[Any] = None, service: Optional[Any] = None) -> None:
        """初始化 Presenter。

        Args:
            view: 视图实例，需提供 show_error(str) 方法。
            service: 业务服务实例。
        """
        self.view: Optional[Any] = view
        self.service: Optional[Any] = service

    def handle_error(self, e: Exception) -> None:
        """统一错误处理：记录日志并通知视图。

        Args:
            e: 捕获的异常对象。
        """
        logger.error(f"[{self.__class__.__name__}] {e}", exc_info=True)
        if self.view is not None and hasattr(self.view, "show_error"):
            self.view.show_error(str(e))
