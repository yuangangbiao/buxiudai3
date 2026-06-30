@echo off
chcp 65001 >nul
echo ========================================
echo 晨圣报工系统 - 统一启动脚本
echo ========================================
echo.

REM 存储类型: MySQL (container_center), 通过 .env 配置
set MYSQL_PASSWORD=88888888

REM 设置 API 密钥（容器中心需要）
set WECHAT_CLOUD_API_KEY=WkQ9-8X7Z-3K2M-5P6L

echo [配置]
echo 存储类型: MySQL (container_center)
echo.

REM 启动报工程序（端口 5008）
echo [1/2] 启动报工程序 (端口 5008)...
start "报工程序" cmd /k "cd /d d:\yuan\不锈钢网带跟单3.0 && python mobile_api_ai\app.py"

REM 等待一下再启动容器中心
timeout /t 3 /nobreak >nul

REM 启动容器中心（端口 5002）
echo [2/2] 启动容器中心 (端口 5002)...
start "容器中心" cmd /k "cd /d d:\yuan\不锈钢网带跟单3.0 && python mobile_api_ai\container_center_api.py"

echo.
echo ========================================
echo 启动完成！
echo.
echo 访问地址：
echo   报工页面: http://localhost:5008/cs_report
echo   容器中心: http://localhost:5002
echo   调度中心: http://localhost:5003
echo.
echo 推荐: 使用 python server_launcher.py 统一管理所有服务
echo ========================================
pause
