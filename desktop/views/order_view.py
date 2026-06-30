# -*- coding: utf-8 -*-
"""
订单管理视图（兼容层）
请使用 views.orders 下的新模块：
- views.orders.OrderListView
- views.orders.show_order_confirm
"""
from desktop.views.orders import OrderListView, show_order_confirm

__all__ = ['OrderListView', 'show_order_confirm']
