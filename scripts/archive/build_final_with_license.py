# -*- coding: utf-8 -*-
"""
打包不锈钢网带跟单系统 - 带机器指纹加密（智能收集版）
"""
import subprocess
import os
import shutil

base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)

# 清理旧的构建目录
build_dir = os.path.join(base_dir, "build_with_license_temp")
if os.path.exists(build_dir):
    shutil.rmtree(build_dir)

# 删除旧的EXE
old_exe = os.path.join(base_dir, "dist", "不锈钢网带跟单系统.exe")
if os.path.exists(old_exe):
    os.remove(old_exe)

# PyInstaller命令 - 使用collect-all自动收集模块
cmd = [
    r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
    "--onefile",
    "--windowed",
    "--name=不锈钢网带跟单系统",
    "--distpath=./dist",
    "--workpath=./build_with_license_temp",
    "--clean",
    # 自动收集模块
    "--collect-submodules=numpy",
    "--collect-submodules=PIL",
    "--collect-submodules=openpyxl",
    "--collect-all=pymysql",
    "--collect-all=dotenv",
    # tkinter子模块
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.ttk",
    "--hidden-import=tkinter.messagebox",
    "--hidden-import=tkinter.filedialog",
    "--hidden-import=tkinter.colorchooser",
    "--hidden-import=tkinter.commondialog",
    # 安全模块
    "--hidden-import=security",
    "--hidden-import=security.machine_fingerprint",
    "--hidden-import=security.license_binding",
    "--hidden-import=security.license_manager",
    "--hidden-import=security.license_tool",
    "--hidden-import=security.fingerprint_tool",
    # 添加security目录
    "--add-data=security;security",
    "main.py"
]

print("=" * 70)
print("打包不锈钢网带跟单系统（带机器指纹加密 - 智能收集版）")
print("=" * 70)
print(f"命令: {' '.join(cmd)}")
print("=" * 70)

result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')
print(result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout)
if result.stderr:
    stderr = result.stderr[-3000:] if len(result.stderr) > 3000 else result.stderr
    if "missing module" in stderr.lower():
        print("\n⚠️ 缺少模块警告:")
        print(stderr[-1500:])
print("返回码:", result.returncode)

if result.returncode == 0:
    print("\n✅ 打包成功！")
    exe_path = os.path.join(base_dir, "dist", "不锈钢网带跟单系统.exe")
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n📦 输出位置: {exe_path}")
        print(f"   文件大小: {size:.2f} MB")
    print("\n🔐 包含的加密功能:")
    print("   • 机器指纹生成 (CPU+硬盘+主板+BIOS)")
    print("   • SHA-256指纹哈希")
    print("   • 许可证绑定加密存储")
    print("   • 一机一码验证")
else:
    print("\n❌ 打包失败！")
    print("\n请检查错误信息")

input("\n按回车键退出...")