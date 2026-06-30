# -*- coding: utf-8 -*-
"""
API签名认证模块

为主系统提供API签名和认证能力
基于 mobile_api_ai/modules/api_signature.py 封装
"""

import os
import time
import hashlib
import logging
import secrets
import json
from typing import Optional, Dict, Any, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


class APISignatureError(Exception):
    """API签名异常"""
    pass


class APISignature:
    """API签名验证器"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        timestamp_tolerance: int = 300
    ):
        """
        初始化签名验证器

        Args:
            secret_key: API签名密钥，默认从环境变量读取
            timestamp_tolerance: 时间戳容差（秒），默认5分钟
        """
        self.secret_key = secret_key or os.getenv('API_SECRET_KEY')
        if not self.secret_key:
            logger.warning("API_SECRET_KEY 未设置，API签名验证将被跳过")

        self.timestamp_tolerance = timestamp_tolerance
        self._nonce_cache: Dict[str, float] = {}

    def generate_signature(
        self,
        timestamp: Optional[int] = None,
        nonce: Optional[str] = None,
        body: bytes = b''
    ) -> Dict[str, str]:
        """
        生成API签名（供客户端使用）

        Args:
            timestamp: 时间戳（秒），默认当前时间
            nonce: 随机字符串，默认自动生成
            body: 请求体字节

        Returns:
            包含签名参数的字典
        """
        if timestamp is None:
            timestamp = int(time.time())

        if nonce is None:
            nonce = secrets.token_hex(16)

        body_hash = hashlib.sha256(body).hexdigest()
        sign_str = f"{timestamp}{nonce}{body_hash}{self.secret_key}"
        signature = hashlib.sha256(sign_str.encode()).hexdigest()

        return {
            'X-Timestamp': str(timestamp),
            'X-Nonce': nonce,
            'X-Signature': signature,
            'X-Body-Hash': body_hash
        }

    def validate_timestamp(self, timestamp: str) -> Tuple[bool, str]:
        """
        验证时间戳

        Args:
            timestamp: 时间戳字符串

        Returns:
            (是否有效, 错误信息)
        """
        try:
            timestamp_int = int(timestamp)
        except ValueError:
            return False, "时间戳格式错误"

        current_time = int(time.time())
        diff = abs(current_time - timestamp_int)

        if diff > self.timestamp_tolerance:
            return False, f"时间戳已过期（容差{self.timestamp_tolerance}秒）"

        return True, ""

    def validate_nonce(self, nonce: str) -> Tuple[bool, str]:
        """
        验证Nonce（防止重放攻击）

        Args:
            nonce: 随机字符串

        Returns:
            (是否有效, 错误信息)
        """
        current_time = time.time()

        for cached_nonce, cached_time in list(self._nonce_cache.items()):
            if current_time - cached_time > 600:
                del self._nonce_cache[cached_nonce]

        if nonce in self._nonce_cache:
            return False, "Nonce已被使用（重放攻击）"

        self._nonce_cache[nonce] = current_time
        return True, ""

    def validate_body(self, body: bytes, body_hash: str) -> Tuple[bool, str]:
        """
        验证请求体哈希

        Args:
            body: 请求体字节
            body_hash: 请求体哈希

        Returns:
            (是否有效, 错误信息)
        """
        computed_hash = hashlib.sha256(body).hexdigest()

        if computed_hash != body_hash.lower():
            return False, "请求体哈希不匹配（数据被篡改）"

        return True, ""

    def validate_signature(
        self,
        timestamp: str,
        nonce: str,
        signature: str,
        body: bytes = b''
    ) -> Tuple[bool, str]:
        """
        验证签名

        Args:
            timestamp: 时间戳
            nonce: 随机字符串
            signature: 签名字符串
            body: 请求体字节

        Returns:
            (是否有效, 错误信息)
        """
        if not self.secret_key:
            logger.warning("API_SECRET_KEY 未设置，跳过签名验证")
            return True, ""

        valid, msg = self.validate_timestamp(timestamp)
        if not valid:
            return False, msg

        valid, msg = self.validate_nonce(nonce)
        if not valid:
            return False, msg

        body_hash = hashlib.sha256(body).hexdigest()
        sign_str = f"{timestamp}{nonce}{body_hash}{self.secret_key}"
        expected_signature = hashlib.sha256(sign_str.encode()).hexdigest()

        if signature.lower() != expected_signature.lower():
            return False, "签名验证失败"

        return True, ""

    def validate_request(self, headers: Dict, body: bytes = b'') -> Tuple[bool, str]:
        """
        验证完整请求

        Args:
            headers: 请求头字典
            body: 请求体字节

        Returns:
            (是否有效, 错误信息)
        """
        timestamp = headers.get('X-Timestamp', '')
        nonce = headers.get('X-Nonce', '')
        signature = headers.get('X-Signature', '')
        body_hash = headers.get('X-Body-Hash', '')

        if not all([timestamp, nonce, signature]):
            return False, "缺少签名参数"

        if body and body_hash:
            valid, msg = self.validate_body(body, body_hash)
            if not valid:
                return False, msg

        return self.validate_signature(timestamp, nonce, signature, body)


class APIRateLimiter:
    """API速率限制器"""

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60
    ):
        """
        初始化速率限制器

        Args:
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}

    def _get_client_key(self, client_id: Optional[str] = None) -> str:
        """获取客户端标识"""
        return client_id or 'default'

    def is_allowed(self, client_id: Optional[str] = None) -> bool:
        """
        检查请求是否允许

        Args:
            client_id: 客户端标识，默认使用IP地址

        Returns:
            是否允许请求
        """
        client_key = self._get_client_key(client_id)
        current_time = time.time()

        if client_key not in self._requests:
            self._requests[client_key] = []

        self._requests[client_key] = [
            req_time for req_time in self._requests[client_key]
            if current_time - req_time < self.window_seconds
        ]

        if len(self._requests[client_key]) >= self.max_requests:
            logger.warning(f"速率限制触发: {client_key}")
            return False

        self._requests[client_key].append(current_time)
        return True

    def get_remaining(self, client_id: Optional[str] = None) -> int:
        """获取剩余请求次数"""
        client_key = self._get_client_key(client_id)

        if client_key not in self._requests:
            return self.max_requests

        current_time = time.time()
        recent_requests = [
            req_time for req_time in self._requests[client_key]
            if current_time - req_time < self.window_seconds
        ]

        return max(0, self.max_requests - len(recent_requests))

    def reset(self, client_id: Optional[str] = None) -> None:
        """重置请求计数"""
        client_key = self._get_client_key(client_id)

        if client_key in self._requests:
            del self._requests[client_key]


_api_signature_instance = None
_api_rate_limiter_instance = None


def get_api_signature() -> APISignature:
    """获取API签名验证器单例"""
    global _api_signature_instance
    if _api_signature_instance is None:
        _api_signature_instance = APISignature()
    return _api_signature_instance


def get_api_rate_limiter(
    max_requests: int = 100,
    window_seconds: int = 60
) -> APIRateLimiter:
    """获取API速率限制器单例"""
    global _api_rate_limiter_instance
    if _api_rate_limiter_instance is None:
        _api_rate_limiter_instance = APIRateLimiter(max_requests, window_seconds)
    return _api_rate_limiter_instance


def require_api_signature(func):
    """API签名验证装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from flask import request

        signature = get_api_signature()
        headers = {
            'X-Timestamp': request.headers.get('X-Timestamp', ''),
            'X-Nonce': request.headers.get('X-Nonce', ''),
            'X-Signature': request.headers.get('X-Signature', ''),
            'X-Body-Hash': request.headers.get('X-Body-Hash', '')
        }

        valid, msg = signature.validate_request(headers, request.get_data())

        if not valid:
            logger.warning(f"API签名验证失败: {msg}")
            from flask import jsonify
            return jsonify({'code': 401, 'message': f'认证失败: {msg}'}), 401

        return func(*args, **kwargs)

    return wrapper


def require_api_rate_limit(func):
    """API速率限制装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from flask import request, jsonify

        client_id = request.headers.get('X-Client-ID')
        limiter = get_api_rate_limiter()

        if not limiter.is_allowed(client_id):
            return jsonify({
                'code': 429,
                'message': '请求过于频繁，请稍后再试'
            }), 429

        return func(*args, **kwargs)

    return wrapper


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    signature = get_api_signature()

    print("=" * 60)
    print("API签名认证模块测试")
    print("=" * 60)

    print("\n--- 生成签名 ---")
    headers = signature.generate_signature()
    print(f"生成的签名头: {json.dumps(headers, indent=2)}")

    print("\n--- 验证签名 ---")
    valid, msg = signature.validate_request(headers)
    print(f"验证结果: {'通过' if valid else '失败'} - {msg}")

    print("\n--- 模拟篡改测试 ---")
    tampered_headers = headers.copy()
    tampered_headers['X-Timestamp'] = str(int(time.time()) - 600)
    valid, msg = signature.validate_request(tampered_headers)
    print(f"时间戳过期验证: {'通过' if valid else '失败'} - {msg}")

    print("\n--- 速率限制测试 ---")
    limiter = get_api_rate_limiter(max_requests=5, window_seconds=60)
    for i in range(7):
        allowed = limiter.is_allowed('test_client')
        remaining = limiter.get_remaining('test_client')
        print(f"请求{i+1}: {'允许' if allowed else '拒绝'} - 剩余次数: {remaining}")

    print("\n" + "=" * 60)
