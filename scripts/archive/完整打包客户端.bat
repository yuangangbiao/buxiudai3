@echo off
chcp 65001 >nul
title 库存管理客户端 - 完整打包与验证系统

echo ========================================
echo   库存管理客户端 - 完整打包与验证
echo ========================================
echo.

cd /d "%~dp0"

echo [系统检查]
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    echo.
    pause
    exit /b 1
)

echo Python环境检查通过
echo.
echo ========================================
echo 开始完整打包流程...
echo ========================================
echo.

python full_build_client.py

echo.
echo ========================================
if errorlevel 1 (
    echo   打包失败，请查看上方日志
) else (
    echo   打包成功完成！
)
echo ========================================
echo.
pause
