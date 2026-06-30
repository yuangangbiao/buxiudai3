@echo off
chcp 65001 >nul
title 库存系统连接测试

echo ============================================================
echo   库存系统连接测试
echo ============================================================
echo.

echo 测试服务器连接...
python -c "import requests; r=requests.get('http://192.168.1.32:8080/api/health', timeout=5); print('服务器状态:', r.json().get('status'))"

echo.
echo 按任意键退出...
pause >nul
