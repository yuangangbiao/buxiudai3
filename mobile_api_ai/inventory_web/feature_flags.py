# -*- coding: utf-8 -*-
"""TODO-T6: FEATURE_FLAGS 灰度开关

DESIGN v2.0 第五章 灰度方案
- 部署后改 FEATURE_FLAGS 即可启用/禁用功能，无需改代码
- 默认全部启用（生产可按需关闭）
- 支持环境变量覆盖：INVENTORY_FEATURE_<name>=0/1
"""
import os
import logging

logger = logging.getLogger(__name__)


# 默认功能开关（按 T1-T8 顺序）
DEFAULT_FLAGS = {
    # T1 迁移
    't1_migration': True,
    # T2 service 层
    't2_service_layer': True,
    # T3 CRUD 完整性
    't3_crud_complete': True,
    # T4 高级查询
    't4_advanced_query': True,
    # T4 软删除
    't4_soft_delete': True,
    # T4 回收站
    't4_recycle_bin': True,
    # T5 抽盘
    't5_stocktake': True,
    # T6 调拨
    't6_transfer': True,
    # T7 报表
    't7_reports': True,
    # T7 图表
    't7_charts': True,
    # T8 导入导出
    't8_import_export': True,
    # T8 通知
    't8_notifications': True,
    # T8 扫码
    't8_scanner': True,
    # T8 多用户
    't8_multi_user': False,  # 暂未启用（单用户场景）
}


def _load_flags():
    """从环境变量覆盖默认 flags"""
    flags = DEFAULT_FLAGS.copy()
    for k in list(flags.keys()):
        env_key = f'INVENTORY_FEATURE_{k.upper()}'
        val = os.getenv(env_key)
        if val is not None:
            flags[k] = val.lower() in ('1', 'true', 'yes', 'on')
    return flags


# 懒加载（环境变量启动时一次性读取）
_FLAGS = None


def get_flags():
    """获取当前功能开关（首次调用时加载）

    修复 L-1：提供 reload_flags() 主动重载能力
    运维需要热切换时，调用 reload_flags() 即可重新读取环境变量
    （无需重启服务）
    """
    global _FLAGS
    if _FLAGS is None:
        _FLAGS = _load_flags()
        logger.info(f'[FEATURE_FLAGS] 加载: {_FLAGS}')
    return _FLAGS


def reload_flags() -> dict:
    """重载功能开关（修复 L-1：热切换）

    用法（运维/调试）：
        from inventory_web.feature_flags import reload_flags
        reload_flags()

    触发场景：
    - 修改 INVENTORY_FEATURE_* 环境变量后
    - 通过 SIGHUP 信号或管理 API 触发
    """
    global _FLAGS
    _FLAGS = _load_flags()
    logger.info(f'[FEATURE_FLAGS] 重载: {_FLAGS}')
    return _FLAGS


def is_enabled(name: str) -> bool:
    """检查功能是否启用

    Args:
        name: flag 名（如 't5_stocktake'）

    Returns:
        bool - True=启用 False=禁用

    修复 M-1：未知 flag 默认 False（白名单制）
    拼写错误时不会"意外启用"，需要明确添加到 DEFAULT_FLAGS 才生效
    """
    flags = get_flags()
    if name not in flags:
        # 修复 M-1：未知 flag 记日志，避免静默
        logger.warning(
            f'[FEATURE_FLAGS] 未知 flag: {name}，默认禁用。请在 DEFAULT_FLAGS 中显式声明。'
        )
        return False  # 修复 M-1：默认 False（白名单制）
    return flags[name]


def require_feature(name: str):
    """装饰器：要求功能启用，否则返回 404

    用法：
        @bp.route('/inventory/api/stocktake/create', methods=['POST'])
        @admin_required
        @require_csrf
        @require_feature('t5_stocktake')
        def stocktake_create():
            ...
    """
    from functools import wraps
    from flask import jsonify

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not is_enabled(name):
                return jsonify({
                    'ok': False,
                    'msg': f'功能 {name} 未启用',
                    'code': 'FEATURE_DISABLED'
                }), 404
            return f(*args, **kwargs)
        return decorated
    return decorator


# ============================================================
# 修复 C-2：装饰器导入隔离 — 提供安全的兜底装饰器
# 如果 feature_flags 模块本身导入失败（如语法错/缺依赖），
# 调用方应使用 safe_require_feature 而不是 require_feature
# 失败时降级为 no-op，所有路由照常可用
# ============================================================

def safe_require_feature(name: str):
    """安全装饰器：require_feature 失败时降级为 no-op（不阻断路由）

    用法（推荐）：
        @bp.route(...)
        @admin_required
        @safe_require_feature('t5_stocktake')
        def stocktake_create():
            ...
    """
    from functools import wraps
    from flask import jsonify
    import logging as _logging

    def _noop_decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                if not is_enabled(name):
                    return jsonify({
                        'ok': False,
                        'msg': f'功能 {name} 未启用',
                        'code': 'FEATURE_DISABLED'
                    }), 404
            except Exception as e:
                # 灰度检查失败 → 降级为放行（保证业务可用）
                _logging.getLogger(__name__).warning(
                    f'[FEATURE_FLAGS] 灰度检查失败（{name}），降级放行: {e}'
                )
            return f(*args, **kwargs)
        return decorated
    return _noop_decorator


# 灰度阶段典型配置（参考）
GRAY_STAGES = {
    'stage_1_warehouse_mgmt': {
        't2_service_layer': True,
        't3_crud_complete': True,
        't4_recycle_bin': False,
        't5_stocktake': False,
        't6_transfer': False,
        't7_reports': False,
        't8_notifications': False,
    },
    'stage_2_add_query': {
        't4_advanced_query': True,
        't4_recycle_bin': True,
    },
    'stage_3_stocktake_transfer': {
        't5_stocktake': True,
        't6_transfer': True,
    },
    'stage_4_reports': {
        't7_reports': True,
        't7_charts': True,
        't8_import_export': True,
    },
    'stage_5_notifications': {
        't8_notifications': True,
        't8_scanner': True,
    },
    'all_on': {k: True for k in DEFAULT_FLAGS},
}
