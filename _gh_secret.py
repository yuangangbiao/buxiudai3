import urllib.request, json, ssl, base64

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 从 SSH key 注释提取 token
token = None
with open(r'C:\Users\lenovo\.ssh\id_rsa_github') as f:
    for line in f:
        stripped = line.strip()
        if stripped.startswith('#'):
            token = stripped.lstrip('#').strip()
            break

if not token:
    print('未找到 token')
    exit(1)

print(f'Token: {token[:15]}...')

repo = 'yuangangbiao/buxiudai3'

def gh_api(method, path, data=None):
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        f'https://api.github.com{path}',
        method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            return json.loads(r.read()) if r.headers.get('Content-Length') != '0' else {}
    except urllib.error.HTTPError as e:
        return {'error': f'HTTP {e.code}', 'body': e.read().decode()[:200]}
    except Exception as e:
        return {'error': str(e)}

# 1. 获取 public key for encrypting secret
pk = gh_api('GET', f'/repos/{repo}/actions/secrets/public-key')
print(f'\nPublic key: {pk}')
key_id = pk.get('key_id')
key_val = pk.get('key_value')
if not key_id:
    print(f'❌ 获取公钥失败: {pk}')
    exit(1)

# 2. 获取 MySQL password
mysql_pwd = input('\n请输入 MySQL root 密码: ').strip()
if not mysql_pwd:
    print('密码为空，退出')
    exit(1)

# 3. 加密 secret
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

pub_key = serialization.load_pem_public_key(key_val.encode(), backend=default_backend())
encrypted = pub_key.encrypt(mysql_pwd.encode('utf-8'), padding.PKCS1v15())
encrypted_b64 = base64.b64encode(encrypted).decode('ascii')
print(f'加密后长度: {len(encrypted_b64)} bytes')

# 4. 创建/更新 secret
result = gh_api('PUT', f'/repos/{repo}/actions/secrets/MYSQL_ROOT_PASSWORD', {
    'encrypted_value': encrypted_b64,
    'key_id': key_id,
})
print(f'\n创建结果: {result}')

if 'error' in result:
    print(f'❌ 创建失败: {result}')
else:
    print('✅ MYSQL_ROOT_PASSWORD 创建成功！')
