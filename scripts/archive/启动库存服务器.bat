@echo off
chcp 65001 >nul
echo ========================================
echo 库存管理系统 - 服务器
echo ========================================
echo.

cd /d "%~dp0"

if not exist "venv" (
    echo 正在创建虚拟环境...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo 正在检查依赖...
pip install -q flask requests

echo.
echo 正在启动库存服务器...
echo.
python inventory_server.py

pause
