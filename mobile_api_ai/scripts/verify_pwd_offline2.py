# -*- coding: utf-8 -*-
"""离线验证：相同 .env 加载逻辑下 Admin@2026 是否通过"""
import os
import sys
import hashlib
import hmac
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)

stored = os.getenv('INVENTORY_ADMIN_PASSWORD_HASH')
result_lines = []
result_lines.append(f'HASH (first 32): {stored[:32]}')
result_lines.append(f'HASH length: {len(stored)}')

salt_hex, hash_hex = stored.split('$', 1)
salt = bytes.fromhex(salt_hex)
expected = bytes.fromhex(hash_hex)
h = hashlib.pbkdf2_hmac('sha256', 'Admin@2026'.encode('utf-8'), salt, 200_000, dklen=64)
matches = hmac.compare_digest(h, expected)
result_lines.append(f'Admin@2026 matches: {matches}')

# 顺便验证其他几个常见密码
for pwd in ['88888888', 'admin', 'TestP@ssw0rd2024', 'SteelBelt@2026']:
    h = hashlib.pbkdf2_hmac('sha256', pwd.encode('utf-8'), salt, 200_000, dklen=64)
    result_lines.append(f'  {pwd} matches: {hmac.compare_digest(h, expected)}')

text = '\n'.join(result_lines)
Path(r'd:\yuan\verify_pwd_result.txt').write_text(text, encoding='utf-8')
print(text)
