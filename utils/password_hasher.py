# -*- coding: utf-8 -*-
"""
密码哈希模块 - 提供安全的密码哈希和验证功能
"""
import hashlib
import secrets
import string


def hash_password(password, salt=None):
    """对密码进行哈希

    Args:
        password: 明文密码
        salt: 盐值，如果为None则自动生成

    Returns:
        tuple: (哈希值, 盐值)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )

    return pwd_hash.hex(), salt


def verify_password(password, pwd_hash, salt):
    """验证密码

    Args:
        password: 明文密码
        pwd_hash: 存储的哈希值
        salt: 存储的盐值

    Returns:
        bool: 密码是否正确
    """
    try:
        new_hash, _ = hash_password(password, salt)
        return secrets.compare_digest(new_hash, pwd_hash)
    except Exception:
        return False


def generate_random_password(length=12):
    """生成随机密码

    Args:
        length: 密码长度

    Returns:
        str: 随机密码
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
            return password


def is_password_strong(password):
    """检查密码强度

    Args:
        password: 明文密码

    Returns:
        tuple: (是否满足要求, 提示信息)
    """
    if len(password) < 8:
        return False, "密码长度至少8位"

    if not any(c.islower() for c in password):
        return False, "密码必须包含小写字母"

    if not any(c.isupper() for c in password):
        return False, "密码必须包含大写字母"

    if not any(c.isdigit() for c in password):
        return False, "密码必须包含数字"

    return True, "密码强度合格"
