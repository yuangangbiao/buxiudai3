@echo off
REM 调拨死信清理 - Windows 任务计划程序安装脚本
REM TASK-T6 / TODO-T4
REM
REM 用法（管理员身份运行）：
REM   scripts\install_transfer_reaper_windows.bat
REM
REM 验证：
REM   schtasks /Query /TN "InventoryTransferReaper"

REM ============================================================
REM 修复 H-1：Windows 中文路径兼容
REM 强制 UTF-8 代码页 + 显式 PYTHONIOENCODING，
REM 解决 schtasks 在中文项目目录下编码错乱的问题
REM ============================================================
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

setlocal
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set REAPER=%PROJECT_DIR%\scripts\transfer_reaper.py
set TASK_NAME=InventoryTransferReaper
set PYTHON_EXE=python

echo === 调拨死信清理 - Windows 任务计划安装 ===
echo 项目目录: %PROJECT_DIR%
echo 清理脚本: %REAPER%

REM 检查脚本存在
if not exist "%REAPER%" (
    echo [FAIL] 清理脚本不存在: %REAPER%
    exit /b 1
)

REM 检查是否已存在
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [SKIP] 任务计划已存在: %TASK_NAME%
    schtasks /Query /TN "%TASK_NAME%" /V /FO LIST
    exit /b 0
)

REM 创建任务：每小时执行一次
schtasks /Create ^
    /TN "%TASK_NAME%" ^
    /TR "%PYTHON_EXE% \"%REAPER%\"" ^
    /SC HOURLY ^
    /ST 00:00 ^
    /RL HIGHEST ^
    /F

if %ERRORLEVEL% neq 0 (
    echo [FAIL] 创建任务失败
    exit /b 1
)

echo [OK] 已创建任务计划: %TASK_NAME%
echo.
echo 验证：
schtasks /Query /TN "%TASK_NAME%" /V /FO LIST | findstr "TaskName Status Next Run Time"
echo.
echo 立即测试运行：
cd /d "%PROJECT_DIR%"
%PYTHON_EXE% %REAPER%
echo.
echo 移除任务：schtasks /Delete /TN "%TASK_NAME%" /F
