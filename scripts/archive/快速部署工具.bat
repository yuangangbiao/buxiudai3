@echo off
chcp 65001 >nul
title 库存管理客户端 - 部署工具
cls

echo ============================================================
echo   库存管理客户端 - 完整部署包
echo ============================================================
echo.
echo [验证状态] 两轮验证已全部通过！
echo.
echo 请选择操作：
echo.
echo   [1] 打开最终部署包目录
echo   [2] 快速部署方案 A (Python脚本版)
echo   [3] 快速部署方案 B (便携版)
echo   [4] 打开EXE打包指南
echo   [5] 查看验证报告
echo   [0] 退出
echo.
echo ============================================================
set /p choice=请选择: 

if "%choice%"=="1" goto open_dir
if "%choice%"=="2" goto deploy_a
if "%choice%"=="3" goto deploy_b
if "%choice%"=="4" goto deploy_c
if "%choice%"=="5" goto show_report
if "%choice%"=="0" goto end

echo.
echo 无效选择！
pause
goto start

:open_dir
echo.
echo 正在打开部署包目录...
explorer "%~dp0client_final_complete"
goto end

:deploy_a
echo.
echo 正在打开 Python脚本版 部署包...
explorer "%~dp0client_final_complete\A_Python脚本版"
echo.
echo 提示：将此目录复制到U盘或目标电脑即可使用。
echo.
pause
goto end

:deploy_b
echo.
echo 正在打开 便携版 部署包...
explorer "%~dp0client_final_complete\B_便携版"
echo.
echo 提示：可选添加便携版Python到 python_portable/ 目录
echo.
pause
goto end

:deploy_c
echo.
echo 正在打开 EXE打包指南...
explorer "%~dp0client_final_complete\C_EXE打包指南"
echo.
pause
goto end

:show_report
echo.
echo ============================================================
echo   验证报告
echo ============================================================
type "%~dp0client_final_complete\验证报告.txt"
echo ============================================================
echo.
pause
goto end

:end
echo.
echo 部署完成！
timeout /t 2 >nul
