@echo off
chcp 65001 >nul
title Cloud Service Starter
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0"

echo ===========================================
echo    Cloud Service Starter
echo ===========================================
echo.

REM --- check python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found, please install Python 3.8+
    pause
    exit /b 1
)

for /f "tokens=1,2*" %%i in ('python --version 2^>^&1') do set PY_VER=%%j
echo [Python] %PY_VER%
echo.

cd /d "%ROOT_DIR%"

REM --- add current dir to PYTHONPATH so local modules are found ---
set "PYTHONPATH=%ROOT_DIR%;%PYTHONPATH%"

REM --- clean old logs ---
if exist "%ROOT_DIR%log_5003.txt" del "%ROOT_DIR%log_5003.txt"
if exist "%ROOT_DIR%log_5006.txt" del "%ROOT_DIR%log_5006.txt"

REM --- 1. main wechat service (port 5003) ---
echo [1/2] Starting wechat server (port 5003)...
netstat -ano | findstr ":5003 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    start "ws5003" /D "%ROOT_DIR%" cmd /c "set PYTHONPATH=%ROOT_DIR%&& python wechat_server.py --port 5003 > log_5003.txt 2>&1"
    echo   + Launched wechat server
) else (
    echo   - Port 5003 already in use
)

REM --- 2. cloud helper service (port 5006) ---
echo [2/2] Starting cloud helper service (port 5006)...
netstat -ano | findstr ":5006 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    start "ch5006" /D "%ROOT_DIR%" cmd /c "set FLASK_PORT=5006&& set PYTHONPATH=%ROOT_DIR%&& python wechat_cloud.py > log_5006.txt 2>&1"
    echo   + Launched cloud helper
) else (
    echo   - Port 5006 already in use
)

echo.

REM --- wait for startup ---
echo Waiting for services to start (30 sec)...
ping -n 31 127.0.0.1 >nul

REM --- verify ports ---
echo.
echo ===========================================
echo  Port Status Check
echo ===========================================

set "ALL_OK=1"
for %%p in (5003 5006) do (
    netstat -ano | findstr ":%%p " | findstr "LISTENING" >nul
    if errorlevel 1 (
        echo  [Port %%p]  -- NOT LISTENING
        set "ALL_OK=0"
    ) else (
        echo  [Port %%p]  ++ RUNNING
    )
)

echo.

if "!ALL_OK!"=="1" (
    echo ===========================================
    echo  All services started successfully!
    echo ===========================================
) else (
    echo ===========================================
    echo  Some services failed, check log files below
    echo ===========================================
    echo.
    for %%f in (log_5003.txt log_5006.txt) do (
        if exist "%ROOT_DIR%%%f" (
            echo --- %%f ---
            type "%ROOT_DIR%%%f"
            echo.
        )
    )
)

echo.
echo  Access URLs:
echo   WeChat Server:     http://localhost:5003
echo   Cloud Helper:      http://localhost:5006
echo.
echo  Health Check:
echo   WeChat:  http://localhost:5003/api/health
echo   Cloud:   http://localhost:5006/api/health
echo.
echo  Press any key to exit...
pause >nul
