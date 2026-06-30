# -*- coding: utf-8 -*-
"""
零依赖客户端部署包 - Python版创建器
"""
import os
import sys
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_DIR = os.path.join(BASE_DIR, "零依赖客户端部署包")

print("=" * 60)
print("  库存管理客户端 - 零依赖部署包")
print("=" * 60)
print()

# 1. 清理旧目录
print("[1/5] 清理并创建部署目录...")
if os.path.exists(DEPLOY_DIR):
    shutil.rmtree(DEPLOY_DIR)
os.makedirs(DEPLOY_DIR)
print(f"    目录已创建: {DEPLOY_DIR}")

# 2. 复制主程序文件
print()
print("[2/5] 复制主程序文件...")

# 优先尝试复制Python版（总是可用）
shutil.copy2(os.path.join(BASE_DIR, "inventory_client.py"), DEPLOY_DIR)
print("    [OK] inventory_client.py")

# 创建启动脚本
with open(os.path.join(DEPLOY_DIR, "启动客户端.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 库存管理客户端
cd /d "%~dp0"
echo 正在启动...
python inventory_client.py
if errorlevel 1 (
    echo.
    echo 启动失败！请检查：
    echo 1. 是否安装了 Python 3.8+
    echo 2. 是否运行了「安装依赖.bat」
    echo.
    pause
)
""")
print("    [OK] 启动客户端.bat")

# 创建依赖安装脚本
with open(os.path.join(DEPLOY_DIR, "安装依赖.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
echo ============================================================
echo   安装依赖...
echo ============================================================
echo.
pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.
echo ============================================================
echo   依赖安装完成！
echo ============================================================
echo.
echo 现在可以运行「启动客户端.bat」
echo.
pause
""")
print("    [OK] 安装依赖.bat")

# 3. 复制预配置文件
print()
print("[3/5] 复制预配置文件...")
config_src = os.path.join(BASE_DIR, "inventory_client_config.json")
if os.path.exists(config_src):
    shutil.copy2(config_src, DEPLOY_DIR)
    print("    [OK] inventory_client_config.json")

# 4. 创建说明文档
print()
print("[4/5] 创建说明文档...")

# 使用说明
with open(os.path.join(DEPLOY_DIR, "使用说明.txt"), 'w', encoding='utf-8') as f:
    f.write("""# 库存管理客户端 - 使用说明

## 快速开始

### 第一步：部署
1. 将本文件夹整个复制到目标电脑任意位置

### 第二步：启动
1. 如果目标电脑有Python：
   - 双击「安装依赖.bat」（首次）
   - 双击「启动客户端.bat」
2. 如果目标电脑没有Python：
   - 查看「Python便携版说明.txt」
   - 或使用EXE版（如果有）

### 第三步：配置
1. 启动后点击「设置」
2. 服务器地址：http://服务器IP:8080
   示例：http://192.168.1.100:8080
3. API密钥：steel_belt_inventory_key_2024
4. 点击「保存」
5. 点击「刷新」测试连接

## 获取服务器IP
在服务器电脑上：
- 按 Win+R，输入 cmd
- 输入 ipconfig，找到 IPv4 地址

## 常见问题

Q: 无法连接服务器？
A: 检查
   - 服务器是否已启动
   - IP地址是否正确
   - API密钥是否一致
   - 防火墙是否允许

Q: 提示没有Python？
A: 
   方案A: 安装Python 3.8+（简单）
   方案B: 使用便携版Python（查看相关说明）
   方案C: 使用EXE版（零依赖）
""")
print("    [OK] 使用说明.txt")

# 快速配置
with open(os.path.join(DEPLOY_DIR, "快速配置.txt"), 'w', encoding='utf-8') as f:
    f.write("""# 快速配置 - 3步搞定

## 第一步：获取服务器IP
在服务器电脑上：
1. 按 Win+R
2. 输入 cmd
3. 输入 ipconfig
4. 找到 IPv4 地址（类似：192.168.1.100）

## 第二步：启动客户端
在目标电脑上：
1. 双击「启动客户端.bat」

## 第三步：配置
1. 点击「设置」
2. 服务器地址：http://服务器IP:8080
3. API密钥：steel_belt_inventory_key_2024
4. 保存 → 刷新

完成！
""")
print("    [OK] 快速配置.txt")

# 便携版说明
with open(os.path.join(DEPLOY_DIR, "Python便携版说明.txt"), 'w', encoding='utf-8') as f:
    f.write("""# Python便携版说明

## 适用场景：目标电脑没有Python，又不想安装

## 获取便携版Python

### 方案一：嵌入式Python（推荐，小体积）
1. 访问：https://www.python.org/downloads/windows/
2. 下载 Windows embeddable package (64-bit)
3. 解压到本文件夹，重命名为：python
4. 将目录结构：
   - 本文件夹/
   - 启动客户端.bat
   - python/
   - python/python.exe

### 方案二：WinPython
1. 访问：https://winpython.github.io/
2. 下载 WinPython Zero
3. 解压到本文件夹，重命名为 python

## 使用
1. 将便携版Python放在本文件夹
2. 运行「安装依赖.bat」
3. 启动客户端
""")
print("    [OK] Python便携版说明.txt")

# 一键打开目录脚本
with open(os.path.join(DEPLOY_DIR, "打开本目录.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
explorer "%~dp0"
""")
print("    [OK] 打开本目录.bat")

# 5. 完成
print()
print("=" * 60)
print("  [OK] 零依赖部署包创建完成！")
print("=" * 60)
print()
print(f"部署包位置：{DEPLOY_DIR}")
print()
print("包含文件：")
for item in sorted(os.listdir(DEPLOY_DIR)):
    item_path = os.path.join(DEPLOY_DIR, item)
    if os.path.isdir(item_path):
        print(f"  [DIR] {item}/")
    else:
        print(f"  [FILE] {item}")
print()
print("=" * 60)
print("  使用说明")
print("=" * 60)
print()
print("1. 将整个「零依赖客户端部署包」文件夹")
print("   复制到U盘或目标电脑")
print()
print("2. 如果有预配置，配置会自动加载！")
print()
print("=" * 60)
print()

# 尝试打开目录
try:
    os.startfile(DEPLOY_DIR)
except:
    pass
