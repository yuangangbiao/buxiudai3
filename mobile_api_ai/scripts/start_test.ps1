$ErrorActionPreference = 'SilentlyContinue'
$dir = 'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
$svc = @('container_center_api.py', 'app.py', 'wechat_server.py')
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq '' } | Stop-Process -Force
Start-Sleep 3
$svc | ForEach-Object {
    Write-Host "Starting $_"
    Start-Process python.exe -ArgumentList "$dir\$_" -WorkingDirectory $dir -WindowStyle Hidden
}
Start-Sleep 12
Write-Host "=== Health Check ==="
$r = curl.exe -s --max-time 4 "http://localhost:5000/health"
if ($LASTEXITCODE -eq 0) { Write-Host "DC: OK $r" } else { Write-Host "DC: FAIL $($LASTEXITCODE)" }
$r = curl.exe -s --max-time 4 "http://localhost:5002/health"
if ($LASTEXITCODE -eq 0) { Write-Host "CC: OK $r" } else { Write-Host "CC: FAIL $($LASTEXITCODE)" }
$r = curl.exe -s --max-time 4 "http://localhost:5003/health"
if ($LASTEXITCODE -eq 0) { Write-Host "WX: OK $r" } else { Write-Host "WX: FAIL $($LASTEXITCODE)" }
