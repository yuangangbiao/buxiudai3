@echo off
chcp 65001 >nul
title 库存管理客户端 - 超级快速启动
color 0B

cls
echo ===============================================================================
echo.
echo                            ╔═══════════════════════╗
echo                            ║  超级简单！只需要复制  ║
echo                            ╚═══════════════════════╝
echo.
echo ===============================================================================
echo.
echo 部署包已准备好！您只需要：
echo.
echo   [1] 打开最终部署包目录（复制整个文件夹到U盘）
echo   [2] 只复制核心文件（简单版）
echo   [3] 查看超级简单使用说明
echo   [4] 运行一键部署工具
echo   [0] 退出
echo.
echo ===============================================================================
set /p choice=请选择: 

if "%choice%"=="1" goto open_deploy
if "%choice%"=="2" goto open_simple
if "%choice%"=="3" goto open_readme
if "%choice%"=="4" goto tool
if "%choice%"=="0" goto end

echo.
echo 无效选择！
pause
goto menu

:open_deploy
echo.
echo 正在打开最终部署包目录...
explorer "%~dp0最终一键复制部署包"
echo.
echo 提示：将「最终一键复制部署包」整个文件夹复制到U盘或目标电脑
echo.
pause
goto end

:open_simple
echo.
echo 正在打开核心文件目录...
explorer "%~dp0零依赖客户端部署包"
echo.
echo 提示：将「零依赖客户端部署包」复制到目标电脑即可
echo.
pause
goto end

:open_readme
echo.
echo 正在打开说明文档...
notepad "%~dp0超级简单使用说明.txt"
pause
goto end

:tool
echo.
echo 正在启动一键部署工具...
call "%~dp0最终一键复制部署包\一键部署工具.bat"
goto end

:end
echo.
echo ===============================================================================
echo.
echo  部署顺利！
echo.
echo ===============================================================================
echo.
timeout /t 3 >nul
