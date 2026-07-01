@echo off
chcp 65001 >nul
echo ========================================
echo  系统一键启动
echo ========================================

echo 启动所有服务...
python "%~dp0..\server_launcher.py"
if %errorlevel% neq 0 (
    echo 启动失败，请检查Python环境
    pause
    exit /b 1
)

echo.
echo 启动完成！按任意键查看运行状态...
pause >nul
echo.
echo 提示: 服务器管理器已启动
pause
