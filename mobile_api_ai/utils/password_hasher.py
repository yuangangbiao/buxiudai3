# -*- coding: utf-8 -*-
"""
[架构审计 P0 修复 2026-06-14] 密码哈希桩

之前：models.operator.py / _database_legacy.py 引用 `from utils.password_hasher import ...`
      但 utils/password_hasher.py 不存在 → 5008 import 失败
现在：基于 hashlib + secrets 实现 PBKDF2-HMAC-SHA256 密码哈希
"""
import os
import hashlib
import hmac
import secrets
import base64


_ALGO = 'pbkdf2_sha256'
_ITERATIONS = 200_000


def hash_password(plain: str) -> str:
    """[P0 修复 2026-06-14] 哈希密码（PBKDF2-HMAC-SHA256, 200k iter）

    Returns:
        'pbkdf2_sha256$200000$<salt_b64>$<hash_b64>'
    """
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', plain.encode('utf-8'), salt, _ITERATIONS)
    return f'{_ALGO}${_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}'


def verify_password(plain: str, hashed: str) -> bool:
    """[P0 修复 2026-06-14] 验证明文密码与哈希

    兼容老 hashlib md5 格式（"md5$<hex>"）和 PBKDF2
    """
    if not hashed:
        return False
    if hashed.startswith('md5$'):
        # 老格式：md5$<hex>，用于向后兼容旧存储的密码
        target = hashed[4:]
        return hmac.compare_digest(hashlib.md5(plain.encode('utf-8'), usedforsecurity=False).hexdigest(), target)  # nosec
    if hashed.startswith('pbkdf2_sha256$'):
        try:
            parts = hashed.split('$')
            if len(parts) != 4:
                return False
            _algo, iters, salt_b64, hash_b64 = parts
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(hash_b64)
            dk = hashlib.pbkdf2_hmac('sha256', plain.encode('utf-8'), salt, int(iters))
            return hmac.compare_digest(dk, expected)
        except Exception:
            return False
    # 不识别的格式 → 拒绝
    return False


def generate_random_password(length: int = 12) -> str:
    """[P0 修复 2026-06-14] 生成随机密码"""
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


__all__ = ['hash_password', 'verify_password', 'generate_random_password']
