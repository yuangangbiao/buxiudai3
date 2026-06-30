# Kill old 5001 processes
Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "Killed any process listening on 5001"

# Kill any python process running desktop_web/server.py
Get-Process python* -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*desktop_web*server*' } | ForEach-Object {
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    Write-Host ("Killed desktop_web PID " + $_.Id)
}

Start-Sleep -Seconds 2

# Start desktop_web
$PY = "C:\Users\lenovo\AppData\Local\Python\bin\python3.14-64.exe"
$SCRIPT = "d:\yuan\不锈钢网带跟单3.0\desktop_web\server.py"
$CWD = "d:\yuan\不锈钢网带跟单3.0"
$LOG = "d:\yuan\不锈钢网带跟单3.0\logs\5001.log"
$null = New-Item -ItemType Directory -Path (Split-Path $LOG -Parent) -Force -ErrorAction SilentlyContinue

Write-Host "Starting desktop_web (5001)..."
$logFp = [System.IO.File]::Open($LOG, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write, [System.IO.FileShare]::ReadWrite)
$proc = Start-Process -FilePath $PY -ArgumentList $SCRIPT -WorkingDirectory $CWD -PassThru -WindowStyle Hidden
Write-Host ("Started PID=" + $proc.Id)

Start-Sleep -Seconds 8

# Verify
$listening = Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue
if ($listening) {
    Write-Host ("SUCCESS: 5001 is listening on PID " + $listening[0].OwningProcess)
} else {
    Write-Host "WARNING: 5001 is not listening yet. Check logs:"
    if (Test-Path $LOG) {
        Get-Content $LOG -Tail 20
    }
}
