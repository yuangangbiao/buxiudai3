# -*- coding: utf-8 -*-
"""密码哈希生成工具（CRITICAL Fix C5）

用法:
    python scripts/generate_password_hash.py "your-password"

输出:
    INVENTORY_ADMIN_PASSWORD_HASH=salt_hex$hash_hex

将此行写入 .env 文件。
"""
import hashlib
import secrets
import sys


def hash_password(pwd: str) -> str:
    """生成 pbkdf2_hmac 密码哈希（64 字节 = 128 hex 字符）"""
    salt = secrets.token_bytes(16)  # 16 字节 = 32 hex 字符
    h = hashlib.pbkdf2_hmac('sha256', pwd.encode('utf-8'), salt, 200_000, dklen=64)
    return f"{salt.hex()}${h.hex()}"


def verify_password(pwd: str, stored: str) -> bool:
    """验证密码（用于测试生成的哈希）"""
    import hmac
    salt_hex, hash_hex = stored.split('$', 1)
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    h = hashlib.pbkdf2_hmac('sha256', pwd.encode('utf-8'), salt, 200_000, dklen=64)
    return hmac.compare_digest(h, expected)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python generate_password_hash.py <password>')
        print('示例: python generate_password_hash.py "MyP@ssw0rd2024"')
        sys.exit(1)

    pwd = sys.argv[1]
    if len(pwd) < 8:
        print('[警告] 密码长度 < 8，建议 ≥12 位', file=sys.stderr)

    h = hash_password(pwd)
    print('=' * 60)
    print('将以下行添加到 .env 文件：')
    print('=' * 60)
    print(f'INVENTORY_ADMIN_PASSWORD_HASH={h}')
    print('=' * 60)

    # 自检
    if verify_password(pwd, h):
        print('[OK] 自检通过：哈希可正常验证')
    else:
        print('[FAIL] 自检失败！', file=sys.stderr)
        sys.exit(1)
