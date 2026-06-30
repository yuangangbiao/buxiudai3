@echo off
chcp 65001 >nul
echo ========================================
echo 库存管理系统 - 配置器
echo ========================================
echo.

cd /d "%~dp0"

python inventory_configurator.py

pause
