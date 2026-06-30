@echo off
chcp 65001 >nul
echo ====================================
echo   库存管理系统 V3.0
echo ====================================
cd /d "%~dp0"
python inventory_manager_complete.py
pause
