# -*- coding: utf-8 -*-
"""
将打包好的EXE复制到最终部署包
"""
import os
import sys
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 70)
print("  EXE打包完成！正在创建最终部署包")
print("=" * 70)
print()

# 1. 检查EXE
print("[1/3] 检查EXE文件...")
exe_src = os.path.join(BASE_DIR, "client_build_exe", "dist", "库存管理客户端.exe")
if os.path.exists(exe_src):
    size_mb = os.path.getsize(exe_src) / (1024 * 1024)
    print(f"    [OK] EXE文件存在: {exe_src}")
    print(f"    文件大小: {size_mb:.2f} MB")
else:
    print("    [ERROR] 未找到EXE文件")
    sys.exit(1)

# 2. 创建最终部署包
print()
print("[2/3] 创建最终零依赖EXE部署包...")
FINAL_DIR = os.path.join(BASE_DIR, "最终零依赖EXE部署包")
if os.path.exists(FINAL_DIR):
    shutil.rmtree(FINAL_DIR)
os.makedirs(FINAL_DIR)

# 复制EXE
shutil.copy2(exe_src, FINAL_DIR)
print("    [OK] EXE已复制")

# 复制配置文件
config_src = os.path.join(BASE_DIR, "inventory_client_config.json")
if os.path.exists(config_src):
    shutil.copy2(config_src, FINAL_DIR)
    print("    [OK] 预配置已复制")

# 3. 创建说明
print()
print("[3/3] 创建说明文档...")

with open(os.path.join(FINAL_DIR, "README - 超级简单使用说明.txt"), 'w', encoding='utf-8') as f:
    f.write('''# 最终零依赖EXE部署包 - 超级简单！

## 🎉 恭喜！您拥有了真正的零依赖客户端！

---

## ✨ 您只需要做一件事

   ┌─────────────────────────────────────────────┐
   │  将「最终零依赖EXE部署包」整个文件夹    │
   │  复制到目标电脑任意位置                     │
   └─────────────────────────────────────────────┘

---

## 🚀 启动客户端

   ┌─────────────────────────────────────────────┐
   │  在目标电脑上双击「库存管理客户端.exe」  │
   └─────────────────────────────────────────────┘

   就这么简单！零依赖！

---

## ⚙️ 配置说明

### 首次使用配置

1. 启动后点击「设置」
2. 服务器地址：http://服务器IP:8080
   例如：http://192.168.1.100:8080
3. API密钥：steel_belt_inventory_key_2024
4. 点击「保存」→ 点击「刷新」

### 如何获取服务器IP

在服务器电脑上：
- 按 Win+R → 输入 cmd → 输入 ipconfig
- 找到 IPv4 地址

### 预配置（如果有）

如果有 inventory_client_config.json：
- 将此文件放在EXE同一目录
- 启动会自动加载配置

---

## 📋 目录内容

最终零依赖EXE部署包/
├── 库存管理客户端.exe          → 核心程序，双击即用
├── inventory_client_config.json → 预配置（如果有）
└── README - 超级简单使用说明.txt → 本文档

---

## 🌟 完成！

零依赖！单文件！双击即用！

''')
print("    [OK] 说明文档已创建")

with open(os.path.join(FINAL_DIR, "快速配置.txt"), 'w', encoding='utf-8') as f:
    f.write('''# 快速配置 - 2步

## 第一步：获取服务器IP
在服务器电脑上：
1. 按 Win+R → 输入 cmd → 输入 ipconfig
2. 找到 IPv4 地址（类似：192.168.1.100）

## 第二步：配置客户端
1. 在目标电脑双击「库存管理客户端.exe」
2. 点击「设置」
3. 服务器地址：http://服务器IP:8080
4. API密钥：steel_belt_inventory_key_2024
5. 点击「保存」→ 点击「刷新」

完成！

''')
print("    [OK] 快速配置已创建")

# 打开目录工具
with open(os.path.join(FINAL_DIR, "打开本目录.bat"), 'w', encoding='gbk') as f:
    f.write('''@echo off
chcp 65001 >nul
explorer "%~dp0"
''')
print("    [OK] 打开工具已创建")

print()
print("=" * 70)
print("  [OK] 最终零依赖EXE部署包创建完成！")
print("=" * 70)
print()
print(f"部署包位置：{FINAL_DIR}")
print()
print("包含文件：")
for item in sorted(os.listdir(FINAL_DIR)):
    item_path = os.path.join(FINAL_DIR, item)
    if os.path.isdir(item_path):
        print(f"  [DIR] {item}/")
    else:
        size_kb = os.path.getsize(item_path) / 1024
        print(f"  [FILE] {item} ({size_kb:.1f} KB)")
print()
print("=" * 70)
print("  🌟 恭喜！您拥有了真正的零依赖客户端！")
print("=" * 70)
print()
print("您只需要做的：")
print()
print("1. 将「最终零依赖EXE部署包」整个文件夹")
print("   复制到U盘或目标电脑")
print()
print("2. 在目标电脑双击「库存管理客户端.exe」")
print()
print("零依赖！单文件！双击即用！")
print()
print("=" * 70)

# 尝试打开目录
try:
    os.startfile(FINAL_DIR)
except:
    pass
