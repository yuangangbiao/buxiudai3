@echo off
REM ============================================
REM 企业微信应用机器人 - 服务器一键部署脚本
REM 请在服务器上以管理员身份运行此脚本
REM ============================================

echo ============================================
echo 企业微信应用机器人 - 自动部署脚本
echo ============================================
echo.

REM 检查Python是否安装
echo [1/5] 检查Python安装...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo ✓ Python已安装
echo.

REM 创建目录
echo [2/5] 创建部署目录...
set "DEPLOY_DIR=%~dp0"
echo ✓ 部署目录：%DEPLOY_DIR%
echo.

REM 检查部署文件是否存在
echo [3/5] 检查部署文件...
if not exist "%DEPLOY_DIR%wechat_server.py" (
    echo [错误] 未找到部署文件（wechat_server.py）
    echo 请确保此脚本位于部署文件同目录下
    pause
    exit /b 1
)

if not exist "%DEPLOY_DIR%云端一键启动.bat" (
    echo [警告] 未找到 云端一键启动.bat
) else (
    echo ✓ 云端一键启动.bat 已就绪
)
echo ✓ 部署文件已就绪
echo.

REM 安装Python依赖
echo [4/5] 安装Python依赖（可能需要几分钟）...
cd /d "%DEPLOY_DIR%\.."
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [警告] 使用国内镜像源安装失败，尝试默认源...
    python -m pip install -r requirements.txt
)
echo ✓ 依赖安装完成
echo.

REM 验证校验文件
echo ============================================
echo 验证部署...
echo ============================================
if exist "%DEPLOY_DIR%WW_verify_PWFveCpOUtSmyNnB.txt" (
    echo ✓ 校验文件存在
    type "%DEPLOY_DIR%WW_verify_PWFveCpOUtSmyNnB.txt"
) else (
    echo [警告] 校验文件不存在，正在创建...
    echo PWFveCpOUtSmyNnB > "%DEPLOY_DIR%WW_verify_PWFveCpOUtSmyNnB.txt"
    echo ✓ 校验文件已创建
)
echo.

REM 开放防火墙端口
echo 配置防火墙...
netsh advfirewall firewall show rule name="WeChatBot" >nul 2>&1
if errorlevel 1 (
    netsh advfirewall firewall add rule name="WeChatBot" dir=in action=allow protocol=TCP localport=5003
    echo ✓ 防火墙规则已添加（端口5003）
) else (
    echo ✓ 防火墙规则已存在
)
echo.

REM 启动服务
echo ============================================
echo 部署完成！
echo ============================================
echo.
echo 是否现在启动服务？（Y/N）
set /p choice="请选择："
if /i "%choice%"=="Y" (
    echo.
    echo 启动服务...
    cd /d "%DEPLOY_DIR%"
    echo 推荐方式：双击 云端一键启动.bat 启动所有服务
    echo.
    start "WeChatBot" python wechat_server.py --port 5003
    echo ✓ 服务已启动（新窗口中运行）
    echo.
    echo 请在本地浏览器访问以下地址进行测试：
    echo http://124.223.57.82:5003/health
    echo.
)

echo ============================================
echo 后续步骤：
echo 1. 确认服务启动成功
echo 2. 在本地浏览器测试：http://124.223.57.82:5003/health
echo 3. 配置企业微信后台（见部署指南）
echo 4. （可选）配置开机自启（见部署指南）
echo ============================================
echo.
pause
