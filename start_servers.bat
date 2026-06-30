@echo off
chcp 65001 >nul
echo ========================================
echo   跟单系统 — 启动前校验 + 启动服务
echo ========================================

echo.
echo [1/4] 数据库校验...
cd /d "%~dp0mobile_api_ai"
python scripts\preflight_check.py
if %errorlevel% neq 0 (
    echo.
    echo [错误] 数据库校验失败，启动中止！
    pause
    exit /b 1
)
cd /d "%~dp0"

echo.
echo [2/4] 杀掉旧端口进程...
for %%p in (5002 5003 5008 5009 8008) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p " ^| findstr LISTENING') do (
        echo   端口 %%p → PID %%a
        taskkill /F /PID %%a >nul 2>&1
    )
)
timeout /t 2 /nobreak >nul

echo.
echo [3/4] 清理 Python 缓存...
for /d /r "%~dp0" %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q "%~dp0*.pyc" >nul 2>&1
echo   完成！

echo.
echo [4/4] 启动服务...
cd /d "%~dp0mobile_api_ai"
start "调度中心-5003" python dispatch_center.py
start "容器中心-5002" python container_center_api.py
start "报工系统-5008" python app.py
start "人脸考勤-5009" python face_server.py
start "同步桥-8008"   python sync_bridge_server.py

echo.
echo ========================================
echo   全部服务已启动！
echo   调度中心: http://127.0.0.1:5003
echo   容器中心: http://127.0.0.1:5002
echo   报工系统: http://127.0.0.1:5008
echo   人脸考勤: http://127.0.0.1:5009
echo   同步桥:   http://127.0.0.1:8008
echo ========================================
pause
