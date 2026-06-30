import requests, json, os

gh_token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
gh_app_token = os.environ.get('GITHUB_APP_TOKEN')
gh_api_key = os.environ.get('GITHUB_API_KEY')

print(f'GITHUB_TOKEN: {"已设置" if gh_token else "未设置"}')
print(f'GITHUB_APP_TOKEN: {"已设置" if gh_app_token else "未设置"}')
print(f'GITHUB_API_KEY: {"已设置" if gh_api_key else "未设置"}')

# 检查 GitHub CLI
import subprocess
try:
    r = subprocess.run(['gh', '--version'], capture_output=True, text=True, timeout=10)
    print(f'gh CLI: {r.stdout.strip()}')
except FileNotFoundError:
    print('gh CLI: 未安装')
except Exception as e:
    print(f'gh CLI: {e}')

# 检查 .env 中的 token
env_file = r'D:\yuan\不锈钢网带跟单3.0\.env'
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if 'GITHUB' in line.upper() and '=' in line:
                key = line.split('=')[0].strip()
                print(f'.env: {key} = {"已设置" if line.split("=",1)[1].strip() else "空"}')
