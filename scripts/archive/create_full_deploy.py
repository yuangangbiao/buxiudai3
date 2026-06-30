
# -*- coding: utf-8 -*-
"""
创建不锈钢网带跟单系统完整部署包
"""
import os
import sys
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_DIR = r"F:\智能跟单系统\不锈钢网带跟单系统"

print("=" * 70)
print("  不锈钢网带跟单系统 - 完整部署包")
print("=" * 70)
print()

# 1. 清理并创建目录
print("[1/5] 准备部署目录...")
if os.path.exists(DEPLOY_DIR):
    shutil.rmtree(DEPLOY_DIR)
os.makedirs(DEPLOY_DIR)

# 2. 复制核心项目文件
print()
print("[2/5] 复制核心项目文件...")

# 需要复制的文件和文件夹列表
items_to_copy = [
    # 核心文件
    "main.py",
    "config.py",
    "constants.py",
    "inventory_config.json",
    # 核心模块
    "core/",
    "models/",
    "views/",
    "controllers/",
    "services/",
    "utils/",
    # 依赖文件
    "inventory_db_complete.py",
    "inventory_print.py",
    "inventory_backup.py",
    "backup_system.py",
    "i18n.py",
]

for item in items_to_copy:
    src = os.path.join(BASE_DIR, item)
    dst = os.path.join(DEPLOY_DIR, item)
    
    if os.path.exists(src):
        if os.path.isdir(src):
            shutil.copytree(src, dst)
            print(f"    [OK] {item}/")
        else:
            shutil.copy2(src, dst)
            print(f"    [OK] {item}")

# 3. 创建启动脚本
print()
print("[3/5] 创建启动脚本...")

# 主启动脚本
with open(os.path.join(DEPLOY_DIR, "启动系统.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 不锈钢网带跟单系统
color 0A

cd /d "%~dp0"

echo =======================================================================
echo   不锈钢网带跟单系统 - 启动中...
echo =======================================================================
echo.

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 未找到Python！
    echo.
    echo 请安装Python 3.8+
    echo.
    echo 下载地址：https://www.python.org/downloads/windows/
    echo.
    pause
    exit /b 1
)
echo [OK] Python环境正常

echo.
echo [2/3] 检查依赖...
python -c "import tkinter, pymysql" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [信息] 需要安装依赖...
    echo.
    echo 正在安装依赖...
    pip install pymysql openpyxl pillow
    if errorlevel 1 (
        echo.
        echo [错误] 依赖安装失败！
        echo.
        echo 请尝试手动运行：pip install pymysql openpyxl pillow
        echo.
        pause
        exit /b 1
    )
    echo [OK] 依赖安装完成
)

echo.
echo [3/3] 启动系统...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo 程序异常退出！
    echo.
    pause
)
""")
print("    [OK] 启动系统.bat")

# 依赖安装脚本
with open(os.path.join(DEPLOY_DIR, "安装依赖.bat"), 'w', encoding='gbk') as f:
    f.write("""@echo off
chcp 65001 >nul
title 安装依赖
color 0A

echo =======================================================================
echo   不锈钢网带跟单系统 - 依赖安装
echo =======================================================================
echo.

echo 正在安装依赖包...
echo.

pip install pymysql openpyxl pillow -i https://pypi.tuna.tsinghua.edu.cn/simple

if errorlevel 1 (
    echo.
    echo [错误] 安装失败！
    echo.
    echo 请尝试：
    echo 1. 检查网络连接
    echo 2. 手动运行：pip install pymysql openpyxl pillow
    echo.
) else (
    echo.
    echo [OK] 依赖安装成功！
    echo.
    echo 现在可以运行「启动系统.bat」了！
    echo.
)
pause
""")
print("    [OK] 安装依赖.bat")

# 4. 创建使用说明
print()
print("[4/5] 创建使用说明...")

with open(os.path.join(DEPLOY_DIR, "使用说明.txt"), 'w', encoding='utf-8') as f:
    f.write(f"""# 不锈钢网带跟单系统 - 使用说明

## 🌟 系统简介

本系统是不锈钢网带行业的完整跟单管理系统，包含：
- 订单管理
- 生产管理
- 库存管理
- 物料管理
- 报表统计
- 等等...

---

## 🚀 快速上手

### 第一步：准备环境

1. 确保电脑已安装Python 3.8+
   - 下载地址：https://www.python.org/downloads/windows/

2. 双击运行「安装依赖.bat」（仅第一次）

### 第二步：启动系统

双击「启动系统.bat」

---

## 📦 目录说明

不锈钢网带跟单系统/
├── 启动系统.bat          → 一键启动
├── 安装依赖.bat          → 安装依赖包
├── main.py              → 主程序入口
├── config.py            → 配置文件
├── inventory_config.json → 数据库配置
├── core/               → 核心模块
├── models/             → 数据模型
├── views/              → 界面视图
├── controllers/        → 控制器
├── services/           → 业务服务
└── utils/              → 工具函数

---

## ⚙️ 数据库配置

### 配置数据库连接

1. 首次启动前，检查 inventory_config.json
2. 根据实际情况修改配置

### 数据库初始化

如果数据库还没初始化：
- 使用配套的数据库初始化工具
- 或联系系统管理员

---

## 🎯 主要功能

| 模块 | 说明 |
|-----|-----|
| 订单管理 | 订单创建、查询、修改 |
| 生产管理 | 生产任务、进度跟踪 |
| 库存管理 | 入库、出库、盘点 |
| 物料管理 | 物料清单、需求计算 |
| 报表统计 | 各类统计报表 |

---

## ❓ 常见问题

**Q: 启动报错找不到模块？**
A: 运行「安装依赖.bat」

**Q: 数据库连接失败？**
A: 检查 inventory_config.json 中的配置

**Q: 如何更新系统？**
A: 替换 main.py 和相关模块文件，保持配置文件不变

---

## 📞 技术支持

如有问题，请联系系统管理员

---

版本：3.0
更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
print("    [OK] 使用说明.txt")

# 5. 完成
print()
print("=" * 70)
print("  [OK] 完整部署包创建完成！")
print("=" * 70)
print()
print(f"部署位置：{DEPLOY_DIR}")
print()
print("包含内容：")
for item in sorted(os.listdir(DEPLOY_DIR)):
    item_path = os.path.join(DEPLOY_DIR, item)
    if os.path.isdir(item_path):
        print(f"  [DIR] {item}/")
    else:
        size_kb = os.path.getsize(item_path) / 1024
        print(f"  [FILE] {item} ({size_kb:.1f} KB)")
print()
print("=" * 70)
print("  使用方法")
print("=" * 70)
print()
print("1. 将「不锈钢网带跟单系统」文件夹")
print("   复制到目标电脑")
print()
print("2. 如果是第一次使用")
print("   运行「安装依赖.bat」")
print()
print("3. 双击「启动系统.bat」")
print()
print("=" * 70)
print()

# 尝试打开目录
try:
    os.startfile(DEPLOY_DIR)
except Exception as e:
    print(f"打开部署包目录失败: {e}")
