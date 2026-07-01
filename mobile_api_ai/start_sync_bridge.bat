@echo off
chcp 65001 > nul
echo ================================================
echo Sync Bridge Service Starter (Port 8008)
echo ================================================
echo.

cd /d "%~dp0"
echo Current Directory: %CD%
echo.

:: Use python from PATH
echo [Starting] Launching Sync Bridge Service...
start "" python "%~dp0sync_bridge_server.py"
echo.
echo [Done] Sync Bridge Service Started
echo [Port] 8008
echo [Health Check] http://127.0.0.1:8008/health
echo.
pause
