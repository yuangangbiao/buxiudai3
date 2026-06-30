@echo off
chcp 65001 >nul
echo ==========================================
echo   MySQL 局域网连接配置
echo ==========================================
echo.
echo 正在停止MySQL服务...
net stop MySQL

echo.
echo 正在启动MySQL服务...
net start MySQL

echo.
echo 配置完成！MySQL现在应该绑定到0.0.0.0
echo 请检查网络连接: netstat -an | findstr 3306
echo.
pause
