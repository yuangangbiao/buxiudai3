@echo off
chcp 65001 >nul
echo ========================================
echo  Stopping All Services
echo ========================================
cd /d "%~dp0"

python -c "
import psutil, socket
ports = {5000: 'MobileReportAPI', 5002: 'ContainerCenter', 5003: 'WeChatServer', 5006: 'CloudService'}
for conn in psutil.net_connections():
    if conn.status == 'LISTEN' and conn.laddr.port in ports:
        try:
            proc = psutil.Process(conn.pid)
            proc.terminate()
            print('Stopped ' + ports[conn.laddr.port] + ' (PID ' + str(conn.pid) + ')')
        except:
            pass
" 2>nul

echo All services stopped
pause
