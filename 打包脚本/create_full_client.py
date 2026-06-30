# -*- coding: utf-8 -*-
"""
创建完整功能的客户端部署包
"""
import os
import shutil
import sys

print("=" * 70)
print("  创建完整功能客户端部署包")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 定义源文件和目标目录
SOURCE_FILES = [
    ("inventory_client.py", "库存管理客户端.py"),
    ("inventory_client_config.json", "inventory_client_config.json"),
    ("utils/api_client.py", "utils/api_client.py"),
    ("utils/logger.py", "utils/logger.py"),
    ("utils/helpers.py", "utils/helpers.py"),
    ("gui/main_window.py", "gui/main_window.py"),
    ("gui/inventory_view.py", "gui/inventory_view.py"),
    ("gui/warehouse_view.py", "gui/warehouse_view.py"),
    ("gui/settings_dialog.py", "gui/settings_dialog.py"),
    ("gui/print_preview.py", "gui/print_preview.py"),
    ("gui/about_dialog.py", "gui/about_dialog.py"),
]

DEST_DIR = os.path.join(BASE_DIR, "完整功能客户端部署包")
os.makedirs(DEST_DIR, exist_ok=True)
os.makedirs(os.path.join(DEST_DIR, "utils"), exist_ok=True)
os.makedirs(os.path.join(DEST_DIR, "gui"), exist_ok=True)

# 复制文件
print("复制核心文件...")
for src, dest in SOURCE_FILES:
    src_path = os.path.join(BASE_DIR, src)
    dest_path = os.path.join(DEST_DIR, dest)
    if os.path.exists(src_path):
        shutil.copy2(src_path, dest_path)
        print(f"    [OK] {dest}")
    else:
        print(f"    [WARN] {src} 不存在")

print()

# 创建启动脚本
print("创建启动脚本...")
startup_content = '''@echo off
chcp 65001 >nul
title 库存管理系统客户端

echo ============================================================
echo.
echo            库存管理系统客户端
echo.
echo ============================================================
echo.

echo Starting inventory client...
python "库存管理客户端.py"

if errorlevel 1 (
    echo.
    echo [ERROR] 启动失败！
    echo.
    echo 请检查：
    echo 1. 是否安装了 Python 3.8+
    echo 2. 是否运行了「安装依赖.bat」
    echo.
    pause
)
'''

with open(os.path.join(DEST_DIR, "启动客户端.bat"), 'w', encoding='gbk') as f:
    f.write(startup_content)
print("    [OK] 启动客户端.bat")

# 创建依赖安装脚本
deps_content = '''@echo off
chcp 65001 >nul
title Install Dependencies

echo ============================================================
echo.
echo            安装依赖库
echo.
echo ============================================================
echo.

echo Installing required packages...
pip install requests flask pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ============================================================
echo   Installation Complete
echo ============================================================
echo.
pause
'''

with open(os.path.join(DEST_DIR, "安装依赖.bat"), 'w', encoding='gbk') as f:
    f.write(deps_content)
print("    [OK] 安装依赖.bat")

# 创建使用说明
readme_content = '''# 库存管理系统客户端 - 使用说明

## 功能特性

### 📦 库存管理
- 产品入库管理
- 产品出库管理
- 库存查询
- 库存盘点

### 🏭 仓库管理
- 多仓库支持
- 仓库库存统计
- 库存转移

### 📊 统计报表
- 库存统计
- 出入库记录
- 数据导出

### 🖨️ 打印功能
- 打印预览
- 出库单打印
- 入库单打印

### ⚙️ 系统设置
- 服务器配置
- API密钥管理
- 自动刷新设置

## 快速开始

### 第一步：安装依赖（首次运行）
```
双击「安装依赖.bat」
等待安装完成
```

### 第二步：配置服务器
```
双击「启动客户端.bat」
在设置中配置：
- 服务器地址: http://192.168.1.32:8080
- API密钥: steel_belt_inventory_key_2024
```

### 第三步：启动客户端
```
双击「启动客户端.bat」
```

## 文件结构

```
完整功能客户端部署包/
├── 库存管理客户端.py      ← 主程序
├── inventory_client_config.json  ← 配置文件
├── utils/
│   ├── api_client.py      ← API客户端
│   ├── logger.py          ← 日志模块
│   └── helpers.py         ← 辅助函数
├── gui/
│   ├── main_window.py     ← 主窗口
│   ├── inventory_view.py  ← 库存视图
│   ├── warehouse_view.py  ← 仓库视图
│   ├── settings_dialog.py ← 设置对话框
│   ├── print_preview.py   ← 打印预览
│   └── about_dialog.py    ← 关于对话框
├── 启动客户端.bat         ← 启动脚本
├── 安装依赖.bat           ← 依赖安装
└── README.txt             ← 使用说明
```

## 系统要求

- Windows 7/8/10/11
- Python 3.8 或更高版本
- 网络连接（连接服务器）

## 服务器配置

| 配置项 | 值 |
|--------|-----|
| 服务器地址 | http://192.168.1.32:8080 |
| API密钥 | steel_belt_inventory_key_2024 |
| 数据库 | inventory_management_db |

## 技术支持

如有问题，请联系管理员。

---
版本: 1.0.0
日期: 2024
'''

with open(os.path.join(DEST_DIR, "README.txt"), 'w', encoding='utf-8') as f:
    f.write(readme_content)
print("    [OK] README.txt")

print()
print("=" * 70)
print("  [OK] 完整功能客户端部署包创建完成")
print("=" * 70)
print()
print(f"位置: {DEST_DIR}")
print()
print("包含功能：")
print("  📦 库存管理（入库、出库、查询、盘点）")
print("  🏭 仓库管理（多仓库支持、库存转移）")
print("  📊 统计报表（库存统计、数据导出）")
print("  🖨️ 打印功能（打印预览、单据打印）")
print("  ⚙️ 系统设置（服务器配置、API密钥）")
print()
print("=" * 70)

# 打开目录
try:
    os.startfile(DEST_DIR)
except:
    pass
