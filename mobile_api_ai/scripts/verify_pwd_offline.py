# -*- coding: utf-8 -*-
"""通过本地 Flask test_client 验证：相同 .env 加载逻辑下 Admin@2026 是否通过"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 强制加载 .env
load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)
print('INVENTORY_ADMIN_PASSWORD_HASH =', os.getenv('INVENTORY_ADMIN_PASSWORD_HASH', '(missing)')[:60] + '...')
print('FLASK_SECRET_KEY (len):', len(os.getenv('FLASK_SECRET_KEY', '')))

# 验证密码
import hashlib
import hmac
stored = os.getenv('INVENTORY_ADMIN_PASSWORD_HASH')
salt_hex, hash_hex = stored.split('$', 1)
salt = bytes.fromhex(salt_hex)
expected = bytes.fromhex(hash_hex)
h = hashlib.pbkdf2_hmac('sha256', 'Admin@2026'.encode('utf-8'), salt, 200_000, dklen=64)
print('Admin@2026 matches:', hmac.compare_digest(h, expected))
