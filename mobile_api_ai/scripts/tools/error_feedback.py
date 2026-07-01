# -*- coding: utf-8 -*-
"""
错误反馈类型定义

定义所有匹配失败和处理失败的错误类型及提示消息
"""

from enum import Enum
from typing import Dict, Optional


class ErrorFeedbackType(Enum):
    # 订单相关
    ORDER_NOT_FOUND = "order_not_found"              # 未找到工单
    PROCESS_NOT_FOUND = "process_not_found"          # 工序不存在
    ORDER_COMPLETED = "order_completed"              # 工单已完成

    # 物料相关
    MATERIAL_NOT_FOUND = "material_not_found"        # 物料不存在
    MATERIAL_INSUFFICIENT = "material_insufficient"  # 物料不足

    # 维修相关
    REPAIR_NOT_FOUND = "repair_not_found"            # 维修工单不存在
    REPAIR_INCOMPLETE = "repair_incomplete"          # 上一道维修未完成

    # 报工相关
    PROCESS_INCOMPLETE = "process_incomplete"        # 上一道工序未完成
    QUANTITY_EXCEEDED = "quantity_exceeded"          # 报工数量超过计划
    DUPLICATE_REPORT = "duplicate_report"            # 重复报工

    # 操作相关
    INVALID_OPERATION = "invalid_operation"          # 无效操作
    OPERATION_FORBIDDEN = "operation_forbidden"      # 操作被禁止
    CONFIRMATION_REQUIRED = "confirmation_required" # 需要确认

    # 系统相关
    SYSTEM_ERROR = "system_error"                    # 系统错误
    TIMEOUT = "timeout"                              # 处理超时
    DATABASE_ERROR = "database_error"                 # 数据库错误

    # 求助相关
    HELP_CATEGORY_UNCLEAR = "help_category_unclear"  # 求助分类不明确

    # 未知错误
    UNKNOWN = "unknown"                              # 未知错误


class ErrorFeedback:
    """错误反馈"""

    ERROR_MESSAGES: Dict[ErrorFeedbackType, str] = {
        ErrorFeedbackType.ORDER_NOT_FOUND: "未找到工单 {order_no}，请核对订单号",
        ErrorFeedbackType.PROCESS_NOT_FOUND: "工单 {order_no} 无此工序 [{process}]，请核对",
        ErrorFeedbackType.ORDER_COMPLETED: "工单 {order_no} 已全部完成，无需再报",
        ErrorFeedbackType.MATERIAL_NOT_FOUND: "未找到物料 [{material_name}]，请检查名称",
        ErrorFeedbackType.MATERIAL_INSUFFICIENT: "物料 [{material_name}] 库存不足，当前库存: {stock}",
        ErrorFeedbackType.REPAIR_NOT_FOUND: "未找到维修工单 [{repair_no}]",
        ErrorFeedbackType.REPAIR_INCOMPLETE: "上一道维修未完成，请先完成 [{previous_repair}]",
        ErrorFeedbackType.PROCESS_INCOMPLETE: "上一道工序 [{process}] 未完成，请先完成",
        ErrorFeedbackType.QUANTITY_EXCEEDED: "报工数量超过计划数量，当前剩余: {remaining}",
        ErrorFeedbackType.DUPLICATE_REPORT: "今日已报过该工单，如需再次报工请回复「确认」",
        ErrorFeedbackType.INVALID_OPERATION: "该操作不允许，请检查指令格式",
        ErrorFeedbackType.OPERATION_FORBIDDEN: "此操作被禁止，请联系管理员",
        ErrorFeedbackType.CONFIRMATION_REQUIRED: "检测到重复操作，请回复「确认」继续",
        ErrorFeedbackType.SYSTEM_ERROR: "系统错误，请稍后重试",
        ErrorFeedbackType.TIMEOUT: "处理超时，请稍后重试",
        ErrorFeedbackType.DATABASE_ERROR: "数据库错误，请联系管理员",
        ErrorFeedbackType.HELP_CATEGORY_UNCLEAR: "您的求助已收到，但分类不明确，将转交调度中心处理",
        ErrorFeedbackType.UNKNOWN: "未知错误，请联系管理员",
    }

    ERROR_CODES: Dict[ErrorFeedbackType, int] = {
        ErrorFeedbackType.ORDER_NOT_FOUND: 404,
        ErrorFeedbackType.PROCESS_NOT_FOUND: 404,
        ErrorFeedbackType.ORDER_COMPLETED: 400,
        ErrorFeedbackType.MATERIAL_NOT_FOUND: 404,
        ErrorFeedbackType.MATERIAL_INSUFFICIENT: 400,
        ErrorFeedbackType.REPAIR_NOT_FOUND: 404,
        ErrorFeedbackType.REPAIR_INCOMPLETE: 400,
        ErrorFeedbackType.PROCESS_INCOMPLETE: 400,
        ErrorFeedbackType.QUANTITY_EXCEEDED: 400,
        ErrorFeedbackType.DUPLICATE_REPORT: 409,
        ErrorFeedbackType.INVALID_OPERATION: 400,
        ErrorFeedbackType.OPERATION_FORBIDDEN: 403,
        ErrorFeedbackType.CONFIRMATION_REQUIRED: 409,
        ErrorFeedbackType.SYSTEM_ERROR: 500,
        ErrorFeedbackType.TIMEOUT: 504,
        ErrorFeedbackType.DATABASE_ERROR: 500,
        ErrorFeedbackType.HELP_CATEGORY_UNCLEAR: 200,
        ErrorFeedbackType.UNKNOWN: 500,
    }

    @classmethod
    def get_message(cls, error_type: ErrorFeedbackType, **kwargs) -> str:
        """
        获取错误消息

        Args:
            error_type: 错误类型
            **kwargs: 格式化参数

        Returns:
            错误消息
        """
        template = cls.ERROR_MESSAGES.get(error_type, cls.ERROR_MESSAGES[ErrorFeedbackType.UNKNOWN])
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template

    @classmethod
    def get_code(cls, error_type: ErrorFeedbackType) -> int:
        """
        获取错误代码

        Args:
            error_type: 错误类型

        Returns:
            HTTP状态码
        """
        return cls.ERROR_CODES.get(error_type, 500)

    @classmethod
    def create_response(
        cls,
        error_type: ErrorFeedbackType,
        msg_id: str,
        to_user_id: str,
        **kwargs
    ) -> Dict:
        """
        创建错误响应

        Args:
            error_type: 错误类型
            msg_id: 消息ID
            to_user_id: 目标用户ID
            **kwargs: 额外参数

        Returns:
            错误响应字典
        """
        return {
            "msg_id": msg_id,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "source": "local_container",
            "to_user_id": to_user_id,
            "success": False,
            "message": cls.get_message(error_type, **kwargs),
            "error_type": error_type.value,
            "data": kwargs,
            "code": cls.get_code(error_type)
        }

    @classmethod
    def create_success_response(
        cls,
        msg_id: str,
        to_user_id: str,
        message: str,
        data: Optional[Dict] = None
    ) -> Dict:
        """
        创建成功响应

        Args:
            msg_id: 消息ID
            to_user_id: 目标用户ID
            message: 成功消息
            data: 额外数据

        Returns:
            成功响应字典
        """
        return {
            "msg_id": msg_id,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "source": "local_container",
            "to_user_id": to_user_id,
            "success": True,
            "message": message,
            "data": data or {},
            "code": 200
        }