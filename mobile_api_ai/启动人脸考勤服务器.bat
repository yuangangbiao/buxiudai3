@echo off
chcp 65001 >nul
title 人脸考勤服务器 5009
setlocal enabledelayedexpansion

set "ROOT_DIR=%~dp0"

echo ===========================================
echo    人脸考勤服务器 (端口 5009)
echo    独立于调度中心/容器中心
echo ===========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未检测到 Python 环境
    pause
    exit /b 1
)

cd /d "%ROOT_DIR%"
echo [INFO] 工作目录: %CD%
echo [INFO] 启动 5009 人脸考勤服务器...
echo.

py face_server.py

echo.
echo [INFO] 人脸考勤服务器已退出
pause
