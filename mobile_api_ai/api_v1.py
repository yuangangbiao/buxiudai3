# -*- coding: utf-8 -*-
"""
API版本控制蓝图模板

功能说明：
- 提供v1版本API蓝图模板
- 统一响应格式
- 标准化错误处理

使用方式：
    from api_v1 import api_v1_bp

    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
"""
import os
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, g

logger = logging.getLogger(__name__)

api_v1_bp = Blueprint('api_v1', __name__)


class APIResponse:
    """统一API响应格式"""

    @staticmethod
    def success(data=None, message='success', code=0):
        """成功响应"""
        return jsonify({
            'code': code,
            'message': message,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })

    @staticmethod
    def error(message, code=400, errors=None):
        """错误响应"""
        response = {
            'code': code,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        if errors:
            response['errors'] = errors
        return jsonify(response)

    @staticmethod
    def paginated(data, page, page_size, total, message='success'):
        """分页响应"""
        total_pages = (total + page_size - 1) // page_size
        return jsonify({
            'code': 0,
            'message': message,
            'data': {
                'items': data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            },
            'timestamp': datetime.now().isoformat()
        })


@api_v1_bp.before_request
def before_request():
    """请求前置处理"""
    g.request_id = request.headers.get('X-Request-ID') or os.urandom(8).hex()
    g.start_time = datetime.now()


@api_v1_bp.after_request
def after_request(response):
    """响应后置处理"""
    if hasattr(g, 'start_time'):
        duration = (datetime.now() - g.start_time).total_seconds()
        response.headers['X-Response-Time'] = f'{duration:.3f}s'

    if hasattr(g, 'request_id'):
        response.headers['X-Request-ID'] = g.request_id

    response.headers['X-API-Version'] = 'v1'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'

    return response


@api_v1_bp.errorhandler(400)
def bad_request(e):
    """400错误处理"""
    return APIResponse.error('请求参数错误', code=400), 400


@api_v1_bp.errorhandler(401)
def unauthorized(e):
    """401错误处理"""
    return APIResponse.error('未授权访问', code=401), 401


@api_v1_bp.errorhandler(403)
def forbidden(e):
    """403错误处理"""
    return APIResponse.error('禁止访问', code=403), 403


@api_v1_bp.errorhandler(404)
def not_found(e):
    """404错误处理"""
    return APIResponse.error('资源不存在', code=404), 404


@api_v1_bp.errorhandler(429)
def rate_limit(e):
    """429错误处理"""
    return APIResponse.error('请求过于频繁', code=429), 429


@api_v1_bp.errorhandler(500)
def internal_error(e):
    """500错误处理"""
    logger.error(f"[APIv1] 内部错误: {e}")
    return APIResponse.error('服务器内部错误', code=500), 500


@api_v1_bp.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return APIResponse.success({
        'service': 'mobile-report-api',
        'version': 'v1',
        'status': 'healthy'
    })


@api_v1_bp.route('/ping', methods=['GET'])
def ping():
    """心跳检测"""
    return APIResponse.success({'pong': True})
