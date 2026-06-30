# -*- coding: utf-8 -*-
"""
打包完整功能的库存管理客户端为EXE
"""
import os
import subprocess
import shutil

print("=" * 70)
print("  打包完整功能库存管理客户端")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_FILE = os.path.join(BASE_DIR, "inventory_client.py")
OUTPUT_DIR = os.path.join(BASE_DIR, "完整功能EXE部署包")

# 清理旧的输出
if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("开始打包...")
print(f"源文件: {CLIENT_FILE}")
print(f"输出目录: {OUTPUT_DIR}")
print()

# 使用PyInstaller打包
command = [
    "pyinstaller",
    "--onefile",
    "--windowed",
    "--icon=NONE",
    "--name=库存管理客户端",
    "--distpath", OUTPUT_DIR,
    "--workpath", os.path.join(BASE_DIR, "build_temp"),
    "--specpath", BASE_DIR,
    "--hidden-import=requests",
    "--hidden-import=tkinter",
    "--hidden-import=json",
    "--hidden-import=threading",
    "--hidden-import=datetime",
    "--hidden-import=os",
    "--hidden-import=sys",
    "--add-data", f"{os.path.join(BASE_DIR, 'inventory_client_config.json')};.",
    CLIENT_FILE
]

try:
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    if result.returncode == 0:
        print("[OK] 打包成功！")
        print()
        
        # 复制配置文件
        shutil.copy2(
            os.path.join(BASE_DIR, "inventory_client_config.json"),
            os.path.join(OUTPUT_DIR, "inventory_client_config.json")
        )
        print("[OK] 已复制配置文件")
        
        # 创建启动脚本
        startup_bat = '''@echo off
chcp 65001 >nul
title 库存管理系统客户端
start "" "库存管理客户端.exe"
'''
        with open(os.path.join(OUTPUT_DIR, "启动客户端.bat"), 'w', encoding='gbk') as f:
            f.write(startup_bat)
        print("[OK] 已创建启动脚本")
        
        # 创建使用说明
        readme = """# 库存管理系统客户端 - 完整功能版

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

### 第一步：启动客户端
```
双击「库存管理客户端.exe」
或双击「启动客户端.bat」
```

### 第二步：配置服务器（首次运行）
```
点击「设置」按钮
服务器地址: http://192.168.1.32:8080
API密钥: steel_belt_inventory_key_2024
点击「保存」→「刷新」
```

## 文件结构

```
完整功能EXE部署包/
├── 库存管理客户端.exe          ← 主程序（零依赖）
├── inventory_client_config.json  ← 配置文件
├── 启动客户端.bat              ← 启动脚本
└── README.txt                  ← 使用说明
```

## 系统要求

- Windows 7/8/10/11
- 网络连接（连接服务器）

## 服务器配置

| 配置项 | 值 |
|--------|-----|
| 服务器地址 | http://192.168.1.32:8080 |
| API密钥 | steel_belt_inventory_key_2024 |

## 技术支持

如有问题，请联系管理员。

---
版本: 1.0.0 - 完整功能版
"""
        with open(os.path.join(OUTPUT_DIR, "README.txt"), 'w', encoding='utf-8') as f:
            f.write(readme)
        print("[OK] 已创建使用说明")
        
        # 检查生成的文件
        exe_path = os.path.join(OUTPUT_DIR, "库存管理客户端.exe")
        if os.path.exists(exe_path):
            size = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"[OK] EXE文件大小: {size:.2f} MB")
        
        print()
        print("=" * 70)
        print("  [OK] 打包完成！")
        print("=" * 70)
        print()
        print(f"部署包位置: {OUTPUT_DIR}")
        print()
        print("包含功能：")
        print("  📦 库存管理（入库、出库、查询、盘点）")
        print("  🏭 仓库管理（多仓库支持、库存转移）")
        print("  📊 统计报表（库存统计、数据导出）")
        print("  🖨️ 打印功能（打印预览、单据打印）")
        print("  ⚙️ 系统设置（服务器配置、API密钥）")
        print()
        print("使用方式：")
        print("  1. 复制整个「完整功能EXE部署包」文件夹")
        print("  2. 在目标电脑双击「库存管理客户端.exe」")
        print("  3. 配置服务器地址即可使用")
        
        # 打开输出目录
        try:
            os.startfile(OUTPUT_DIR)
        except:
            pass
            
    else:
        print("[ERROR] 打包失败！")
        print("错误信息:")
        print(result.stderr[:2000] if result.stderr else "无详细错误信息")
        
except Exception as e:
    print(f"[ERROR] 打包过程出错: {e}")
