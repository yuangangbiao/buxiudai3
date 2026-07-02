# -*- coding: utf-8 -*-
"""
[v3.6] 全局异常处理器

功能:
- 统一处理所有 Flask 异常
- 记录详细日志（含 trace_id）
- 返回脱敏后的响应（不暴露 DB 结构）

使用:
- from utils.exception_handler import register_exception_handlers
- register_exception_handlers(app)
"""
import logging
import traceback
import uuid
from flask import jsonify, g

logger = logging.getLogger(__name__)


class BusinessError(Exception):
    """业务异常基类"""
    def __init__(self, message: str, code: int = 3001, http_status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


def safe_error_response(e: Exception, http_status: int = 500):
    """统一异常处理：记录日志 + 返回 trace_id

    Args:
        e: 异常对象
        http_status: HTTP 状态码

    Returns:
        (response, status_code)
    """
    trace_id = str(uuid.uuid4())
    g.trace_id = trace_id
    logger.error(f'[{trace_id}] {type(e).__name__}: {e}\n{traceback.format_exc()}')
    return jsonify({
        'code': http_status,
        'message': '系统错误，请联系管理员',
        'trace_id': trace_id
    }), http_status


def register_exception_handlers(app):
    """注册全局异常处理器

    Args:
        app: Flask 应用实例
    """

    @app.errorhandler(BusinessError)
    def handle_business_error(e: BusinessError):
        return jsonify({
            'code': e.code,
            'message': e.message,
            'trace_id': g.get('trace_id', '')
        }), e.http_status

    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({
            'code': 4001,
            'message': '资源不存在',
            'trace_id': g.get('trace_id', '')
        }), 404

    @app.errorhandler(405)
    def handle_405(e):
        return jsonify({
            'code': 4002,
            'message': '方法不被允许',
            'trace_id': g.get('trace_id', '')
        }), 405

    @app.errorhandler(Exception)
    def handle_exception(e: Exception):
        return safe_error_response(e)
