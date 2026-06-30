# -*- coding: utf-8 -*-
"""
全局声明: order_no ≡ order_no

生效日期: 2026-05-27
适用范围: SteelBelt 3.0 全项目

规则:
1. production_orders.order_no = orders.order_no（排产时自动设置）
2. process_sub_steps.order_no = process_sub_steps.order_no（8008同步时自动设置）
3. wechat_container.db data_packages.related_order = 订单号（ORD-格式）
4. 已删除 generate_order_no 委托函数，统一使用 generate_order_no()
5. 所有新数据: order_no 列镜像 order_no 列

过渡:
- order_no 列保留6个月用于向后兼容
- 查询使用 (order_no = ? OR order_no = ?) 双重匹配
- 新代码只使用 order_no
"""
