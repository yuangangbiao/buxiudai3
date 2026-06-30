@echo off
chcp 65001 >nul
title 库存管理客户端 - 零依赖一键部署

echo ============================================================
echo   库存管理客户端 - 零依赖部署包
echo ============================================================
echo.
echo [状态] 正在准备部署包...
echo.

set DEPLOY_DIR=%~dp0零依赖客户端部署包
echo [1/5] 创建部署目录: %DEPLOY_DIR%
if exist "%DEPLOY_DIR%" rmdir /s /q "%DEPLOY_DIR%"
mkdir "%DEPLOY_DIR%"

echo.
echo [2/5] 复制主程序文件...

REM 先检查是否有EXE文件
if exist "%~dp0client_build\dist\库存管理客户端.exe" (
    echo [OK] 找到EXE文件，正在复制...
    copy "%~dp0client_build\dist\库存管理客户端.exe" "%DEPLOY_DIR%\" >nul
) else (
    echo [WARN] 未找到EXE文件，将复制Python源码版...
    copy "%~dp0inventory_client.py" "%DEPLOY_DIR%\" >nul
    
    echo @echo off > "%DEPLOY_DIR%\启动客户端.bat"
    echo chcp 65001 ^>^>nul >> "%DEPLOY_DIR%\启动客户端.bat"
    echo title 库存管理客户端 >> "%DEPLOY_DIR%\启动客户端.bat"
    echo python inventory_client.py >> "%DEPLOY_DIR%\启动客户端.bat"
    echo pause >> "%DEPLOY_DIR%\启动客户端.bat"
    
    echo @echo off > "%DEPLOY_DIR%\安装依赖.bat"
    echo chcp 65001 ^>^>nul >> "%DEPLOY_DIR%\安装依赖.bat"
    echo pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple >> "%DEPLOY_DIR%\安装依赖.bat"
    echo echo. >> "%DEPLOY_DIR%\安装依赖.bat"
    echo echo 依赖安装完成！ >> "%DEPLOY_DIR%\安装依赖.bat"
    echo pause >> "%DEPLOY_DIR%\安装依赖.bat"
)

echo.
echo [3/5] 复制预配置文件...
if exist "%~dp0inventory_client_config.json" (
    copy "%~dp0inventory_client_config.json" "%DEPLOY_DIR%\" >nul
    echo [OK] 预配置文件已复制
)

echo.
echo [4/5] 创建配置和说明文件...

REM 创建使用说明
(
echo # 库存管理客户端 - 使用说明
echo.
echo ## 快速开始
echo.
echo ### 方案一：EXE版（推荐，零依赖）
echo 1. 直接双击「库存管理客户端.exe」
echo 2. 如果有预配置，会自动加载
echo.
echo ### 方案二：Python版
echo 1. 确保电脑已安装 Python 3.8+
echo 2. 双击「安装依赖.bat」
echo 3. 双击「启动客户端.bat」
echo.
echo ## 配置服务器连接
echo.
echo ### 获取服务器IP地址
echo 在服务器电脑上：
echo 1. 按 Win+R，输入 cmd
echo 2. 输入 ipconfig，找到 IPv4 地址
echo.
echo ### 在客户端配置
echo 1. 启动客户端，点击「设置」
echo 2. 服务器地址：http://服务器IP:8080
echo    例如：http://192.168.1.100:8080
echo 3. API密钥：steel_belt_inventory_key_2024
echo 4. 点击「保存」
echo 5. 点击「刷新」测试连接
echo.
echo ## 常见问题
echo.
echo Q: 无法连接服务器？
echo A: 检查：
echo    - 服务器是否已启动
echo    - IP地址是否正确
echo    - API密钥是否一致
echo    - 防火墙是否允许连接
echo.
echo Q: 如何更新？
echo A: 替换最新的程序文件即可
) > "%DEPLOY_DIR%\使用说明.txt"

REM 创建快速配置指南
(
echo # 快速配置 - 3步搞定
echo.
echo 1️⃣ 获取服务器IP
echo 在服务器电脑上按 Win+R，输入 cmd
echo 输入 ipconfig，找到 IPv4 地址
echo.
echo 2️⃣ 启动客户端
echo 双击 库存管理客户端.exe
echo.
echo 3️⃣ 配置连接
echo 点击「设置」
echo 服务器地址：http://服务器IP:8080
echo API密钥：steel_belt_inventory_key_2024
echo 保存 → 刷新
echo.
echo 完成！
) > "%DEPLOY_DIR%\快速配置.txt"

REM 创建预配置文件说明
(
echo # 预配置说明
echo.
echo 如果您已经在服务器上配置好了客户端，
echo 配置会保存在 inventory_client_config.json 中。
echo.
echo 将此文件一起复制到目标电脑，
echo 客户端启动时会自动加载配置，无需重新设置！
) > "%DEPLOY_DIR%\预配置说明.txt"

echo.
echo [5/5] 创建一键打开工具...

REM 创建打开目录的脚本
(
echo @echo off
echo chcp 65001 ^>^>nul
echo explorer "%%~dp0"
echo pause
) > "%DEPLOY_DIR%\打开本目录.bat"

REM 创建系统信息检查工具
(
echo @echo off
echo chcp 65001 ^>^>nul
echo ============================================================
echo   系统信息检查
echo ============================================================
echo.
echo [检查 Python]
python --version >nul 2^>^&1
if errorlevel 1 (
    echo [x] Python 未安装
) else (
    echo [OK] Python 已安装
    python --version
)
echo.
echo [检查网络]
echo 尝试连接服务器...
echo 注意：请先修改配置文件中的服务器地址
echo.
echo ============================================================
echo 检查完成
echo ============================================================
echo.
pause
) > "%DEPLOY_DIR%\系统检查.bat"

echo.
echo ============================================================
echo   [OK] 部署包创建完成！
echo ============================================================
echo.
echo 部署包位置：%DEPLOY_DIR%
echo.
echo 包含文件：
dir /b "%DEPLOY_DIR%"
echo.
echo ============================================================
echo   使用说明
echo ============================================================
echo.
echo 1. 将整个「零依赖客户端部署包」文件夹复制到U盘
echo 2. 将文件夹复制到目标电脑任意位置
echo 3. 双击「库存管理客户端.exe」启动（或用Python版）
echo.
echo [预配置提示] 如果您已配置好服务器，
echo 将配置文件一起复制，客户端会自动加载！
echo.
echo ============================================================
echo.

REM 询问是否打开目录
set /p open="是否打开部署包目录？(Y/N): "
if /i "%open%"=="Y" explorer "%DEPLOY_DIR%"

echo.
pause
