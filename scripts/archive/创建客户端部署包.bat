@echo off
chcp 65001 >nul
echo ========================================
echo 库存管理客户端 - 简化部署包
echo ========================================
echo.

set CLIENT_DIR=%~dp0client_deploy
echo 正在创建部署目录: %CLIENT_DIR%
if not exist "%CLIENT_DIR%" mkdir "%CLIENT_DIR%"

echo.
echo [1/5] 复制客户端程序...
copy "%~dp0inventory_client.py" "%CLIENT_DIR%\" >nul
echo   inventory_client.py

echo.
echo [2/5] 复制启动脚本...
(
echo @echo off
echo chcp 65001 ^>nul
echo title 库存管理客户端
echo echo ========================================
echo echo 库存管理系统 - 客户端
echo echo ========================================
echo echo.
echo cd /d "%%~dp0"
echo echo 正在启动...
echo echo.
echo python inventory_client.py
echo pause
) > "%CLIENT_DIR%\启动客户端.bat"
echo   启动客户端.bat

echo.
echo [3/5] 创建配置说明...
(
echo # 库存管理客户端配置说明
echo.
echo ## 快速开始
echo.
echo 1. 确保已安装Python 3.8+
echo 2. 运行 安装依赖.bat 安装所需库
echo 3. 运行 启动客户端.bat 启动程序
echo.
echo ## 服务器连接配置
echo.
echo 首次运行时，在设置中配置:
echo - 服务器地址: http://服务器IP:端口
echo - API密钥: 与服务器一致的密钥
echo.
echo ## 默认配置
echo.
echo - 服务器地址: http://localhost:8080
echo - API密钥: steel_belt_inventory_key_2024
echo.
echo ## 从配置器导入配置
echo.
echo 如果有 inventory_client_config.json:
echo 1. 将配置文件放在同一目录
echo 2. 直接启动客户端即可
) > "%CLIENT_DIR%\配置说明.txt"
echo   配置说明.txt

echo.
echo [4/5] 创建依赖安装脚本...
(
echo @echo off
echo chcp 65001 ^>nul
echo ========================================
echo 库存管理客户端 - 依赖安装
echo ========================================
echo.
echo 正在安装依赖库...
echo.
echo pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
echo pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.
echo ========================================
echo 依赖安装完成！
echo ========================================
echo.
echo 现在可以运行 启动客户端.bat 了
echo.
pause
) > "%CLIENT_DIR%\安装依赖.bat"
echo   安装依赖.bat

echo.
echo [5/5] 创建README...
(
echo # 库存管理客户端 - 简化部署包
echo.
echo ## 使用说明
echo.
echo ### 方法一：直接运行Python脚本（推荐）
echo.
echo 1. 确保电脑已安装Python 3.8或更高版本
echo 2. 双击运行 `安装依赖.bat`
echo 3. 双击运行 `启动客户端.bat`
echo.
echo ### 方法二：使用已打包的EXE文件
echo.
echo 如果有 `库存管理客户端.exe`，直接双击运行即可。
echo.
echo ## 配置服务器连接
echo.
echo 首次启动后，点击"设置"按钮配置：
echo - 服务器地址：填写服务器的局域网IP地址（如：http://192.168.1.100:8080）
echo - API密钥：与服务器配置的一致
echo.
echo ## 从配置器导入配置
echo.
echo 如果有配置文件：
echo 1. 将 inventory_client_config.json 放在本目录
echo 2. 直接启动客户端即可自动加载配置
echo.
echo ## 常见问题
echo.
echo Q: 提示找不到Python？
echo A: 请先安装Python 3.8+，安装时勾选"Add Python to PATH"
echo.
echo Q: 无法连接服务器？
echo A: 1. 确认服务器已启动
echo    2. 检查服务器IP地址是否正确
echo    3. 确认API密钥一致
echo    4. 检查防火墙设置
echo.
echo ## 技术支持
echo.
echo 详见主目录下的 `部署说明.md`
) > "%CLIENT_DIR%\README.txt"
echo   README.txt

echo.
echo ========================================
echo 客户端部署包创建完成！
echo ========================================
echo.
echo 部署包位置: %CLIENT_DIR%
echo.
echo 包含的文件:
echo   inventory_client.py      ^(主程序^)
echo   启动客户端.bat          ^(启动脚本^)
echo   安装依赖.bat            ^(依赖安装^)
echo   配置说明.txt            ^(配置指南^)
echo   README.txt             ^(使用说明^)
echo.
echo 现在可以将整个 client_deploy 文件夹
echo 复制到其他电脑上部署使用！
echo.
echo 提示：如果已配置好服务器，
echo 可以先在服务器上用配置器导出配置，
echo 一起复制到部署包中。
echo.
pause
