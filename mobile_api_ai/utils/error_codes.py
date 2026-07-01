# -*- coding: utf-8 -*-
"""
[错误码字典 v1.0 - 2026-06-13]
落地 docs/模块化改造/ERROR_CODES.md 中定义的错误码
业务层用 ErrorCode.XXX 替代裸字符串

错误码格式：<类别码><序号>
- 1xxx: 通用错误（参数/权限/系统）
- 2xxx: 订单错误
- 3xxx: 报工错误
- 4xxx: 排产错误
- 5xxx: 同步错误
- 6xxx: 容器/镜像错误
- 9xxx: 业务层自定义
"""


class ErrorCode:
    """错误码字典"""

    # ===== 1xxx 通用错误 =====
    SUCCESS = (0, '操作成功')
    PARAM_MISSING = (1001, '参数缺失')
    PARAM_INVALID = (1002, '参数无效')
    PERMISSION_DENIED = (1003, '权限不足')
    AUTH_FAILED = (1004, '认证失败')
    INTERNAL_ERROR = (1500, '系统内部错误')
    DB_ERROR = (1501, '数据库错误')
    NETWORK_ERROR = (1502, '网络错误')
    RATE_LIMIT = (1503, '请求过于频繁')

    # ===== 2xxx 订单错误 =====
    ORDER_NOT_FOUND = (2001, '订单不存在')
    ORDER_DELETED = (2002, '订单已删除')
    ORDER_DUPLICATED = (2003, '订单重复')
    ORDER_LOCKED = (2004, '订单被锁定')
    ORDER_STATUS_INVALID = (2005, '订单状态非法')

    # ===== 3xxx 报工错误 =====
    SUBSTEP_NOT_FOUND = (3001, '报工记录不存在')
    SUBSTEP_DUPLICATED = (3002, '报工记录重复')
    SUBSTEP_QUANTITY_INVALID = (3003, '报工数量非法')
    SUBSTEP_STEP_NAME_INVALID = (3004, '工序名称非法')
    SUBSTEP_OPERATOR_INVALID = (3005, '操作员非法')

    # ===== 4xxx 排产错误 =====
    SCHEDULE_NOT_FOUND = (4001, '排产记录不存在')
    SCHEDULE_CONFLICT = (4002, '排产时间冲突')
    SCHEDULE_OVERDUE = (4003, '排产已超期')

    # ===== 5xxx 同步错误 =====
    SYNC_ETL_FAILED = (5001, 'ETL 同步失败')
    SYNC_MIRROR_FAILED = (5002, '镜像同步失败')
    SYNC_OUTBOX_DEAD = (5003, 'Outbox 死信')
    SYNC_TRACE_MISSING = (5004, 'trace_id 缺失')

    # ===== 6xxx 容器/镜像错误 =====
    MIRROR_AUTH_FAILED = (6001, '镜像路由鉴权失败')
    MIRROR_TABLE_NOT_FOUND = (6002, '镜像表不存在')
    MIRROR_FIELD_INVALID = (6003, '镜像字段非法')
    MIRROR_WRITE_FAILED = (6004, '镜像写入失败')

    # ===== 9xxx 业务自定义 =====
    BIZ_RULE_VIOLATION = (9001, '业务规则违反')
    BIZ_WORKFLOW_DENIED = (9002, '工作流拒绝')
    BIZ_DATA_INCONSISTENT = (9003, '数据不一致')

    @classmethod
    def get_message(cls, code: int) -> str:
        """获取错误码对应的中文消息"""
        for attr in dir(cls):
            v = getattr(cls, attr)
            if isinstance(v, tuple) and len(v) == 2 and v[0] == code:
                return v[1]
        return f'未知错误码 {code}'

    @classmethod
    def get_code(cls, name: str):
        """通过名称获取错误码"""
        if hasattr(cls, name):
            v = getattr(cls, name)
            if isinstance(v, tuple):
                return v
        return None


# 响应格式
def make_error(code: int, message: str = None, data: dict = None) -> dict:
    """统一错误响应"""
    msg = message or ErrorCode.get_message(code)
    return {
        'code': code,
        'message': msg,
        'data': data or {},
    }


def make_success(data: dict = None, message: str = '操作成功') -> dict:
    """统一成功响应"""
    return {
        'code': 0,
        'message': message,
        'data': data or {},
    }
