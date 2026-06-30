@echo off
cd /d "d:\yuan\不锈钢网带跟单3.0"
echo.
echo ============================================================
echo 检查 workers 表状态
echo ============================================================
echo.
"C:\Users\lenovo\AppData\Local\Programs\Python\Python314\python.exe" scripts\check_workers_table.py
echo.
pause
