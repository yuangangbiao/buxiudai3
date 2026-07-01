# 企业微信应用机器人 - 一键打包脚本
# 运行此脚本将生成可执行文件和配置文件夹

@echo off
chcp 65001 >nul
echo ========================================
echo 企业微信应用机器人 - 打包工具
echo ========================================
echo.

echo 正在安装依赖...
pip install pyinstaller flask requests python-dotenv cryptography -q

echo.
echo 正在清理旧文件...
cd /d "%~dp0"
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "WeChatBotServer.spec" del /q WeChatBotServer.spec

echo.
echo 正在打包...
echo.

pyinstaller --onefile --console ^
    --add-data "bots;bots" ^
    --add-data "commands;commands" ^
    --add-data "services;services" ^
    --add-data "modules;modules" ^
    --add-data "storage_layer.py;." ^
    --add-data "container_center_v5.py;." ^
    --add-data "operation_log.py;." ^
    --add-data "enhanced_modules.py;." ^
    --add-data "clock_sync.py;." ^
    --add-data "data_integrity.py;." ^
    --add-data "fault_tolerance.py;." ^
    --add-data "data_boundary.py;." ^
    --add-data "WW_verify_PWFveCpOUtSmyNnB.txt;." ^
    --hidden-import=flask ^
    --hidden-import=requests ^
    --hidden-import=dotenv ^
    --hidden-import=cryptography ^
    --hidden-import=redis ^
    --hidden-import=elasticsearch ^
    --hidden-import=psutil ^
    --hidden-import=ntplib ^
    --hidden-import=msgpack ^
    --hidden-import=prometheus_client ^
    --hidden-import=modules.api_signature ^
    --hidden-import=modules.circuit_breaker ^
    --hidden-import=modules.queue_manager ^
    --hidden-import=modules.health_checker ^
    --hidden-import=modules.deployment_manager ^
    --hidden-import=modules.enhanced_audit_logger ^
    --hidden-import=modules.enhanced_backup ^
    --hidden-import=enhanced_modules ^
    --hidden-import=clock_sync ^
    --hidden-import=data_integrity ^
    --hidden-import=fault_tolerance ^
    --hidden-import=data_boundary ^
    --name WeChatBotServer ^
    wechat_server.py

echo.
echo 正在创建DAT配置文件夹...
if not exist "dist\DAT" mkdir "dist\DAT"

echo .env> "dist\DAT\.env.example"
echo WECHAT_TOKEN=your_token_here >> "dist\DAT\.env.example"
echo WECHAT_AES_KEY=your_aes_key_here >> "dist\DAT\.env.example"
echo WECHAT_APP_ID=your_app_id >> "dist\DAT\.env.example"
echo WECHAT_APP_SECRET=your_app_secret >> "dist\DAT\.env.example"
echo MAIN_SOFTWARE_CALLBACK_URL=http://localhost:5002/api/callback >> "dist\DAT\.env.example"

echo ^<#^> 企业微信配置 ^<#/^> >> "dist\DAT\.env.example"
echo WECHAT_TOKEN=feS7fW82vs3897popy5MV >> "dist\DAT\.env.example"
echo WECHAT_AES_KEY=kaGqG5owrdcbYMAoz6JwS9soixobrTYW9qx0PJHS2H >> "dist\DAT\.env.example"
echo WECHAT_APP_ID=ww2a8dcc32f0c57889 >> "dist\DAT\.env.example"
echo WECHAT_APP_SECRET= >> "dist\DAT\.env.example"
echo. >> "dist\DAT\.env.example"
echo ^<#^> 回调地址 ^<#/^> >> "dist\DAT\.env.example"
echo MAIN_SOFTWARE_CALLBACK_URL=http://127.0.0.1:5002/api/callback >> "dist\DAT\.env.example"

if exist ".env" (
    copy ".env" "dist\DAT\.env"
    echo 已复制现有的 .env 文件到 DAT 文件夹
) else (
    echo 已创建 .env.example，请复制并重命名为 .env
)

echo.
echo ========================================
echo 打包完成！
echo.
echo 生成的文件：
echo   - dist\WeChatBotServer.exe  ^< 主程序
echo   - dist\DAT\.env              ^< 配置文件（需要填写）
echo.
echo 部署步骤：
echo   1. 将 WeChatBotServer.exe 复制到服务器
echo   2. 将 DAT 文件夹一并复制到服务器
echo   3. 编辑 DAT\.env 填写正确的配置
echo   4. 运行 WeChatBotServer.exe
echo.
echo 注意事项：
echo   - DAT 文件夹需要与 exe 在同一目录
echo   - 数据库文件将创建在 exe 同目录下
echo ========================================
echo.
pause
