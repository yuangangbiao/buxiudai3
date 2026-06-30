# -*- coding: utf-8 -*-
"""
创建包含便携版Python的零依赖部署包
即使没有EXE，也能零依赖使用
"""
import os
import sys
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_DIR = os.path.join(BASE_DIR, "完整零依赖部署包")

print("=" * 70)
print("  库存管理客户端 - 完整零依赖部署包")
print("=" * 70)
print()

# 1. 清理目录
print("[1/5] 准备部署目录...")
if os.path.exists(DEPLOY_DIR):
    shutil.rmtree(DEPLOY_DIR)
os.makedirs(DEPLOY_DIR)

# 2. 复制主程序
print()
print("[2/5] 复制主程序文件...")

shutil.copy2(os.path.join(BASE_DIR, "inventory_client.py"), DEPLOY_DIR)
print("    [OK] inventory_client.py")

# 复制预配置
config_src = os.path.join(BASE_DIR, "inventory_client_config.json")
if os.path.exists(config_src):
    shutil.copy2(config_src, DEPLOY_DIR)
    print("    [OK] inventory_client_config.json")

# 3. 创建启动脚本
print()
print("[3/5] 创建启动脚本...")

# 主启动脚本 - 智能选择
with open(os.path.join(DEPLOY_DIR, "启动客户端.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 库存管理客户端
cd /d "%~dp0"

echo ============================================================
echo   库存管理客户端 - 启动中...
echo ============================================================
echo.

REM 优先尝试便携版Python
if exist "python\\python.exe" (
    echo [1/3] 使用便携版Python...
    python\\python.exe inventory_client.py
    if not errorlevel 1 goto end
)

REM 尝试系统Python
echo [2/3] 尝试系统Python...
python inventory_client.py
if not errorlevel 1 goto end

REM 都没有，给出提示
echo.
echo ============================================================
echo   [错误] 未找到Python！
echo ============================================================
echo.
echo 请选择以下方案之一：
echo.
echo 方案一：安装Python 3.8+
echo   然后运行「安装依赖.bat」
echo.
echo 方案二：使用便携版Python
echo   查看「Python便携版说明.txt」
echo.
echo 方案三：使用EXE版
echo   查看「EXE打包指南.txt」
echo.
echo ============================================================
echo.
pause
goto end

:end
echo.
echo 客户端已退出
pause
""")
print("    [OK] 启动客户端.bat")

# 依赖安装脚本
with open(os.path.join(DEPLOY_DIR, "安装依赖.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 安装依赖
echo ============================================================
echo   安装依赖...
echo ============================================================
echo.

if exist "python\\python.exe" (
    echo 使用便携版Python安装...
    python\\python.exe -m pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
) else (
    echo 使用系统Python安装...
    pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo.
echo ============================================================
echo   依赖安装完成！
echo ============================================================
echo.
echo 现在可以运行「启动客户端.bat」了
echo.
pause
""")
print("    [OK] 安装依赖.bat")

# 4. 创建说明文档
print()
print("[4/5] 创建说明文档...")

# 主说明
with open(os.path.join(DEPLOY_DIR, "README - 零依赖使用说明.txt"), 'w', encoding='utf-8') as f:
    f.write("""# 库存管理客户端 - 零依赖使用说明

## 🌟 超级简单！零依赖部署

### 您只需要：
1. 将「完整零依赖部署包」整个文件夹复制到目标电脑
2. 根据情况选择方案一/二/三
3. 双击「启动客户端.bat」

---

## 📦 三种部署方案

### 方案一：使用便携版Python（推荐，真零依赖）

1. **准备便携版Python**
   - 访问：https://www.python.org/downloads/windows/
   - 下载：Windows embeddable package (64-bit)
   - 解压到本文件夹，重命名为「python」

2. **安装pip**
   - 下载：https://bootstrap.pypa.io/get-pip.py
   - 放到 python/ 目录
   - 运行：python/python.exe get-pip.py

3. **安装依赖**
   - 双击运行「安装依赖.bat」

4. **启动**
   - 双击「启动客户端.bat」

### 方案二：目标电脑有Python（最简单）

1. 双击运行「安装依赖.bat」（仅第一次）
2. 双击「启动客户端.bat」

### 方案三：使用EXE版（最完美）

1. 在服务器电脑运行「EXE打包指南」里的工具
2. 打包出EXE文件
3. 将EXE复制到目标电脑，直接双击使用

---

## ⚙️ 配置说明

### 配置服务器连接

1. 启动客户端后，点击「设置」
2. 服务器地址：http://服务器IP:8080
   例如：http://192.168.1.100:8080
3. API密钥：steel_belt_inventory_key_2024
4. 保存 → 刷新

### 获取服务器IP

在服务器电脑上：
- 按 Win+R
- 输入 cmd
- 输入 ipconfig
- 找到 IPv4 地址

### 预配置（可选）

如果已在服务器配置好客户端：
- inventory_client_config.json 已保存配置
- 一起复制，目标电脑会自动加载！

---

## 📋 目录结构

完整零依赖部署包/
├── inventory_client.py          → 主程序
├── inventory_client_config.json → 预配置（如果有）
├── 启动客户端.bat              → 智能启动脚本
├── 安装依赖.bat                → 依赖安装脚本
├── README - 零依赖使用说明.txt → 本文档
├── Python便携版说明.txt        → 便携版详细说明
├── EXE打包指南.txt             → EXE打包说明
├── 快速配置.txt                → 3步配置
└── 打开本目录.bat              → 快速打开
""")
print("    [OK] README - 零依赖使用说明.txt")

# 便携版详细说明
with open(os.path.join(DEPLOY_DIR, "Python便携版说明.txt"), 'w', encoding='utf-8') as f:
    f.write("""# Python便携版 - 详细说明

## 适用场景
目标电脑没有Python，又不想安装

---

## 方案一：嵌入式Python（推荐，小体积）

### 1. 下载
访问：https://www.python.org/downloads/windows/
下载：Windows embeddable package (64-bit)
（例如：python-3.11.9-embed-amd64.zip）

### 2. 解压
将压缩包解压到本文件夹，重命名为：python

目录结构应该是：
完整零依赖部署包/
├── python/
│   ├── python.exe
│   └── ...
├── 启动客户端.bat
└── ...

### 3. 安装pip
下载：https://bootstrap.pypa.io/get-pip.py
放到 python/ 目录

打开命令行（CMD），进入本文件夹：
python\\python.exe get-pip.py

### 4. 安装依赖
双击「安装依赖.bat」

### 5. 完成！
双击「启动客户端.bat」

---

## 方案二：WinPython

### 1. 下载
访问：https://winpython.github.io/
下载：WinPython Zero

### 2. 使用
解压到本文件夹，重命名为：python
直接使用，通常已包含pip

---

## 验证安装

运行「安装依赖.bat」，如果成功，说明便携版Python配置正确！
""")
print("    [OK] Python便携版说明.txt")

# EXE打包指南
with open(os.path.join(DEPLOY_DIR, "EXE打包指南.txt"), 'w', encoding='utf-8') as f:
    f.write("""# EXE打包指南

## 什么时候用EXE？
- 需要最完美的零依赖方案
- 目标电脑不想有任何Python痕迹
- 想要单文件，双击即用

---

## 如何打包？

### 在服务器电脑上：

1. 确保有Python 3.8+ 和 PyInstaller

2. 运行打包工具：
   - 运行项目目录里的「package_exe_now.py」
   - 或使用「full_build_client.py」

3. 等待打包完成（2-5分钟）

4. 获取EXE文件：
   - 从 client_build_exe/dist/ 目录
   - 找到「库存管理客户端.exe」

5. 部署EXE：
   - 只需要复制「库存管理客户端.exe」
   - 可选：一起复制「inventory_client_config.json」（预配置）
   - 目标电脑双击即用！

---

## EXE的优点

- 真零依赖，不需要Python
- 单文件，易于分发
- 启动简单，双击即用
- 不需要配置环境
""")
print("    [OK] EXE打包指南.txt")

# 快速配置
with open(os.path.join(DEPLOY_DIR, "快速配置.txt"), 'w', encoding='utf-8') as f:
    f.write("""# 快速配置 - 3步

## 第一步：获取服务器IP
在服务器电脑上：
1. 按 Win+R
2. 输入 cmd
3. 输入 ipconfig
4. 找到 IPv4 地址（类似：192.168.1.100）

## 第二步：启动客户端
在目标电脑上双击「启动客户端.bat」

## 第三步：配置连接
1. 点击「设置」
2. 服务器地址：http://服务器IP:8080
3. API密钥：steel_belt_inventory_key_2024
4. 点击「保存」→ 点击「刷新」

完成！
""")
print("    [OK] 快速配置.txt")

# 打开目录脚本
with open(os.path.join(DEPLOY_DIR, "打开本目录.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
explorer "%~dp0"
""")
print("    [OK] 打开本目录.bat")

# 5. 完成
print()
print("=" * 70)
print("  [OK] 完整零依赖部署包创建完成！")
print("=" * 70)
print()
print(f"部署包位置：{DEPLOY_DIR}")
print()
print("包含文件：")
for item in sorted(os.listdir(DEPLOY_DIR)):
    item_path = os.path.join(DEPLOY_DIR, item)
    if os.path.isdir(item_path):
        print(f"  [DIR] {item}/")
    else:
        size_kb = os.path.getsize(item_path) / 1024
        print(f"  [FILE] {item} ({size_kb:.1f} KB)")
print()
print("=" * 70)
print("  您只需要做的")
print("=" * 70)
print()
print("1. 将「完整零依赖部署包」整个文件夹")
print("   复制到U盘或目标电脑")
print()
print("2. 在目标电脑，选择方案一/二/三：")
print("   - 方案一：使用便携版Python（真零依赖）")
print("   - 方案二：系统已有Python（最简单）")
print("   - 方案三：使用EXE版（最完美）")
print()
print("3. 根据相应方案操作")
print()
print("=" * 70)
print()

# 尝试打开目录
try:
    os.startfile(DEPLOY_DIR)
except:
    pass
