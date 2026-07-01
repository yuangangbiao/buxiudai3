@echo off
chcp 65001 >nul
echo ============================================
echo  Cloud WeChat Service Starter
echo ============================================
echo.

pushd "%~dp0"

set "FLASK_PORT=5006"
set "PYTHONPATH=%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    popd
    exit /b 1
)

echo Starting cloud service on port 5006...
start "ch5006" cmd /c "set FLASK_PORT=5006&& set PYTHONPATH=%~dp0&& python wechat_cloud.py > log_5006.txt 2>&1"
echo Done. Check log_5006.txt for output.
pause
