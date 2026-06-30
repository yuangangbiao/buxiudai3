"""找 MySQL 真实密码 - 全项目搜 + 系统环境变量 + 启动脚本"""
import subprocess
import os

# 1. 系统环境变量 (User/Process/System)
print('='*70)
print('【1. 系统环境变量里的 MYSQL 配置】')
print('='*70)
for scope in ['User', 'Process']:
    out = subprocess.run(['powershell', '-NoProfile', '-Command', f'[System.Environment]::GetEnvironmentVariable("MYSQL_PASSWORD", "{scope}")'], capture_output=True, text=True, timeout=5)
    pwd = out.stdout.strip()
    out2 = subprocess.run(['powershell', '-NoProfile', '-Command', f'[System.Environment]::GetEnvironmentVariable("MYSQL_USER", "{scope}")'], capture_output=True, text=True, timeout=5)
    user = out2.stdout.strip()
    print(f'  {scope}: MYSQL_USER={user!r}, MYSQL_PASSWORD={pwd!r}')

# 2. 看现在的 python 进程环境 (Powershell $env)
print()
print('【2. 当前 PowerShell $env MYSQL_*】')
out = subprocess.run(['powershell', '-NoProfile', '-Command', 'gci env:MYSQL_* | Format-Table Name,Value -AutoSize'], capture_output=True, text=True, timeout=5)
print(out.stdout)

# 3. 全项目搜 root888
print('='*70)
print('【3. 项目里 root888 在哪用】')
print('='*70)
out = subprocess.run(['powershell', '-NoProfile', '-Command', "Get-ChildItem -Path D:\\yuan\\不锈钢网带跟单3.0 -Recurse -Include *.py,*.env,*.cfg,*.ini,*.bat,*.cmd,*.ps1 -ErrorAction SilentlyContinue | Select-String -Pattern 'root888' -ErrorAction SilentlyContinue | Select-Object -First 10 | ForEach-Object { $_.Path.Substring(30) + ':' + $_.LineNumber + ' ' + $_.Line.Trim() }"], capture_output=True, text=True, timeout=15)
print(out.stdout[:2000])

# 4. 全项目搜各种 password=xxx
print()
print('='*70)
print('【4. 全项目搜 password=xxx (非空)】')
print('='*70)
out = subprocess.run(['powershell', '-NoProfile', '-Command', "Get-ChildItem -Path D:\\yuan\\不锈钢网带跟单3.0 -Recurse -Include *.py,*.env,*.cfg,*.ini,*.bat,*.cmd,*.ps1 -ErrorAction SilentlyContinue | Select-String -Pattern 'password\\s*=\\s*[\\'\\\"][^\\'\\\"]*[\\'\\\"]' -ErrorAction SilentlyContinue | Select-Object -First 30 | ForEach-Object { $_.Path.Substring(30) + ':' + $_.LineNumber + ' ' + $_.Line.Trim().Substring(0, [Math]::Min(80, $_.Line.Trim().Length)) }"], capture_output=True, text=True, timeout=15)
print(out.stdout[:2500])

# 5. 启动脚本
print()
print('='*70)
print('【5. 启动脚本 (.bat .cmd .ps1)】')
print('='*70)
for ext in ['*.bat', '*.cmd', '*.ps1', '*.sh']:
    out = subprocess.run(['powershell', '-NoProfile', '-Command', f"Get-ChildItem -Path D:\\yuan\\不锈钢网带跟单3.0 -Recurse -Filter '{ext}' -ErrorAction SilentlyContinue | Select-Object -First 5 | ForEach-Object {{ $_.FullName.Substring(30) }}"], capture_output=True, text=True, timeout=5)
    if out.stdout.strip():
        print(f'  {ext}:')
        print(out.stdout)
