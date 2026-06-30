@echo off
chcp 65001 >nul
title 升级包生成工具

echo ============================================================
echo  不锈钢网带跟单系统 - 升级包生成工具
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%build_upgrade_package.py"

echo [信息] 脚本目录: %SCRIPT_DIR%
echo [信息] Python脚本: %PYTHON_SCRIPT%
echo.

REM 检查Python脚本是否存在
if not exist "%PYTHON_SCRIPT%" (
    echo [错误] 未找到升级包生成脚本
    pause
    exit /b 1
)

REM 运行升级包生成脚本
python "%PYTHON_SCRIPT%"

echo.
pause
