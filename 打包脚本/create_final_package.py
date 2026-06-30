# -*- coding: utf-8 -*-
"""
终极一键部署包创建器
"""
import os
import sys
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FINAL_DIR = os.path.join(BASE_DIR, "最终一键复制部署包")

print("=" * 70)
print("  库存管理客户端 - 最终一键部署包")
print("=" * 70)
print()

# 1. 清理并创建目录
print("[1/6] 准备目录...")
if os.path.exists(FINAL_DIR):
    shutil.rmtree(FINAL_DIR)
os.makedirs(FINAL_DIR)

# 2. 复制Python源码版部署包
print()
print("[2/6] 复制核心部署包...")
source_deploy = os.path.join(BASE_DIR, "零依赖客户端部署包")
if os.path.exists(source_deploy):
    for item in os.listdir(source_deploy):
        src = os.path.join(source_deploy, item)
        dst = os.path.join(FINAL_DIR, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    print("    [OK] 核心部署包已复制")

# 3. 创建EXE打包指南
print()
print("[3/6] 创建EXE打包指南...")
exe_dir = os.path.join(FINAL_DIR, "EXE打包工具")
os.makedirs(exe_dir, exist_ok=True)

shutil.copy2(os.path.join(BASE_DIR, "full_build_client.py"), os.path.join(exe_dir, "full_build_client.py"))

with open(os.path.join(exe_dir, "一键打包.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 库存管理客户端 - EXE打包工具

echo ============================================================
echo   库存管理客户端 - EXE打包工具
echo ============================================================
echo.
echo 正在检查环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python！
    echo.
    pause
    exit /b 1
)

echo.
echo [1/3] 检查PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 正在安装PyInstaller...
    pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo [2/3] 开始打包...
echo.
echo 注意：打包过程需要2-5分钟，请耐心等待...
echo.
python full_build_client.py

echo.
echo [3/3] 打包完成！
echo.
echo EXE文件位置：client_build\\dist\\库存管理客户端.exe
echo.
echo 现在可以将EXE文件复制到目标电脑了！
echo.
pause
""")

with open(os.path.join(exe_dir, "打包说明.txt"), 'w', encoding='utf-8') as f:
    f.write("""# EXE打包说明

## 什么时候用？
- 目标电脑不想安装Python
- 需要最简单的部署方式

## 如何打包？
1. 在服务器电脑上运行「一键打包.bat」
2. 等待2-5分钟
3. 从 client_build\\dist\\ 目录获取EXE文件
4. 将EXE文件复制到目标电脑

## 部署EXE
1. 只需复制「库存管理客户端.exe」
2. 可选：一起复制 inventory_client_config.json（预配置）
3. 双击EXE即可使用
""")

print("    [OK] EXE打包工具已创建")

# 4. 创建便携版Python准备目录
print()
print("[4/6] 创建便携版Python准备目录...")
portable_dir = os.path.join(FINAL_DIR, "便携版Python准备")
os.makedirs(portable_dir, exist_ok=True)

with open(os.path.join(portable_dir, "下载说明.txt"), 'w', encoding='utf-8') as f:
    f.write("""# 便携版Python准备

## 推荐方案（最小体积）

### 1. 下载嵌入版Python
访问：https://www.python.org/downloads/windows/
下载：Windows embeddable package (64-bit)
（例如：python-3.11.9-embed-amd64.zip）

### 2. 解压
将下载的压缩包解压到这里

### 3. 目录结构
确保结构如下：
便携版Python准备/
  python/
    python.exe
    ...

### 4. 添加pip
下载：https://bootstrap.pypa.io/get-pip.py
放到 python/ 目录
运行：python get-pip.py

### 5. 安装依赖
运行：../安装依赖.bat
（或手动：python -m pip install requests）

### 6. 使用
将整个文件夹复制到目标电脑
运行「启动客户端.bat」

## 备用方案（WinPython）
访问：https://winpython.github.io/
下载：WinPython Zero
使用方法同上
""")

with open(os.path.join(portable_dir, "一键准备.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 便携版Python准备工具
echo ============================================================
echo   便携版Python准备工具
echo ============================================================
echo.
echo 本工具将帮助您准备便携版Python
echo.
echo 步骤：
echo 1. 下载Python
echo 2. 解压到本目录
echo 3. 运行安装pip
echo 4. 安装依赖
echo.
echo ============================================================
echo.
echo 正在打开下载页面...
echo 请下载 Windows embeddable package (64-bit)
echo.
start https://www.python.org/downloads/windows/
echo.
pause
echo.
echo 下载完成后，请按以下步骤：
echo.
echo 1. 将压缩包解压到本目录，重命名为「python」
echo 2. 运行「安装pip.bat」
echo.
pause
""")

print("    [OK] 便携版Python准备已创建")

# 5. 创建最终总览说明
print()
print("[5/6] 创建总览说明...")

with open(os.path.join(FINAL_DIR, "README - 最终部署说明.txt"), 'w', encoding='utf-8') as f:
    f.write("""# 库存管理客户端 - 最终一键部署

## 🌟 三种部署方案，总有一款适合您

### 方案一：Python源码版（最简单，推荐）
直接复制主目录文件到目标电脑
- 需要目标电脑有Python
- 使用：启动客户端.bat

### 方案二：便携版Python（零依赖）
包含完整Python，目标电脑不需要任何配置
- 需要先准备便携版Python
- 查看「便携版Python准备」目录

### 方案三：EXE版（最完美）
打包成单文件EXE，双击即用
- 需要先用「EXE打包工具」打包
- 目标电脑零依赖

---

## 🚀 您只需要做

### 第一步：选择方案
- 如果目标电脑有Python → 用方案一
- 如果目标电脑没有Python → 用方案二或三

### 第二步：复制
1. 将整个「最终一键复制部署包」文件夹复制到U盘
2. 带到目标电脑

### 第三步：使用
根据选择的方案，查看对应目录的说明

---

## 📋 目录说明

最终一键复制部署包/
├── 启动客户端.bat          → 启动主程序
├── 安装依赖.bat             → 安装requests库
├── inventory_client.py      → 主程序
├── inventory_client_config.json → 预配置（如果有）
├── 使用说明.txt            → 详细说明
├── 快速配置.txt            → 3步配置指南
├── Python便携版说明.txt    → 便携版使用说明
├── 打开本目录.bat          → 快速打开
├── EXE打包工具/            → EXE打包工具
└── 便携版Python准备/       → 便携版Python准备

---

## ⚙️ 预配置说明

如果您已在服务器上配置好客户端：
- 配置已保存在 inventory_client_config.json
- 将此文件一起复制，目标电脑会自动加载！
- 无需重新配置！

---

## 📞 快速配置步骤

1️⃣ 获取服务器IP
   在服务器电脑：Win+R → cmd → ipconfig

2️⃣ 启动客户端
   双击「启动客户端.bat」

3️⃣ 配置连接
   服务器地址：http://服务器IP:8080
   API密钥：steel_belt_inventory_key_2024

完成！

---

## 💡 最佳实践

- 先在服务器上测试好
- 配置好后一起复制配置文件
- 选择合适的部署方案

---

版本：1.0
最后更新：{time}
""".format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

print("    [OK] 总览说明已创建")

# 6. 创建一键启动工具
print()
print("[6/6] 创建一键启动工具...")

with open(os.path.join(FINAL_DIR, "一键部署工具.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 库存管理客户端 - 一键部署工具
color 0A

:menu
cls
echo ============================================================
echo   库存管理客户端 - 一键部署工具
echo ============================================================
echo.
echo 请选择部署方案：
echo.
echo   [1] 方案一：Python源码版（推荐，简单）
echo   [2] 方案二：准备便携版Python
echo   [3] 方案三：打包EXE
echo   [4] 打开最终部署目录
echo   [5] 查看总览说明
echo   [0] 退出
echo.
echo ============================================================
set /p choice=请选择: 

if "%choice%"=="1" goto option1
if "%choice%"=="2" goto option2
if "%choice%"=="3" goto option3
if "%choice%"=="4" goto option4
if "%choice%"=="5" goto option5
if "%choice%"=="0" goto end

echo.
echo 无效选择！
pause
goto menu

:option1
echo.
echo ============================================================
echo   方案一：Python源码版
echo ============================================================
echo.
echo 本方案需要目标电脑有Python 3.8+
echo.
echo 包含文件：
echo   - inventory_client.py
echo   - 启动客户端.bat
echo   - 安装依赖.bat
echo   - 使用说明.txt
echo.
echo ============================================================
echo.
echo 操作：
echo 1. 将本文件夹复制到目标电脑
echo 2. 在目标电脑运行「安装依赖.bat」
echo 3. 双击「启动客户端.bat」
echo.
pause
goto menu

:option2
echo.
echo ============================================================
echo   方案二：便携版Python
echo ============================================================
echo.
echo 正在打开便携版Python准备目录...
explorer "%~dp0便携版Python准备"
echo.
echo 请阅读「下载说明.txt」
echo.
pause
goto menu

:option3
echo.
echo ============================================================
echo   方案三：EXE打包
echo ============================================================
echo.
echo 正在打开EXE打包工具目录...
explorer "%~dp0EXE打包工具"
echo.
echo 运行「一键打包.bat」进行打包
echo.
pause
goto menu

:option4
echo.
echo 正在打开部署目录...
explorer "%~dp0"
pause
goto menu

:option5
echo.
echo 正在打开说明文档...
notepad "%~dp0README - 最终部署说明.txt"
pause
goto menu

:end
echo.
echo 部署完成！
echo.
timeout /t 2 >nul
""")

print("    [OK] 一键部署工具已创建")

# 完成
print()
print("=" * 70)
print("  [OK] 最终一键部署包创建完成！")
print("=" * 70)
print()
print(f"最终部署包位置：{FINAL_DIR}")
print()
print("包含内容：")
for item in sorted(os.listdir(FINAL_DIR)):
    item_path = os.path.join(FINAL_DIR, item)
    if os.path.isdir(item_path):
        print(f"  [DIR] {item}/")
    else:
        print(f"  [FILE] {item}")
print()
print("=" * 70)
print("  您只需要做的")
print("=" * 70)
print()
print("1. 将整个「最终一键复制部署包」文件夹")
print("   复制到U盘或直接复制到目标电脑")
print()
print("2. 在目标电脑，根据情况选择方案一/二/三")
print()
print("3. 如果有预配置，会自动加载！")
print()
print("=" * 70)
print()

# 尝试打开目录
try:
    os.startfile(FINAL_DIR)
except:
    pass
