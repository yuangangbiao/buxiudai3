@echo off
chcp 65001 >nul
echo ========================================
echo 库存管理客户端 - 便携版创建工具
echo ========================================
echo.

set PORTABLE_DIR=%~dp0client_portable
echo 正在创建便携版目录: %PORTABLE_DIR%
if not exist "%PORTABLE_DIR%" mkdir "%PORTABLE_DIR%"

echo.
echo [1/6] 复制客户端程序...
copy "%~dp0inventory_client.py" "%PORTABLE_DIR%\" >nul
echo   inventory_client.py

echo.
echo [2/6] 创建启动脚本...
(
echo @echo off
echo chcp 65001 ^>nul
echo title 库存管理客户端 v3.0
echo echo ========================================
echo echo 库存管理系统 - 客户端
echo echo ========================================
echo echo.
echo cd /d "%%~dp0"
echo.
echo if not exist "python_portable" goto NO_PORTABLE
echo.
echo :START_WITH_PORTABLE
echo echo 使用便携版Python启动...
echo python_portable\python.exe inventory_client.py
echo goto END
echo.
echo :NO_PORTABLE
echo echo 未检测到便携版Python
echo echo 尝试使用系统Python...
echo python inventory_client.py
echo if errorlevel 1 (
echo     echo.
echo     echo 错误：未找到Python！
echo     echo.
echo     echo 请选择以下方案之一：
echo     echo 1. 安装Python 3.8+，运行 安装依赖.bat
echo     echo 2. 将便携版Python放在 python_portable 文件夹
echo     echo.
echo     pause
echo ^)
echo goto END
echo.
echo :END
echo pause
) > "%PORTABLE_DIR%\启动客户端.bat"
echo   启动客户端.bat

echo.
echo [3/6] 创建依赖安装脚本...
(
echo @echo off
echo chcp 65001 ^>nul
echo ========================================
echo 库存管理客户端 - 依赖安装
echo ========================================
echo.
echo 正在安装依赖库...
echo.
echo if exist "python_portable" (
echo     echo 使用便携版Python安装...
echo     python_portable\python.exe -m pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ^) else (
echo     echo 使用系统Python安装...
echo     pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ^)
echo.
echo ========================================
echo 依赖安装完成！
echo ========================================
echo.
echo 现在可以运行 启动客户端.bat 了
echo.
pause
) > "%PORTABLE_DIR%\安装依赖.bat"
echo   安装依赖.bat

echo.
echo [4/6] 创建配置说明...
(
echo # 库存管理客户端 - 配置说明
echo.
echo ## 快速开始
echo.
echo ### 方案一：使用便携版Python（推荐）
echo.
echo 1. 下载便携版Python（WinPython或嵌入式Python）
echo 2. 解压到 python_portable 文件夹
echo 3. 运行 安装依赖.bat
echo 4. 运行 启动客户端.bat
echo.
echo ### 方案二：使用系统Python
echo.
echo 1. 确保已安装Python 3.8+
echo 2. 运行 安装依赖.bat
echo 3. 运行 启动客户端.bat
echo.
echo ### 方案三：使用EXE文件
echo.
echo 如果已打包成EXE，直接运行即可。
echo.
echo ## 服务器配置
echo.
echo 首次运行时，在设置中配置：
echo.
echo - 服务器地址: http://服务器IP:端口
echo   例如: http://192.168.1.100:8080
echo.
echo - API密钥: 与服务器一致的密钥
echo.
echo ## 获取服务器IP
echo.
echo 在服务器电脑上:
echo 1. 按 Win+R，输入 cmd，回车
echo 2. 输入 ipconfig，回车
echo 3. 查找 IPv4 地址（如：192.168.1.100）
echo.
echo ## 导入预配置
echo.
echo 如果有 inventory_client_config.json:
echo 1. 将配置文件放在本目录
echo 2. 启动客户端会自动加载
echo.
echo ## 默认配置
echo.
echo - 服务器地址: http://localhost:8080
echo - API密钥: steel_belt_inventory_key_2024
) > "%PORTABLE_DIR%\配置说明.txt"
echo   配置说明.txt

echo.
echo [5/6] 创建便携版Python说明...
(
echo # 便携版Python使用说明
echo.
echo ## 下载便携版Python
echo.
echo ### 方案一：使用嵌入式Python（推荐，体积小）
echo.
echo 1. 访问: https://www.python.org/downloads/windows/
echo 2. 下载 "Windows embeddable package (64-bit)"
echo    例如: python-3.11.9-embed-amd64.zip
echo.
echo 3. 解压到 python_portable 文件夹
echo.
echo 4. 下载 get-pip.py:
echo    https://bootstrap.pypa.io/get-pip.py
echo.
echo 5. 运行: python_portable\python.exe get-pip.py
echo.
echo 6. 运行: 安装依赖.bat
echo.
echo ### 方案二：使用WinPython（功能全）
echo.
echo 1. 访问: https://winpython.github.io/
echo 2. 下载 WinPython Zero 或基础版
echo 3. 解压到 python_portable 文件夹
echo 4. 确保 python.exe 在 python_portable 根目录
echo.
echo ## 目录结构示例
echo.
echo client_portable/
echo ├── python_portable/
echo │   ├── python.exe
echo │   ├── python311.dll
echo │   └── ...其他文件
echo ├── inventory_client.py
echo ├── 启动客户端.bat
echo ├── 安装依赖.bat
echo └── 配置说明.txt
echo.
echo ## 验证安装
echo.
echo 双击运行 启动客户端.bat
echo 如果启动成功，说明配置正确。
echo.
echo ## 常见问题
echo.
echo Q: 提示找不到 python_portable？
echo A: 确保文件夹名称是 python_portable，
echo    且在 client_portable 目录下。
echo.
echo Q: 运行时提示缺少模块？
echo A: 运行 安装依赖.bat 安装所需库。
) > "%PORTABLE_DIR%\便携版Python说明.txt"
echo   便携版Python说明.txt

echo.
echo [6/6] 创建主README...
(
echo # 库存管理客户端 - 便携版
echo.
echo ## 版本信息
echo.
echo - 版本: 3.0
echo - 日期: 2024
echo - 类型: 便携版/绿色版
echo.
echo ## 快速开始
echo.
echo ### 选择部署方案
echo.
echo 根据目标电脑情况选择：
echo.
echo | 方案 | 适用场景 | 难度 |
echo ^|------^|----------^|------^|
echo ^| 方案一 ^| 已有Python ^| ⭐简单 ^|
echo ^| 方案二 ^| 使用便携Python ^| ⭐⭐中等 ^|
echo ^| 方案三 ^| 使用EXE文件 ^| ⭐最简单 ^|
echo.
echo ---
echo.
echo ## 方案一：目标电脑已安装Python
echo.
echo 1. 直接复制本文件夹到目标电脑
echo 2. 双击 安装依赖.bat
echo 3. 双击 启动客户端.bat
echo 4. 在设置中配置服务器地址和API密钥
echo.
echo ## 方案二：使用便携版Python（推荐）
echo.
echo 适合目标电脑没有安装Python的情况。
echo.
echo 1. 准备便携版Python（详细见：便携版Python说明.txt）
echo 2. 将便携版Python放在 python_portable 文件夹
echo 3. 运行 安装依赖.bat
echo 4. 运行 启动客户端.bat
echo.
echo ## 方案三：使用EXE文件
echo.
echo 如果已使用PyInstaller打包成EXE：
echo.
echo 1. 只需要复制 EXE文件
echo 2. 如果有预配置，一起复制 inventory_client_config.json
echo 3. 双击EXE运行即可
echo.
echo ## 配置服务器连接
echo.
echo ### 获取服务器IP
echo.
echo 在服务器电脑上:
echo 1. 按 Win+R，输入 cmd
echo 2. 输入 ipconfig
echo 3. 查找 IPv4 地址（如 192.168.1.100）
echo.
echo ### 在客户端配置
echo.
echo 1. 启动客户端
echo 2. 点击"设置"按钮
echo 3. 配置服务器地址：http://服务器IP:8080
echo 4. 配置API密钥（与服务器一致）
echo 5. 点击保存
echo 6. 点击"刷新"测试连接
echo.
echo ### 预配置（可选）
echo.
echo 如果有配置文件 inventory_client_config.json:
echo.
echo 1. 将配置文件放在同一目录
echo 2. 启动客户端会自动加载
echo 3. 无需手动配置
echo.
echo ## 文件夹内容说明
echo.
echo ```
echo client_portable/
echo ├── inventory_client.py          ^# 主程序
echo ├── 启动客户端.bat               ^# 启动脚本
echo ├── 安装依赖.bat                 ^# 依赖安装
echo ├── 配置说明.txt                 ^# 配置指南
echo ├── 便携版Python说明.txt          ^# 便携Python指南
echo ├── README.txt                    ^# 本文件
echo ├── python_portable/             ^# 便携版Python（可选）
echo │   └── python.exe
echo └── inventory_client_config.json ^# 预配置文件（可选）
echo ```
echo.
echo ## 常见问题
echo.
echo ### Q1: 提示"未找到Python"
echo.
echo A: 有三种解决方法：
echo    1. 在目标电脑上安装Python 3.8+
echo    2. 使用便携版Python（见方案二）
echo    3. 使用打包好的EXE文件
echo.
echo ### Q2: 无法连接服务器
echo.
echo A: 请检查：
echo    1. 服务器是否已启动
echo    2. 服务器IP地址是否正确
echo    3. API密钥是否一致
echo    4. 防火墙是否开放对应端口
echo    5. 两台电脑是否在同一局域网
echo.
echo ### Q3: 如何预配置客户端
echo.
echo A: 方法：
echo    1. 在服务器上用配置器配置好
echo    2. 导出客户端配置文件
echo    3. 将配置文件一起复制到部署包
echo    4. 客户端启动会自动加载
echo.
echo ### Q4: 如何获取EXE文件
echo.
echo A: 在服务器电脑上：
echo    1. 运行 打包客户端.bat
echo    2. 等待打包完成
echo    3. 从 client_package/dist/ 获取EXE
echo.
echo ## 安全提示
echo.
echo - 妥善保管API密钥
echo - 仅在可信网络内使用
echo - 定期检查服务器日志
echo.
echo ## 技术支持
echo.
echo 详见主程序目录下的 部署说明.md
echo.
echo ## 更新日志
echo.
echo ### v3.0
echo - 支持服务器-客户端架构
echo - 支持便携版部署
echo - 支持预配置文件
) > "%PORTABLE_DIR%\README.txt"
echo   README.txt

echo.
echo ========================================
echo 便携版部署包创建完成！
echo ========================================
echo.
echo 部署包位置: %PORTABLE_DIR%
echo.
echo 包含的文件:
echo   inventory_client.py
echo   启动客户端.bat
echo   安装依赖.bat
echo   配置说明.txt
echo   便携版Python说明.txt
echo   README.txt
echo.
echo 使用方式:
echo.
echo 1. 将整个 client_portable 文件夹复制到U盘
echo.
echo 2. 可选：添加便携版Python到 python_portable 文件夹
echo.
echo 3. 可选：添加预配置文件 inventory_client_config.json
echo.
echo 4. 复制到目标电脑使用！
echo.
echo 详细说明请查看:
echo   %PORTABLE_DIR%\README.txt
echo.
pause
