# -*- coding: utf-8 -*-
"""
配置模块入口
将 core.config 中的所有配置重新导出，方便旧代码使用
"""
from core.config import (
    # 路径配置
    BASE_DIR,
    DATA_DIR,
    CONFIG_DIR,
    LOG_DIR,

    # 应用信息
    APP_NAME,
    APP_VERSION,
    RESOURCE_DIR,

    # 数据库配置
    DB_PATH,
    MYSQL_CONFIG,
    DatabaseConfig,
    get_db_config,
    is_sqlite,
    get_sqlite_path,

    # 材质配置
    MATERIALS,
    MATERIAL_DENSITIES,
    PRESET_MAT_PARAMS,

    # 尺寸参数
    PRESET_DIM_PARAMS,

    # 业务选项
    PRODUCT_TYPES,
    SURFACE_TREATMENTS,
    ORDER_STATUS,
    PROCESSES,
    UNITS,

    # 质检配置
    INSPECTION_TYPES,
    INSPECTION_RESULTS,
    INSPECTION_ITEMS_BY_CATEGORY,

    # 阈值配置
    STOCK_WARNING_THRESHOLD,
    BusinessConfig,

    # API密钥
    ApiKeyConfig,

    # 样式配置
    FONTS,
    COLORS,
    StyleConfig,

    # 布局配置
    LAYOUT,

    # 窗口配置
    WINDOW_SIZES,
    WINDOW,
    CONTAINER_CENTER_URL,

    # 兼容存根
    Config,

    # 工具函数
    get_data_path,
    get_config_path,
    ensure_dir,
)

__all__ = [
    # 路径配置
    'BASE_DIR',
    'DATA_DIR',
    'CONFIG_DIR',
    'LOG_DIR',

    # 应用信息
    'APP_NAME',
    'APP_VERSION',
    'RESOURCE_DIR',

    # 数据库配置
    'DB_PATH',
    'MYSQL_CONFIG',
    'DatabaseConfig',
    'get_db_config',
    'is_sqlite',
    'get_sqlite_path',

    # 材质配置
    'MATERIALS',
    'MATERIAL_DENSITIES',
    'PRESET_MAT_PARAMS',

    # 尺寸参数
    'PRESET_DIM_PARAMS',

    # 业务选项
    'PRODUCT_TYPES',
    'SURFACE_TREATMENTS',
    'ORDER_STATUS',
    'PROCESSES',
    'UNITS',

    # 质检配置
    'INSPECTION_TYPES',
    'INSPECTION_RESULTS',
    'INSPECTION_ITEMS_BY_CATEGORY',

    # 阈值配置
    'STOCK_WARNING_THRESHOLD',
    'BusinessConfig',

    # API密钥
    'ApiKeyConfig',

    # 样式配置
    'FONTS',
    'COLORS',
    'StyleConfig',

    # 布局配置
    'LAYOUT',

    # 窗口配置
    'WINDOW_SIZES',
    'WINDOW',

    # 容器中心
    'CONTAINER_CENTER_URL',

    # 兼容存根
    'Config',

    # 工具函数
    'get_data_path',
    'get_config_path',
    'ensure_dir',
]
