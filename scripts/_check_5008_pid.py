import subprocess
ps = r'''
Get-NetTCPConnection -LocalPort 5008 -ErrorAction SilentlyContinue | ForEach-Object {
  $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
  Write-Output ("PID=" + $_.OwningProcess + " StartTime=" + $p.StartTime + " Path=" + $p.Path)
}
'''
r = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True, encoding='utf-8')
print(r.stdout)
print('ERR:', r.stderr[:300])
