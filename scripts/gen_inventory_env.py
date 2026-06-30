"""生成 inventory 启动所需环境变量"""
import os
import secrets
import hashlib

# 1. FLASK_SECRET_KEY ≥32 + 3 类字符
sk_chars = []
sk_chars.append(secrets.token_hex(8))     # 16 hex (数字+小写字母)
sk_chars.append(secrets.token_hex(8).upper())  # 16 大写
sk_chars.append(secrets.choice('!@#$%^&*-_=+'))  # 特殊字符
sk_chars.append(secrets.token_hex(8))     # 16 hex
sk = ''.join(sk_chars)
print(f'FLASK_SECRET_KEY={sk} (len={len(sk)})')
# 验证
import re
classes = sum(bool(re.search(p, sk)) for p in [r'[A-Z]', r'[a-z]', r'\d', r'[^A-Za-z0-9]'])
print(f'  复杂度等级: {classes} 类 (需 ≥3)')
print(f'  长度: {len(sk)} (需 ≥32)')

# 2. INVENTORY_ADMIN_PASSWORD_HASH (pbkdf2 salt$hash)
# 默认密码 yuan_inventory_admin
pwd = 'yuan_inventory_admin'
salt = secrets.token_bytes(16)
hash_val = hashlib.pbkdf2_hmac('sha256', pwd.encode('utf-8'), salt, 100000)
admin_hash = f'{salt.hex()}${hash_val.hex()}'
print(f'\nINVENTORY_ADMIN_PASSWORD_HASH={admin_hash} (len={len(admin_hash)})')
print(f'  默认密码: {pwd}')

# 输出到 .env
env_add = f'''
# [5010 inventory] 2026-06-14
FLASK_SECRET_KEY={sk}
INVENTORY_ADMIN_PASSWORD_HASH={admin_hash}
INVENTORY_DB_NAME=inventory_db
INVENTORY_API_PORT=5010
'''
print('\n--- 待追加到 .env ---')
print(env_add)
