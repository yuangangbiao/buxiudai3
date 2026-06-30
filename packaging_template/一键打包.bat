@echo off
chcp 65001 >nul
REM ============================================================
REM gbd3.0 项目 PyInstaller 一键打包脚本
REM 位置: D:\yuan\gbd3.0\packaging_template\一键打包.bat
REM 依据: D:\yuan\.trae\skills\pyinstaller-packaging\SKILL.md
REM ============================================================

setlocal
cd /d "%~dp0\.."

echo ============================================================
echo  gbd3.0 不锈钢网带跟单 3.0 - 一键打包
echo ============================================================
echo.

REM 沙箱根锚定
set PROJECT_ROOT=D:\yuan\gbd3.0
set PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo [ERROR] 找不到 Python 解释器: %PYTHON_EXE%
    echo 请确认 venv 存在,或修改本脚本的 PYTHON_EXE 变量
    pause
    exit /b 1
)

echo [1/2] 执行打包脚本...
"%PYTHON_EXE%" "%~dp0scripts\build.py" %*
if errorlevel 1 (
    echo.
    echo [ERROR] 打包失败!查看日志: %PROJECT_ROOT%\logs\packaging_*.log
    pause
    exit /b 1
)

echo.
echo [2/2] 检查输出...
if exist "%PROJECT_ROOT%\dist\*.exe" (
    for %%f in (%PROJECT_ROOT%\dist\*.exe) do (
        echo   生成: %%~nxf (大小: %%~zf bytes)
    )
    echo.
    echo 打包完成!exe 在: %PROJECT_ROOT%\dist\
) else (
    echo [WARN] 未找到生成的 exe
)

echo.
pause
endlocal
