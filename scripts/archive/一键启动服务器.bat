@echo off
chcp 65001 >nul
title 库存管理系统 - 服务器启动工具
color 0A

cls
echo ============================================================
echo.
echo                    库存管理系统 - 服务器
echo.
echo ============================================================
echo.
echo 服务器配置信息：
echo.
echo    IP地址:   192.168.1.32
echo    端口:     8080
echo    API密钥:  steel_belt_inventory_key_2024
echo.
echo ============================================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python！请先安装Python 3.8+
    echo.
    pause
    exit /b 1
)

echo [OK] Python环境正常
echo.

REM 检查依赖
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖...
    pip install flask requests pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo [OK] 依赖检查完成
echo.

echo ============================================================
echo   正在启动服务器...
echo ============================================================
echo.
echo 提示：
echo   - 服务器启动后，请保持此窗口打开
echo   - 关闭窗口将停止服务器
echo   - 按 Ctrl+C 可以安全停止服务器
echo.
echo ============================================================
echo.

cd /d "%~dp0"
python inventory_server.py

pause
