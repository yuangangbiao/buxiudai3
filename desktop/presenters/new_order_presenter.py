# -*- coding: utf-8 -*-
"""新建订单 Presenter"""

import logging
from typing import Any, Dict, Tuple, List, Optional

from desktop.presenters.base_presenter import BasePresenter
from services.order_service import OrderService

logger = logging.getLogger(__name__)


class NewOrderPresenter(BasePresenter):
    """新建订单页面的 Presenter。

    负责协调 NewOrderView 和 OrderService 之间的交互：
    - 表单校验委托给 desktop.views.validators.order_form_validator
    - 订单创建委托给 OrderService 单例
    """

    def __init__(self, view: Optional[Any] = None) -> None:
        """初始化新建订单 Presenter。

        Args:
            view: 新建订单视图实例（需提供 show_error(str) 方法）。
        """
        super().__init__(view=view, service=OrderService.get_instance())

    def create_order(self, data: Dict[str, Any]) -> Optional[Any]:
        """创建订单。

        Args:
            data: 订单表单数据字典。

        Returns:
            创建成功的订单对象，失败则返回 None。
        """
        try:
            logger.info(f"[NewOrderPresenter] 创建订单: {data.get('customer_name', '?')} — "
                        f"{data.get('product_type', '?')}")
            order = self.service.create_order(data)
            logger.info(f"[NewOrderPresenter] 订单创建成功: {getattr(order, 'id', order)}")
            return order
        except Exception as e:
            self.handle_error(e)
            return None

    def validate_order(self, data: Dict[str, Any],
                       dim_fields: Optional[List[Dict]] = None) -> Tuple[bool, List[str]]:
        """校验订单表单数据。

        Args:
            data: 表单收集的数据字典。
            dim_fields: 尺寸参数字段定义列表（可选），用于必填项校验。

        Returns:
            (is_valid, errors): 校验通过标志和错误信息列表。
        """
        from desktop.views.validators.order_form_validator import validate_order_form

        return validate_order_form(data, dim_fields)
