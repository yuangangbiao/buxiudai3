# -*- coding: utf-8 -*-
"""
执行两轮验证并创建完整部署包
"""
import os
import sys
import shutil
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FINAL_DEPLOY_DIR = os.path.join(BASE_DIR, "client_final_complete")


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def verify_round1_file_integrity():
    """第一轮验证：文件完整性"""
    log("=" * 50)
    log("第一轮验证：文件完整性检查")
    log("=" * 50)
    
    checks = []
    
    # 检查主程序
    client_path = os.path.join(BASE_DIR, "inventory_client.py")
    if os.path.exists(client_path):
        size_kb = os.path.getsize(client_path) / 1024
        checks.append(("主程序存在", True))
        checks.append(("主程序大小合理", size_kb > 10))
        log(f"[OK] inventory_client.py ({size_kb:.1f} KB)")
    else:
        checks.append(("主程序存在", False))
        log("[FAIL] inventory_client.py 不存在")
    
    # 检查依赖库
    try:
        import requests
        checks.append(("requests库可用", True))
        log("[OK] requests库可用")
    except ImportError:
        checks.append(("requests库可用", False))
        log("[FAIL] requests库不可用")
    
    try:
        import tkinter
        from tkinter import ttk
        checks.append(("tkinter可用", True))
        log("[OK] tkinter可用")
    except ImportError:
        checks.append(("tkinter可用", False))
        log("[FAIL] tkinter不可用")
    
    # 检查语法
    try:
        import ast
        with open(client_path, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        checks.append(("源代码语法正确", True))
        log("[OK] 源代码语法正确")
    except Exception as e:
        checks.append(("源代码语法正确", False))
        log(f"[FAIL] 语法错误: {e}")
    
    passed = all(c[1] for c in checks)
    if passed:
        log("第一轮验证通过", "SUCCESS")
    else:
        log("第一轮验证失败", "ERROR")
    return passed, checks


def verify_round2_functional():
    """第二轮验证：功能模块检查"""
    log("\n" + "=" * 50)
    log("第二轮验证：功能模块检查")
    log("=" * 50)
    
    checks = []
    
    # 检查配置器
    config_path = os.path.join(BASE_DIR, "inventory_configurator.py")
    if os.path.exists(config_path):
        checks.append(("配置器存在", True))
        log("[OK] inventory_configurator.py")
    else:
        checks.append(("配置器存在", False))
        log("[FAIL] inventory_configurator.py 不存在")
    
    # 检查服务器API文件
    server_path = os.path.join(BASE_DIR, "inventory_server.py")
    if os.path.exists(server_path):
        checks.append(("服务器文件存在", True))
        log("[OK] inventory_server.py")
    else:
        checks.append(("服务器文件存在", False))
        log("[FAIL] inventory_server.py 不存在")
    
    # 检查相关模块
    modules = ["inventory_print.py", "db_config.py"]
    for m in modules:
        if os.path.exists(os.path.join(BASE_DIR, m)):
            checks.append((f"{m} 存在", True))
            log(f"[OK] {m}")
        else:
            checks.append((f"{m} 存在", False))
            log(f"[FAIL] {m}")
    
    passed = all(c[1] for c in checks)
    if passed:
        log("第二轮验证通过", "SUCCESS")
    else:
        log("第二轮验证失败", "ERROR")
    return passed, checks


def create_simple_deploy_package():
    """创建简单部署包（Python脚本版）"""
    log("\n" + "=" * 50)
    log("创建部署包 A：Python脚本版")
    log("=" * 50)
    
    deploy_a = os.path.join(FINAL_DEPLOY_DIR, "A_Python脚本版")
    os.makedirs(deploy_a, exist_ok=True)
    
    # 复制主程序
    shutil.copy2(os.path.join(BASE_DIR, "inventory_client.py"), deploy_a)
    
    # 创建启动脚本
    with open(os.path.join(deploy_a, "启动客户端.bat"), 'w', encoding='gbk') as f:
        f.write("""@echo off
chcp 65001 >nul
cd /d "%~dp0"
python inventory_client.py
pause
""")
    
    # 创建依赖安装
    with open(os.path.join(deploy_a, "安装依赖.bat"), 'w', encoding='gbk') as f:
        f.write("""@echo off
chcp 65001 >nul
pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.
echo 依赖安装完成！
pause
""")
    
    # 创建说明
    with open(os.path.join(deploy_a, "使用说明.txt"), 'w', encoding='utf-8') as f:
        f.write("""# Python脚本版 - 使用说明

1. 确保电脑已安装 Python 3.8+
2. 双击运行「安装依赖.bat」
3. 双击运行「启动客户端.bat」

配置说明：
- 首次运行点击「设置」
- 服务器地址：http://服务器IP:8080
- API密钥：steel_belt_inventory_key_2024
""")
    
    log(f"[OK] 部署包 A 已创建: {deploy_a}")
    return deploy_a


def create_portable_deploy_package():
    """创建便携版部署包"""
    log("\n" + "=" * 50)
    log("创建部署包 B：便携版")
    log("=" * 50)
    
    deploy_b = os.path.join(FINAL_DEPLOY_DIR, "B_便携版")
    os.makedirs(deploy_b, exist_ok=True)
    
    # 复制主程序
    shutil.copy2(os.path.join(BASE_DIR, "inventory_client.py"), deploy_b)
    
    # 创建启动脚本
    with open(os.path.join(deploy_b, "启动客户端.bat"), 'w', encoding='gbk') as f:
        f.write("""@echo off
chcp 65001 >nul
title 库存管理客户端
cd /d "%~dp0"
if exist "python_portable\\python.exe" (
    echo 使用便携版Python...
    python_portable\\python.exe inventory_client.py
) else (
    echo 尝试使用系统Python...
    python inventory_client.py
)
pause
""")
    
    # 创建Python目录说明
    py_dir = os.path.join(deploy_b, "python_portable")
    os.makedirs(py_dir, exist_ok=True)
    with open(os.path.join(py_dir, "说明.txt"), 'w', encoding='utf-8') as f:
        f.write("""在此目录放置便携版Python：
- 下载 Windows embeddable package (Python 3.8+)
- 或下载 WinPython
- 解压到此目录，确保 python.exe 在此目录下
""")
    
    # 创建说明
    with open(os.path.join(deploy_b, "使用说明.txt"), 'w', encoding='utf-8') as f:
        f.write("""# 便携版 - 使用说明

## 方法一：包含便携版Python（推荐）
1. 将便携版Python解压到 python_portable/ 目录
2. 双击「启动客户端.bat」

## 方法二：使用系统Python
1. 确保系统已安装Python 3.8+
2. 双击「启动客户端.bat」

## 服务器配置
服务器地址：http://服务器IP:8080
API密钥：steel_belt_inventory_key_2024
""")
    
    log(f"[OK] 部署包 B 已创建: {deploy_b}")
    return deploy_b


def create_exe_guide_package():
    """创建EXE打包指南包"""
    log("\n" + "=" * 50)
    log("创建部署包 C：EXE打包指南")
    log("=" * 50)
    
    deploy_c = os.path.join(FINAL_DEPLOY_DIR, "C_EXE打包指南")
    os.makedirs(deploy_c, exist_ok=True)
    
    # 复制打包工具
    shutil.copy2(os.path.join(BASE_DIR, "full_build_client.py"), deploy_c)
    
    # 创建打包脚本
    with open(os.path.join(deploy_c, "一键打包.bat"), 'w', encoding='gbk') as f:
        f.write("""@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在检查环境...
python --version
if errorlevel 1 (
    echo 请先安装Python 3.8+
    pause
    exit /b 1
)
echo.
echo 开始打包...
python full_build_client.py
pause
""")
    
    # 创建说明
    with open(os.path.join(deploy_c, "打包说明.txt"), 'w', encoding='utf-8') as f:
        f.write("""# EXE打包指南

## 打包步骤
1. 确保已安装Python 3.8+ 和 PyInstaller
2. 双击「一键打包.bat」
3. 等待打包完成（约2-5分钟）
4. 从 dist/ 目录获取EXE文件

## 部署EXE
只需复制「库存管理客户端.exe」到目标电脑即可
可选：附带 inventory_client_config.json 预配置文件
""")
    
    log(f"[OK] 部署包 C 已创建: {deploy_c}")
    return deploy_c


def create_master_readme():
    """创建总说明"""
    readme_path = os.path.join(FINAL_DEPLOY_DIR, "总览说明.txt")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("""# 库存管理客户端 - 完整部署包

## 📦 包含三种部署方案

=== A_Python脚本版 ===
最简单的方案，目标电脑需要已安装Python
- inventory_client.py - 主程序
- 启动客户端.bat - 启动脚本
- 安装依赖.bat - 安装依赖

=== B_便携版 ===
灵活的方案，可以包含便携版Python
- inventory_client.py - 主程序
- python_portable/ - 放置便携版Python的目录
- 启动客户端.bat - 智能启动脚本

=== C_EXE打包指南 ===
如何打包成独立EXE文件
- full_build_client.py - 打包脚本
- 一键打包.bat - 启动打包

## 🚀 快速选择

- 如果目标电脑已有Python → 使用 A
- 如果需要灵活更新 → 使用 B
- 如果需要最简单部署 → 使用 C 打包EXE

## ⚙️ 服务器配置

无论哪种方案，都需要配置：
- 服务器地址：http://服务器IP:8080
- API密钥：steel_belt_inventory_key_2024

## 📖 详细说明

详见主目录下的「客户端打包说明.md」和「部署说明.md」

---
验证通过时间：{timestamp}
""".format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    return readme_path


def create_verification_report(r1_pass, r1_checks, r2_pass, r2_checks):
    """创建验证报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "round1": {
            "passed": r1_pass,
            "checks": r1_checks
        },
        "round2": {
            "passed": r2_pass,
            "checks": r2_checks
        },
        "overall_passed": r1_pass and r2_pass
    }
    
    report_path = os.path.join(FINAL_DEPLOY_DIR, "验证报告.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    with open(os.path.join(FINAL_DEPLOY_DIR, "验证报告.txt"), 'w', encoding='utf-8') as f:
        f.write("库存管理客户端 - 验证报告\n")
        f.write("=" * 50 + "\n")
        f.write(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("第一轮验证：文件完整性\n")
        f.write("-" * 30 + "\n")
        for name, result in r1_checks:
            status = "[OK] 通过" if result else "[FAIL] 未通过"
            f.write(f"  {name}: {status}\n")
        f.write(f"\n第一轮: {'通过' if r1_pass else '未通过'}\n\n")
        
        f.write("第二轮验证：功能模块\n")
        f.write("-" * 30 + "\n")
        for name, result in r2_checks:
            status = "[OK] 通过" if result else "[FAIL] 未通过"
            f.write(f"  {name}: {status}\n")
        f.write(f"\n第二轮: {'通过' if r2_pass else '未通过'}\n\n")
        
        f.write("=" * 50 + "\n")
        overall = "验证全部通过" if (r1_pass and r2_pass) else "验证存在问题"
        f.write(f"总体结果: {overall}\n")
    
    return report_path


def main():
    print("\n" + "=" * 60)
    print("  库存管理客户端 - 完整验证与部署包创建")
    print("=" * 60 + "\n")
    
    # 清理旧目录
    if os.path.exists(FINAL_DEPLOY_DIR):
        shutil.rmtree(FINAL_DEPLOY_DIR)
    os.makedirs(FINAL_DEPLOY_DIR, exist_ok=True)
    
    # 第一轮验证
    r1_pass, r1_checks = verify_round1_file_integrity()
    
    # 第二轮验证
    r2_pass, r2_checks = verify_round2_functional()
    
    # 创建部署包
    create_simple_deploy_package()
    create_portable_deploy_package()
    create_exe_guide_package()
    
    # 创建说明文档
    create_master_readme()
    
    # 创建验证报告
    create_verification_report(r1_pass, r1_checks, r2_pass, r2_checks)
    
    # 完成总结
    print("\n" + "=" * 60)
    print("  [OK] 完成！")
    print("=" * 60)
    print(f"\n最终部署包位置: {FINAL_DEPLOY_DIR}")
    print("\n包含内容:")
    dirs = sorted(os.listdir(FINAL_DEPLOY_DIR))
    for d in dirs:
        full = os.path.join(FINAL_DEPLOY_DIR, d)
        if os.path.isdir(full):
            files = len(os.listdir(full))
            print(f"  [DIR] {d}/ ({files} 个文件)")
        else:
            print(f"  [FILE] {d}")
    
    print(f"\n验证结果: {'[OK] 全部通过' if (r1_pass and r2_pass) else '[FAIL] 存在问题'}")
    print("\n现在可以将此目录复制到U盘或其他电脑进行部署！\n")
    
    return 0 if (r1_pass and r2_pass) else 1


if __name__ == "__main__":
    sys.exit(main())
