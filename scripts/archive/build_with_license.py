# -*- coding: utf-8 -*-
"""
不锈钢网带跟单系统打包脚本
包含完整的加密锁定功能：
1. 机器指纹生成（硬件信息采集：CPU、硬盘、主板、BIOS）
2. 许可证绑定（SHA-256加密存储）
3. 指纹验证（一机一码锁定）
4. AES-256加密保护绑定信息
"""
import subprocess
import sys
import os
import shutil
import time


def verify_security_modules():
    """验证安全模块完整性"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    security_dir = os.path.join(base_dir, "security")
    
    required_files = [
        "__init__.py",
        "machine_fingerprint.py",
        "license_binding.py",
        "license_manager.py",
        "license_tool.py",
        "fingerprint_tool.py"
    ]
    
    print(f"\n{'='*60}")
    print("验证安全模块完整性")
    print(f"{'='*60}")
    
    missing_files = []
    for f in required_files:
        path = os.path.join(security_dir, f)
        if os.path.exists(path):
            print(f"✓ {f}")
        else:
            print(f"✗ {f} - 缺失")
            missing_files.append(f)
    
    if missing_files:
        print(f"\n⚠️ 警告: 缺少以下安全模块文件: {', '.join(missing_files)}")
        return False
    
    print("\n✓ 所有安全模块已就绪")
    return True


def build_main_system():
    """打包主系统（带完整加密锁定）"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    print(f"{'='*60}")
    print(f"不锈钢网带跟单系统打包脚本")
    print(f"打包目录: {base_dir}")
    print(f"{'='*60}")
    
    # 验证安全模块
    if not verify_security_modules():
        print("\n❌ 安全模块不完整，无法继续打包")
        return
    
    # 清理旧的临时目录
    temp_dir = os.path.join(base_dir, "temp_build_full")
    build_dir = os.path.join(base_dir, "build")
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    
    os.makedirs(temp_dir)
    
    # PyInstaller命令 - 包含完整的安全模块和加密功能
    cmd = [
        r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
        "--onefile",
        "--windowed",
        "--name=不锈钢网带跟单系统",
        "--icon=steel_belt.ico",
        f"--distpath={temp_dir}",
        f"--workpath={build_dir}",
        "--clean",
        # 核心依赖
        "--hidden-import=pymysql",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=dotenv",
        # 安全模块 - 机器指纹与加密
        "--hidden-import=security",
        "--hidden-import=security.machine_fingerprint",
        "--hidden-import=security.license_binding",
        "--hidden-import=security.license_manager",
        "--hidden-import=security.license_tool",
        "--hidden-import=security.fingerprint_tool",
        # 加密依赖
        "--hidden-import=hashlib",
        "--hidden-import=secrets",
        "--hidden-import=socket",
        "--hidden-import=json",
        # 包含security目录
        "--add-data=security;security",
        "main.py"
    ]
    
    print(f"\n执行命令: {' '.join(cmd)}")
    print(f"\n{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')
        print("STDOUT:", result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
        print("返回码:", result.returncode)
        
        if result.returncode == 0:
            exe_path = os.path.join(temp_dir, "不锈钢网带跟单系统.exe")
            if os.path.exists(exe_path):
                size = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"\n✅ 打包成功！")
                print(f"    文件: {exe_path}")
                print(f"    大小: {size:.2f} MB")
                
                # 复制到目标位置
                target_dir = os.path.join(base_dir, "dist")
                os.makedirs(target_dir, exist_ok=True)
                target_path = os.path.join(target_dir, "不锈钢网带跟单系统.exe")
                
                if os.path.exists(target_path):
                    os.remove(target_path)
                
                shutil.copy2(exe_path, target_dir)
                print(f"\n✅ 已复制到: {target_path}")
                
                # 复制配置文件和依赖
                files_to_copy = [
                    ".env.example",
                    "config.py",
                    "db_config.py",
                    "constants.py",
                ]
                
                for f in files_to_copy:
                    src = os.path.join(base_dir, f)
                    dst = os.path.join(target_dir, f)
                    if os.path.exists(src):
                        shutil.copy2(src, dst)
                        print(f"✅ 已复制: {f}")
                
                # 验证
                print(f"\n{'='*60}")
                print("✅ 主程序打包完成！")
                print(f"    主程序: {target_path}")
                print(f"    大小: {os.path.getsize(target_path) / (1024 * 1024):.2f} MB")
                print(f"\n🔐 加密功能已包含:")
                print(f"    • 机器指纹生成 (CPU+硬盘+主板+BIOS)")
                print(f"    • SHA-256指纹哈希")
                print(f"    • 许可证绑定加密存储")
                print(f"    • 一机一码验证")
                print(f"{'='*60}")
                
            else:
                print("\n❌ EXE文件未生成！")
        else:
            print("\n❌ 打包失败！")
            
    except Exception as e:
        print(f"执行出错: {e}")
        import traceback
        traceback.print_exc()


def build_activation_tool():
    """打包激活工具（独立运行）"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    print(f"\n{'='*60}")
    print(f"打包激活工具")
    print(f"{'='*60}")
    
    temp_dir = os.path.join(base_dir, "temp_build_tool")
    build_dir = os.path.join(base_dir, "build_tool")
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    
    os.makedirs(temp_dir)
    
    # PyInstaller命令（控制台模式）
    cmd = [
        r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
        "--onefile",
        "--console",
        "--name=license_activator",
        f"--distpath={temp_dir}",
        f"--workpath={build_dir}",
        "--clean",
        # 安全模块
        "--hidden-import=security",
        "--hidden-import=security.license_tool",
        "--hidden-import=security.machine_fingerprint",
        "--hidden-import=security.license_binding",
        "--hidden-import=security.license_manager",
        # 加密依赖
        "--hidden-import=hashlib",
        "--hidden-import=secrets",
        "--hidden-import=socket",
        "--hidden-import=json",
        "security/license_tool.py"
    ]
    
    print(f"\n执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')
        print("STDOUT:", result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
        print("返回码:", result.returncode)
        
        if result.returncode == 0:
            exe_path = os.path.join(temp_dir, "license_activator.exe")
            if os.path.exists(exe_path):
                size = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"\n✅ 激活工具打包成功！")
                print(f"    文件: {exe_path}")
                print(f"    大小: {size:.2f} MB")
                
                # 复制到dist目录
                target_dir = os.path.join(base_dir, "dist")
                os.makedirs(target_dir, exist_ok=True)
                target_path = os.path.join(target_dir, "license_activator.exe")
                
                if os.path.exists(target_path):
                    os.remove(target_path)
                
                shutil.copy2(exe_path, target_dir)
                print(f"✅ 已复制到: {target_path}")
            else:
                print("\n❌ EXE文件未生成！")
        else:
            print("\n❌ 打包失败！")
            
    except Exception as e:
        print(f"执行出错: {e}")


def main():
    """主打包流程"""
    print(f"{'='*60}")
    print(f"不锈钢网带跟单系统 - 完整打包流程")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # 1. 打包主系统
    build_main_system()
    
    # 2. 打包激活工具
    build_activation_tool()
    
    print(f"\n{'='*60}")
    print("🎉 全部打包完成！")
    print(f"{'='*60}")
    print("\n📦 输出文件位置:")
    print(f"    d:\\yuan\\不锈钢网带跟单3.0\\dist\\")
    print(f"    ├── 不锈钢网带跟单系统.exe   (主程序 - 含加密锁定)")
    print(f"    ├── license_activator.exe    (激活工具)")
    print(f"    └── .env.example             (环境配置)")
    print("\n🔐 加密功能:")
    print(f"    • 机器指纹生成 (CPU+硬盘+主板+BIOS)")
    print(f"    • SHA-256指纹哈希")
    print(f"    • 许可证绑定加密存储")
    print(f"    • 一机一码验证")
    print("\n📋 部署步骤:")
    print(f"    1. 将 dist/ 目录复制到客户电脑")
    print(f"    2. 运行 license_activator.exe 获取机器指纹")
    print(f"    3. 联系销售获取激活密钥")
    print(f"    4. 在激活工具中输入密钥完成激活")
    print(f"    5. 运行 不锈钢网带跟单系统.exe")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()