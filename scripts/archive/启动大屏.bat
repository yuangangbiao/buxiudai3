@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================================================
echo           大屏服务器启动中...
echo ================================================
echo.
python run_dashboard.py
pause
