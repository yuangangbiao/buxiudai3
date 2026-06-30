"""查 generate_order_no 定义位置"""
import subprocess
ps_cmd = 'Get-ChildItem -Path "d:\\yuan\\不锈钢网带跟单3.0" -Recurse -Filter *.py -ErrorAction SilentlyContinue | Select-String -Pattern "def generate_order_no" | Select-Object -First 3 Path,LineNumber'
r = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], capture_output=True, text=True)
print(r.stdout[:1500])
print('stderr:', r.stderr[:300])
