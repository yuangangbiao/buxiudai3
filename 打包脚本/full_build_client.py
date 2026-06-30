# -*- coding: utf-8 -*-
"""
库存管理客户端 - 完整打包与验证系统
包含两轮验证机制确保打包完整
"""

import os
import sys
import shutil
import subprocess
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BASE_DIR, "client_build")
OUTPUT_DIR = os.path.join(BUILD_DIR, "dist")
FINAL_DIR = os.path.join(BASE_DIR, "client_final_package")


def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def check_python():
    """检查Python环境"""
    log("检查Python环境...")
    try:
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            log(f"Python版本: {version.major}.{version.minor}.{version.micro} - 符合要求", "SUCCESS")
            return True
        else:
            log(f"Python版本过低: {version.major}.{version.minor}，需要3.8+", "ERROR")
            return False
    except Exception as e:
        log(f"检查Python环境失败: {e}", "ERROR")
        return False


def install_pyinstaller():
    """安装PyInstaller"""
    log("检查PyInstaller...")
    try:
        import PyInstaller
        log(f"PyInstaller已安装: {PyInstaller.__version__}", "SUCCESS")
        return True
    except ImportError:
        log("正在安装PyInstaller...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "pyinstaller",
                "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
            ])
            log("PyInstaller安装成功", "SUCCESS")
            return True
        except Exception as e:
            log(f"PyInstaller安装失败: {e}", "ERROR")
            return False


def check_source_files():
    """检查源文件完整性"""
    log("检查源文件...")
    required_files = [
        "inventory_client.py",
    ]
    
    missing = []
    for f in required_files:
        if not os.path.exists(os.path.join(BASE_DIR, f)):
            missing.append(f)
    
    if missing:
        log(f"缺少必要文件: {missing}", "ERROR")
        return False
    else:
        log("所有源文件完整", "SUCCESS")
        return True


def cleanup_old_build():
    """清理旧的构建目录"""
    log("清理旧构建...")
    for dirname in [BUILD_DIR, FINAL_DIR]:
        if os.path.exists(dirname):
            shutil.rmtree(dirname)
            log(f"已删除: {dirname}")
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return True


def create_spec_file():
    """创建PyInstaller spec文件"""
    log("创建打包配置...")
    
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['{os.path.join(BASE_DIR, "inventory_client.py")}'],
    pathex=['{BASE_DIR}'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'requests',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'json',
        'os',
        'sys',
        'threading',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='库存管理客户端',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    spec_path = os.path.join(BUILD_DIR, "inventory_client.spec")
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    log(f"配置文件已创建: {spec_path}", "SUCCESS")
    return spec_path


def run_pyinstaller(spec_path):
    """运行PyInstaller"""
    log("=" * 60)
    log("开始打包...")
    log("=" * 60)
    
    try:
        os.chdir(BUILD_DIR)
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", spec_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            log("打包成功完成", "SUCCESS")
            return True
        else:
            log(f"打包返回错误: {result.returncode}", "ERROR")
            log(f"错误输出: {result.stderr[-500:] if result.stderr else '无'}", "ERROR")
            return False
            
    except Exception as e:
        log(f"打包异常: {e}", "ERROR")
        return False


def verify_round1_file_check():
    """第一轮验证：文件完整性检查"""
    log("\n" + "=" * 60)
    log("第一轮验证：文件完整性检查")
    log("=" * 60)
    
    exe_path = os.path.join(OUTPUT_DIR, "库存管理客户端.exe")
    
    checks = []
    
    # 检查EXE是否存在
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        checks.append(("EXE文件存在", True))
        checks.append((f"文件大小: {size_mb:.2f} MB", size_mb > 10))  # 应该大于10MB
        log(f"✓ EXE文件存在，大小: {size_mb:.2f} MB")
    else:
        checks.append(("EXE文件存在", False))
        log("✗ EXE文件不存在")
    
    # 检查目录结构
    if os.path.exists(OUTPUT_DIR):
        files = os.listdir(OUTPUT_DIR)
        checks.append(("输出目录存在", True))
        log(f"✓ 输出目录存在，文件数: {len(files)}")
    else:
        checks.append(("输出目录存在", False))
        log("✗ 输出目录不存在")
    
    passed = all(check[1] for check in checks)
    
    if passed:
        log("第一轮验证通过", "SUCCESS")
    else:
        log("第一轮验证失败", "ERROR")
    
    return passed


def verify_round2_function_test():
    """第二轮验证：功能测试（导入测试）"""
    log("\n" + "=" * 60)
    log("第二轮验证：功能模块测试")
    log("=" * 60)
    
    checks = []
    
    # 测试1：检查源代码是否可导入
    try:
        log("测试1: 检查源代码模块...")
        import ast
        with open(os.path.join(BASE_DIR, "inventory_client.py"), 'r', encoding='utf-8') as f:
            content = f.read()
            ast.parse(content)
        checks.append(("源代码语法正确", True))
        log("✓ 源代码语法正确")
    except Exception as e:
        checks.append(("源代码语法正确", False))
        log(f"✗ 源代码语法错误: {e}")
    
    # 测试2：检查依赖库
    try:
        log("测试2: 检查依赖库...")
        import requests
        checks.append(("requests库可用", True))
        log("✓ requests库可用")
    except ImportError:
        checks.append(("requests库可用", False))
        log("✗ requests库不可用")
    
    # 测试3：检查tkinter
    try:
        log("测试3: 检查tkinter...")
        import tkinter
        from tkinter import ttk
        checks.append(("tkinter可用", True))
        log("✓ tkinter可用")
    except ImportError:
        checks.append(("tkinter可用", False))
        log("✗ tkinter不可用")
    
    passed = all(check[1] for check in checks)
    
    if passed:
        log("第二轮验证通过", "SUCCESS")
    else:
        log("第二轮验证失败", "ERROR")
    
    return passed


def create_final_package():
    """创建最终部署包"""
    log("\n" + "=" * 60)
    log("创建最终部署包")
    log("=" * 60)
    
    os.makedirs(FINAL_DIR, exist_ok=True)
    
    # 复制EXE
    exe_src = os.path.join(OUTPUT_DIR, "库存管理客户端.exe")
    exe_dst = os.path.join(FINAL_DIR, "库存管理客户端.exe")
    if os.path.exists(exe_src):
        shutil.copy2(exe_src, exe_dst)
        log(f"✓ 已复制: 库存管理客户端.exe")
    
    # 创建使用说明
    readme_content = """# 库存管理客户端 - 使用说明

## 快速开始

### 第一步：准备服务器配置
确保库存管理系统服务器已启动，并记录：
- 服务器IP地址
- 端口号
- API密钥

### 第二步：运行客户端
直接双击 `库存管理客户端.exe`

### 第三步：配置连接
1. 点击"设置"按钮
2. 配置服务器地址（例如：http://192.168.1.100:8080）
3. 配置API密钥（与服务器一致）
4. 点击保存
5. 点击刷新测试连接

## 预配置（可选）

如果有 `inventory_client_config.json` 文件：
1. 将其放在与EXE同一目录
2. 启动时会自动加载配置

## 功能说明

- 库存列表：查看所有库存
- 统计信息：查看统计数据
- 出入库流水：查看记录
- 通知消息：查看并处理通知
- 刷新：重新从服务器加载数据
- 设置：配置服务器连接

## 常见问题

Q: 无法连接服务器？
A: 1. 检查服务器是否已启动
   2. 确认IP地址和端口正确
   3. 确认API密钥一致
   4. 检查防火墙设置

Q: 如何获取服务器IP？
A: 在服务器电脑上打开CMD，输入 `ipconfig`，查找IPv4地址

## 技术支持

详见 `部署说明.md`

---
版本：3.0
日期：2024
"""
    
    readme_path = os.path.join(FINAL_DIR, "使用说明.txt")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    log(f"✓ 已创建: 使用说明.txt")
    
    # 创建快速配置指南
    quick_guide = """# 快速配置指南

## 3步完成配置

1️⃣ 获取服务器信息
   - 在服务器电脑按 Win+R，输入 cmd
   - 输入 ipconfig，找到 IPv4 地址（如 192.168.1.100）
   - 确认服务器已启动

2️⃣ 运行客户端
   - 双击 库存管理客户端.exe

3️⃣ 配置连接
   - 点击"设置"
   - 服务器地址: http://服务器IP:8080
   - API密钥: steel_belt_inventory_key_2024
   - 保存 → 刷新

完成！
"""
    quick_path = os.path.join(FINAL_DIR, "快速配置.txt")
    with open(quick_path, 'w', encoding='utf-8') as f:
        f.write(quick_guide)
    log(f"✓ 已创建: 快速配置.txt")
    
    # 复制配置文件（如果存在）
    config_src = os.path.join(BASE_DIR, "inventory_client_config.json")
    if os.path.exists(config_src):
        shutil.copy2(config_src, os.path.join(FINAL_DIR, "inventory_client_config.json"))
        log(f"✓ 已复制: inventory_client_config.json")
    
    log("\n最终部署包创建完成！", "SUCCESS")
    log(f"位置: {FINAL_DIR}")
    
    return True


def create_build_report(success):
    """创建构建报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
    
    report_path = os.path.join(FINAL_DIR, "构建报告.json") if success else os.path.join(BUILD_DIR, "构建报告.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report_path


def main():
    log("=" * 60)
    log("库存管理客户端 - 完整打包与验证系统")
    log("=" * 60)
    
    steps = [
        ("检查Python环境", check_python),
        ("安装PyInstaller", install_pyinstaller),
        ("检查源文件", check_source_files),
        ("清理旧构建", cleanup_old_build),
    ]
    
    for step_name, step_func in steps:
        log(f"\n执行: {step_name}")
        if not step_func():
            log("\n打包流程中止", "ERROR")
            return False
    
    # 创建配置并打包
    spec_path = create_spec_file()
    if not run_pyinstaller(spec_path):
        log("\n打包失败", "ERROR")
        create_build_report(False)
        return False
    
    # 第一轮验证
    if not verify_round1_file_check():
        log("\n第一轮验证失败", "ERROR")
        create_build_report(False)
        return False
    
    # 第二轮验证
    if not verify_round2_function_test():
        log("\n第二轮验证失败", "ERROR")
        create_build_report(False)
        return False
    
    # 创建最终包
    if not create_final_package():
        log("\n创建部署包失败", "ERROR")
        create_build_report(False)
        return False
    
    # 完成
    create_build_report(True)
    
    log("\n" + "=" * 60)
    log("🎉 打包与验证全部完成！")
    log("=" * 60)
    log(f"\n最终部署包位置: {FINAL_DIR}")
    log("\n包含文件:")
    for f in os.listdir(FINAL_DIR):
        fpath = os.path.join(FINAL_DIR, f)
        size = os.path.getsize(fpath) / 1024
        log(f"  - {f} ({size:.1f} KB)")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("\n\n用户中断", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"\n\n发生未预期的错误: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)
