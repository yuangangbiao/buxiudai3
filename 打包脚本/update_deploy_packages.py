# -*- coding: utf-8 -*-
"""
重新打包服务端和客户端EXE，包含最新功能更新
"""
import os
import shutil
import subprocess

print("=" * 70)
print("  重新打包服务端和客户端EXE")
print("=" * 70)
print()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. 更新服务端EXE
print("[1/2] 更新服务端EXE...")
server_exe_dir = os.path.join(BASE_DIR, "零依赖服务器EXE部署包")
server_src = os.path.join(BASE_DIR, "inventory_server.py")

# 清理旧文件
if os.path.exists(os.path.join(server_exe_dir, "库存管理系统服务器.exe")):
    os.remove(os.path.join(server_exe_dir, "库存管理系统服务器.exe"))

# 复制最新源码
shutil.copy2(server_src, os.path.join(server_exe_dir, "inventory_server.py"))
print("    [OK] 已复制最新服务器源码")

# 复制其他依赖文件
deps = ["inventory_db_complete.py", "inventory_backup.py", "inventory_print.py", "inventory_manager_complete.py"]
for dep in deps:
    src = os.path.join(BASE_DIR, dep)
    dst = os.path.join(server_exe_dir, dep)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"    [OK] 已复制 {dep}")

print()

# 2. 更新客户端EXE
print("[2/2] 更新客户端EXE部署包...")
client_exe_dir = os.path.join(BASE_DIR, "最终零依赖EXE部署包")
client_src = os.path.join(BASE_DIR, "inventory_client.py")

# 复制最新客户端源码
shutil.copy2(client_src, os.path.join(client_exe_dir, "库存管理客户端.py"))
print("    [OK] 已复制最新客户端源码")

# 更新配置文件
config_src = os.path.join(BASE_DIR, "inventory_client_config.json")
config_dst = os.path.join(client_exe_dir, "inventory_client_config.json")
if os.path.exists(config_src):
    shutil.copy2(config_src, config_dst)
    print("    [OK] 已更新配置文件")

# 更新说明文档
readme_content = """# 库存管理系统客户端 - 最终零依赖版

## 更新日志

### v3.0.1 - 新增功能
- ✅ 新增服务器连接模块
  - 服务器状态检查
  - 服务器信息显示
  - 重新连接功能
- ✅ 新增容器连接模块
  - 容器状态检查
  - 容器列表管理
  - 启动/停止容器

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

### 🔗 服务器连接
- 服务器状态检查
- 服务器信息显示
- 重新连接

### 📦 容器连接
- 容器状态检查
- 容器列表管理
- 启动/停止容器

### ⚙️ 系统设置
- 服务器配置
- API密钥管理
- 自动刷新设置

## 快速开始

### 第一步：启动客户端
```
双击「库存管理客户端.exe」
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
最终零依赖EXE部署包/
├── 库存管理客户端.exe          ← 主程序（零依赖）
├── inventory_client_config.json  ← 配置文件
├── README - 超级简单使用说明.txt  ← 使用说明
├── 快速配置.txt                  ← 配置指南
└── 打开本目录.bat               ← 快捷工具
```

## 系统要求

- Windows 7/8/10/11
- 网络连接（连接服务器）

## 服务器配置

| 配置项 | 值 |
|--------|-----|
| 服务器地址 | http://192.168.1.32:8080 |
| API密钥 | steel_belt_inventory_key_2024 |

---
版本: 3.0.1
"""

with open(os.path.join(client_exe_dir, "README - 超级简单使用说明.txt"), 'w', encoding='utf-8') as f:
    f.write(readme_content)
print("    [OK] 已更新说明文档")

print()
print("=" * 70)
print("  [OK] 更新完成！")
print("=" * 70)
print()
print("服务端部署包:")
print(f"  {server_exe_dir}")
print()
print("客户端部署包:")
print(f"  {client_exe_dir}")
print()
print("新增功能:")
print("  ✅ 服务器连接模块")
print("  ✅ 容器连接模块")

# 打开客户端部署包目录
try:
    os.startfile(client_exe_dir)
except:
    pass
