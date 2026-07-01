@echo off
chcp 65001 >nul
echo ============================================
echo  Cloud Relay Service (精简转发)
echo ============================================
echo.

pushd "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    popd
    exit /b 1
)

echo Starting cloud relay on port 5005...
start "cloud-relay" cmd /c "python cloud_relay.py > logs\cloud_relay.log 2>&1"
echo Done. Check logs\cloud_relay.log for output.
pause
