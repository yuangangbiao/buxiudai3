@echo off
chcp 65001 >nul
echo ========================================
echo 库存管理客户端 - 一键打包
echo ========================================
echo.

cd /d "%~dp0"

echo [1/5] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo Python环境检查通过

echo.
echo [2/5] 检查并安装PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 正在安装PyInstaller...
    pip install pyinstaller
)
echo PyInstaller就绪

echo.
echo [3/5] 创建打包目录...
if not exist "client_package" mkdir client_package
if not exist "client_package\output" mkdir client_package\output

echo.
echo [4/5] 生成打包配置...
python build_client.py

echo.
echo [5/5] 开始打包...
cd client_package
pyinstaller --clean inventory_client.spec

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
echo 可执行文件位置:
echo client_package\dist\库存管理客户端.exe
echo.
echo 请将以下文件一起打包分发:
echo - 库存管理客户端.exe
echo - inventory_client_config.json (可选，预配置文件)
echo.
pause
