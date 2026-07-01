@echo off
chcp 65001 >nul
title 不锈钢跟单系统 - 单用户模式
setlocal enabledelayedexpansion

:: ============================================
:: 单用户模式启动脚本（本地车间电脑）
:: 启动服务:
::   1. app.py (端口 5000 - 不锈钢跟单系统主服务)
:: ============================================

:: 切换到脚本所在目录
pushd "%~dp0"

call :print_banner

:: ========== 检查 Python ==========
call :print_step "检查 Python 环境"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [失败] Python 未安装或未加入 PATH
    echo        请安装 Python 3.8+ 并确保勾选 "Add Python to PATH"
    pause
    popd
    exit /b 1
)
for /f %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo [通过] %PY_VER%

:: ========== 检查端口占用 ==========
call :print_step "检查端口状态"
set PORT_MAIN=5000

call :check_port %PORT_MAIN%
if !PORT_FREE! equ 0 (
    echo [警告] 端口 %PORT_MAIN% 已被占用，尝试停止旧进程...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT_MAIN%') do (
        if "%%a" neq "0" (
            taskkill /f /pid %%a >nul 2>&1
        )
    )
    timeout /t 2 /nobreak >nul
    call :check_port %PORT_MAIN%
    if !PORT_FREE! equ 0 (
        echo [失败] 端口 %PORT_MAIN% 仍被占用，请手动释放
        pause
        popd
        exit /b 1
    )
    echo [修复] 端口 %PORT_MAIN% 已释放
) else (
    echo [通过] 端口 %PORT_MAIN% 可用
)

:: ========== 启动主服务 ==========
call :print_step "启动不锈钢跟单系统主服务"

echo.
echo  ┌─────────────────────────────────────────────┐
echo  │  正在启动移动报工API主服务...                  │
echo  │  端口: %PORT_MAIN%                              │
echo  └─────────────────────────────────────────────┘
echo.

start "MobileReportAPI" pythonw app.py
if %errorlevel% neq 0 (
    echo [失败] app.py 启动失败
    pause
    popd
    exit /b 1
)
echo [启动] 移动报工API (PID: 获取中...)
timeout /t 4 /nobreak >nul

:: ========== 验证服务状态 ==========
call :print_step "验证服务状态"

set ALL_OK=1

for /f "tokens=2" %%a in ('tasklist /fi "WindowTitle eq MobileReportAPI" /nh 2^>nul') do set PID1=%%a
if defined PID1 (
    echo [通过] 移动报工API 运行中 (PID: %PID1%)
) else (
    echo [警告] 移动报工API 可能未启动
    set ALL_OK=0
)

:: ========== 输出结果 ==========
echo.
if "!ALL_OK!"=="1" (
    call :print_success
) else (
    echo ⚠️ 服务启动异常，请检查上方警告信息
)

echo.
echo ─────────────────────────────────────────────
echo  操作说明:
echo    停止服务: 按任意键后选择关闭所有服务
echo    查看状态: 打开任务管理器查看 python 进程
echo ─────────────────────────────────────────────
echo.

pause

:: ========== 停止服务选项 ==========
echo.
echo ┌─────────────────────────────────────────────┐
echo │  是否停止服务?                               │
echo │  1 - 是，停止服务                            │
echo │  2 - 否，保持服务运行（推荐）                  │
echo └─────────────────────────────────────────────┘
echo.

set /p STOP_CHOICE="请选择 (1/2): "
if "!STOP_CHOICE!"=="1" (
    call :print_step "停止服务"
    taskkill /fi "WindowTitle eq MobileReportAPI" /f >nul 2>&1
    echo [完成] 服务已停止
) else (
    echo [信息] 服务保持运行
    echo         如需停止，请手动结束 python 进程或重新运行本脚本
)

popd
echo.
echo 按任意键退出...
pause >nul
exit /b 0

:: ========== 函数定义 ==========

:print_banner
echo.
echo ╔═══════════════════════════════════════════════════╗
echo ║      不锈钢网带跟单系统 - 单用户启动器            ║
echo ║      主服务: 移动报工API (端口 5000)              ║
echo ╚═══════════════════════════════════════════════════╝
echo.
echo 启动时间: %date% %time%
echo 工作目录: %CD%
echo.
goto :eof

:print_step
echo.
echo ─── %~1 ───
goto :eof

:print_success
echo ┌─────────────────────────────────────────────┐
echo │  ✅  服务启动成功!                           │
echo │                                              │
echo │  主API: http://localhost:5000                │
echo │  健康检查: http://localhost:5000/health      │
echo │                                              │
echo └─────────────────────────────────────────────┘
goto :eof

:check_port
set PORT_FREE=1
netstat -ano | findstr ":%1 " >nul 2>&1
if %errorlevel% equ 0 set PORT_FREE=0
goto :eof
