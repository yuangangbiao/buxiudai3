@echo off
chcp 65001 >nul
title 库存管理系统 - 客户端部署工具
cls

:MENU
echo ========================================
echo   库存管理系统 - 客户端部署工具
echo ========================================
echo.
echo 请选择部署方案:
echo.
echo   [1] EXE打包（推荐，即点即用）
echo   [2] 便携版部署（灵活，可更新）
echo   [3] 直接部署包（目标机有Python）
echo   [4] 查看打包说明文档
echo   [0] 退出
echo.
echo ========================================
set /p choice=请输入选项 [0-4]:

if "%choice%"=="1" goto EXE_PACK
if "%choice%"=="2" goto PORTABLE
if "%choice%"=="3" goto DIRECT
if "%choice%"=="4" goto DOCS
if "%choice%"=="0" goto END
echo.
echo 无效选项，请重新选择！
echo.
pause
goto MENU

:EXE_PACK
cls
echo ========================================
echo   EXE打包方案
echo ========================================
echo.
echo 正在启动EXE打包工具...
echo.
call "打包客户端.bat"
echo.
pause
goto MENU

:PORTABLE
cls
echo ========================================
echo   便携版部署方案
echo ========================================
echo.
echo 正在创建便携版部署包...
echo.
call "创建便携版客户端.bat"
echo.
pause
goto MENU

:DIRECT
cls
echo ========================================
echo   直接部署方案
echo ========================================
echo.
echo 正在创建直接部署包...
echo.
call "创建客户端部署包.bat"
echo.
pause
goto MENU

:DOCS
cls
echo ========================================
echo   打包说明文档
echo ========================================
echo.
echo 正在打开文档...
echo.
if exist "客户端打包说明.md" (
    start "" "客户端打包说明.md"
) else if exist "部署说明.md" (
    start "" "部署说明.md"
) else (
    echo 未找到文档文件
)
echo.
pause
goto MENU

:END
cls
echo ========================================
echo   感谢使用！
echo ========================================
echo.
timeout /t 2 >nul
exit
