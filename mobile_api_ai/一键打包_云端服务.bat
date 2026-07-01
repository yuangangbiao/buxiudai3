@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  微信云端服务 - 一键打包为独立EXE
echo ============================================
echo.
echo 将把 wechat_cloud.py 打包为无依赖EXE
echo 生成的EXE可在没有Python的服务器上运行
echo.
echo 正在执行打包，请等待约2-5分钟...
echo.
python build_cloud_exe.py
echo.
if exist "dist\wechat_cloud_server.exe" (
    echo ============================================
    echo  打包成功!
    echo  输出: dist\wechat_cloud_server.exe
    echo ============================================
) else (
    echo ============================================
    echo  打包失败，请检查上方错误信息
    echo ============================================
)
echo.
pause
