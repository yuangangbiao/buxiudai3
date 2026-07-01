@echo off
chcp 65001 >nul
title 调度中心服务

cd /d "%~dp0"

echo [调度中心] 正在启动服务...
echo.

py -B wechat_server.py

pause
