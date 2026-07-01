@echo off
chcp 65001 > nul
cd /d "%~dp0"
set REDIS_HOST=localhost
set REDIS_PORT=6379
set SOCKET_CONNECT_TIMEOUT=3
echo Starting WeChat Server on port 5003...
start "WeChatServer" /B py -3 wechat_server.py --host 0.0.0.0 --port 5003 > server_console.log 2>&1
echo Server process started. Waiting 20 seconds for startup...
ping -n 21 127.0.0.1 > nul
echo === Port 5003 ==="" ""
netstat -ano | findstr ":5003 "
echo === Server Console Log (last 20 lines) ===
powershell -Command "Get-Content server_console.log -Tail 20 -Encoding UTF8"
