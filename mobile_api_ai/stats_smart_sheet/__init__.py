# -*- coding: utf-8 -*-
"""
stats_smart_sheet 模块
工单 + 库存统计表自动写入企业微信智能表格

架构: 本地 stats 计算 → 5005 (cloud_relay) → 云端 5004 (cloud_group_bot) → 智能表格
数据源: steel_belt / container_center / inventory_db 三个 MySQL 库
"""
__version__ = "1.0.0"
