#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增强版API签名校验模块 - 含Nonce校验、请求体哈希、时序校验"""

import os
import time
import hashlib
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class EnhancedAPISignature:
    """增强版API签名校验器"""

    def __init__(self, redis_client=None, secret_key=None, timestamp_tolerance=300):
        """
        初始化签名校验器

        Args:
            redis_client: Redis客户端（用于Nonce校验）
            secret_key: API签名密钥
            timestamp_tolerance: 时间戳容差（秒），默认5分钟
        """
        self.redis_client = redis_client
        self.secret_key = secret_key or os.getenv('API_SECRET_KEY')
        if not self.secret_key:
            raise ValueError("API_SECRET_KEY 未设置，请在 .env 文件中配置")
        self.timestamp_tolerance = timestamp_tolerance
        self.nonce_ttl = 600  # Nonce有效期10分钟

    def generate_signature(self, timestamp, nonce, body=b''):
        """
        生成API签名（供客户端使用）

        Args:
            timestamp: 时间戳（秒）
            nonce: 随机字符串
            body: 请求体字节

        Returns:
            str: 签名字符串
        """
        body_hash = hashlib.sha256(body).hexdigest()
        sign_str = f"{timestamp}{nonce}{body_hash}{self.secret_key}"
        return hashlib.sha256(sign_str.encode()).hexdigest()

    def validate_signature(self, request):
        """
        验证API签名（完整校验）

        校验流程:
        1. 参数完整性校验
        2. 时间戳校验（防止重放）
        3. Nonce重复使用校验（防止重放攻击）
        4. 请求体哈希校验（防止篡改）
        5. 签名匹配校验

        Args:
            request: Flask请求对象

        Returns:
            tuple: (是否有效, 错误信息)
        """
        timestamp = request.headers.get('X-Timestamp')
        nonce = request.headers.get('X-Nonce')
        signature = request.headers.get('X-Signature')
        body = request.get_data()

        if not all([timestamp, nonce, signature]):
            logger.warning("API签名参数缺失")
            return False, "缺少签名参数"

        try:
            timestamp_int = int(timestamp)
        except ValueError:
            logger.warning(f"时间戳格式错误: {timestamp}")
            return False, "时间戳格式错误"

        if abs(time.time() - timestamp_int) > self.timestamp_tolerance:
            logger.warning(f"API签名时间戳过期: {timestamp_int}, 当前: {time.time()}")
            return False, "时间戳已过期"

        if not self._validate_nonce(nonce):
            logger.warning(f"Nonce已被使用或无效: {nonce}")
            return False, "Nonce无效或已使用"

        body_hash = hashlib.sha256(body).hexdigest()
        expected_signature = self._calculate_signature(timestamp, nonce, body_hash)

        if signature != expected_signature:
            logger.warning(f"API签名校验失败: 期望 {expected_signature[:8]}, 实际 {signature[:8]}")
            return False, "签名校验失败"

        return True, None

    def _validate_nonce(self, nonce):
        """
        校验Nonce是否可用

        Args:
            nonce: Nonce字符串

        Returns:
            bool: 是否有效
        """
        if not self.redis_client:
            logger.warning("Redis未连接，跳过Nonce校验")
            return True

        nonce_key = f"api_nonce:{nonce}"

        try:
            if self.redis_client.exists(nonce_key):
                logger.warning(f"Nonce已被使用: {nonce}")
                return False

            self.redis_client.setex(nonce_key, self.nonce_ttl, "1")
            return True
        except Exception as e:
            logger.error(f"Nonce校验失败: {e}")
            return True

    def _calculate_signature(self, timestamp, nonce, body_hash):
        """
        计算签名

        Args:
            timestamp: 时间戳字符串
            nonce: Nonce字符串
            body_hash: 请求体哈希

        Returns:
            str: 签名字符串
        """
        sign_str = f"{timestamp}{nonce}{body_hash}{self.secret_key}"
        return hashlib.sha256(sign_str.encode()).hexdigest()


class SignatureRequired:
    """签名校验装饰器"""

    def __init__(self, redis_client=None):
        self.validator = EnhancedAPISignature(redis_client=redis_client)

    def __call__(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, jsonify

            is_valid, error_msg = self.validator.validate_signature(request)

            if not is_valid:
                logger.warning(f"签名校验失败: {error_msg}")
                return jsonify({
                    "code": 401,
                    "message": f"API签名校验失败: {error_msg}"
                }), 401

            return f(*args, **kwargs)

        return decorated_function


signature_validator = None


def init_signature_validator(redis_client=None):
    """初始化全局签名校验器"""
    global signature_validator
    signature_validator = EnhancedAPISignature(redis_client=redis_client)
    return signature_validator


def require_signature(f):
    """需要签名校验的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify

        global signature_validator
        if signature_validator is None:
            logger.error("签名校验器未初始化")
            return jsonify({"code": 500, "message": "服务器配置错误"}), 500

        is_valid, error_msg = signature_validator.validate_signature(request)

        if not is_valid:
            logger.warning(f"签名校验失败: {error_msg}")
            return jsonify({
                "code": 401,
                "message": f"API签名校验失败: {error_msg}"
            }), 401

        return f(*args, **kwargs)

    return decorated_function
