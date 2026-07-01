# -*- coding: utf-8 -*-
"""临时重置库存管理员密码为 Admin@2026（生产前必须改回）"""
import hashlib
import secrets
import shutil
import time
from pathlib import Path

# 1) 生成新密码哈希
pwd = 'Admin@2026'
salt = secrets.token_bytes(16)
h = hashlib.pbkdf2_hmac('sha256', pwd.encode('utf-8'), salt, 200_000, dklen=64)
new_hash = salt.hex() + '$' + h.hex()
print('NEW_HASH:', new_hash)

# 2) 备份 .env
env_path = Path(r'd:\yuan\不锈钢网带跟单3.0\.env')
backup_path = env_path.with_suffix(env_path.suffix + f'.bak.{int(time.time())}')
shutil.copy2(env_path, backup_path)
print('BACKUP:', backup_path)

# 3) 替换第 5 行（index=4）
lines = env_path.read_text(encoding='utf-8').splitlines(keepends=True)
old_line = lines[4]
print('OLD_LINE:', old_line.strip())
lines[4] = 'INVENTORY_ADMIN_PASSWORD_HASH=' + new_hash + '\n'
env_path.write_text(''.join(lines), encoding='utf-8')
print('REPLACED line 5 OK')

# 4) 自检
import hmac
salt_b = bytes.fromhex(new_hash.split('$')[0])
hash_b = bytes.fromhex(new_hash.split('$')[1])
h2 = hashlib.pbkdf2_hmac('sha256', pwd.encode('utf-8'), salt_b, 200_000, dklen=64)
print('VERIFY:', hmac.compare_digest(h2, hash_b))
