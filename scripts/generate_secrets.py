#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量密钥生成助手
TASK-005 配套工具

用法:
    python scripts/generate_secrets.py                    # 生成 FLASK_SECRET_KEY
    python scripts/generate_secrets.py --admin "MyPwd!"  # 同时生成 admin 密码哈希
    python scripts/generate_secrets.py --write            # 直接写入 .env 文件

设计原则（jgs7）:
    - 不硬编码密码/secret_key 在源码中
    - 使用 secrets 模块（CSPRNG，非 random）
    - 默认输出到 stdout，--write 选项才写 .env
    - .env 文件不提交 git（已在 .gitignore 中）
"""
import secrets
import string
import sys
import os
import argparse
import hashlib
from pathlib import Path


def generate_flask_secret_key(length: int = 48) -> str:
    """生成 Flask SECRET_KEY（≥32 字符，4 类字符全包含）

    4 类字符:
        - 大写字母 (A-Z)
        - 小写字母 (a-z)
        - 数字 (0-9)
        - 特殊字符 (!@#$%^&*...)
    """
    if length < 32:
        raise ValueError(f'长度 {length} 不足 32 字符（inventory_api_server.py 强制）')

    # 确保每类字符至少出现一次
    alphabet_upper = string.ascii_uppercase
    alphabet_lower = string.ascii_lowercase
    alphabet_digit = string.digits
    alphabet_special = '!@#$%^&*-_+=?'

    # 用 secrets.choice（CSPRNG）
    chars = [
        secrets.choice(alphabet_upper),
        secrets.choice(alphabet_lower),
        secrets.choice(alphabet_digit),
        secrets.choice(alphabet_special),
    ]
    # 剩余字符随机
    all_chars = alphabet_upper + alphabet_lower + alphabet_digit + alphabet_special
    for _ in range(length - 4):
        chars.append(secrets.choice(all_chars))

    # 打乱顺序（避免前 4 位固定模式）
    result = ''.join(chars)
    # 简单洗牌
    lst = list(result)
    for i in range(len(lst) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        lst[i], lst[j] = lst[j], lst[i]
    return ''.join(lst)


def generate_admin_password_hash(password: str) -> str:
    """生成 admin 密码 PBKDF2 哈希（与 inventory_api_server.py 一致）

    inventory_api_server.py 验证逻辑:
        if len(salt_hex) != 32 or len(hash_hex) != 128:
            raise RuntimeError(...)

    所以 salt 16 字节（32hex）+ hash 64 字节（128hex）
    """
    salt = secrets.token_bytes(16)
    # pbkdf2_hmac 默认 iterations=1000，但我们用更高（inventory_api_server.py 未明文要求）
    # 用默认 1000 以兼容既有代码
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 1000)
    return f'{salt.hex()}${dk.hex()}'


def write_to_env(values: dict, env_path: Path) -> bool:
    """写入 .env 文件（保留已有内容，仅追加/更新指定键）"""
    if not env_path.exists():
        env_path.touch()
        print(f'[INFO] 已创建 {env_path}')

    lines = []
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

    # 已存在的 key 索引
    key_index = {}
    for i, line in enumerate(lines):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key = line.split('=', 1)[0].strip()
            key_index[key] = i

    # 更新或追加
    for key, value in values.items():
        new_line = f'{key}={value}\n'
        if key in key_index:
            lines[key_index[key]] = new_line
            print(f'[UPDATE] {key}')
        else:
            lines.append(new_line)
            print(f'[APPEND] {key}')

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    return True


def main():
    parser = argparse.ArgumentParser(description='环境变量密钥生成助手')
    parser.add_argument('--admin', type=str, default='', help='同时生成 admin 密码哈希（明文密码）')
    parser.add_argument('--write', action='store_true', help='直接写入 .env 文件（默认只输出到 stdout）')
    parser.add_argument('--env-path', type=str, default='', help='.env 文件路径（默认自动定位）')
    args = parser.parse_args()

    print('=' * 60)
    print('环境变量密钥生成助手')
    print('=' * 60)
    print()

    # 1. FLASK_SECRET_KEY
    flask_key = generate_flask_secret_key(48)
    print('[1] FLASK_SECRET_KEY (48 字符, 4 类字符):')
    print(f'    {flask_key}')
    print(f'    长度: {len(flask_key)}')
    # 校验
    cats = sum([
        any(c.isupper() for c in flask_key),
        any(c.islower() for c in flask_key),
        any(c.isdigit() for c in flask_key),
        any(not c.isalnum() for c in flask_key)
    ])
    print(f'    复杂度: {cats} 类（≥3 满足要求）')
    print()

    values = {'FLASK_SECRET_KEY': flask_key}

    # 2. admin 密码哈希
    if args.admin:
        admin_hash = generate_admin_password_hash(args.admin)
        print('[2] INVENTORY_ADMIN_PASSWORD_HASH:')
        print(f'    {admin_hash}')
        salt_hex, hash_hex = admin_hash.split('$', 1)
        print(f'    salt: {len(salt_hex)} hex (要求 32)')
        print(f'    hash: {len(hash_hex)} hex (要求 128)')
        values['INVENTORY_ADMIN_PASSWORD_HASH'] = admin_hash
        print()

    # 3. 写入 .env 或仅输出
    if args.write:
        # 定位 .env 路径
        if args.env_path:
            env_path = Path(args.env_path)
        else:
            # 默认 d:\yuan\不锈钢网带跟单3.0\.env
            env_path = Path(__file__).resolve().parent.parent / '.env'

        print(f'[WRITE] 目标: {env_path}')
        # 二次确认（防止误操作）
        if env_path.exists():
            print('⚠️  .env 文件已存在，将覆盖以下 key:')
            for k in values.keys():
                print(f'    - {k}')
            resp = input('确认覆盖? [y/N]: ').strip().lower()
            if resp != 'y':
                print('已取消')
                return 0
        write_to_env(values, env_path)
        print(f'✅ 已写入 {env_path}')
    else:
        print('[HINT] 默认只输出到 stdout')
        print('       如要直接写入 .env，请加 --write 参数')
        print()
        print('手动复制到 .env:')
        for k, v in values.items():
            print(f'  {k}={v}')

    print()
    print('=' * 60)
    print('完成！')
    print('=' * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
