# -*- coding: utf-8 -*-
"""
许可证激活工具打包脚本
"""
import subprocess
import sys
import os
import shutil


def build_license_tool():
    """打包许可证激活工具"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    print(f"{'='*60}")
    print(f"许可证激活工具打包脚本")
    print(f"打包目录: {base_dir}")
    print(f"{'='*60}")

    # 清理旧的临时目录
    temp_dir = os.path.join(base_dir, "temp_build_license")
    build_dir = os.path.join(base_dir, "build_license")

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    os.makedirs(temp_dir)

    # PyInstaller命令
    cmd = [
        r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
        "--onefile",
        "--windowed",
        "--name=许可证激活工具",
        f"--distpath={temp_dir}",
        f"--workpath={build_dir}",
        "--clean",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.scrolledtext",
        "--hidden-import=tkinter.colorchooser",
        "--hidden-import=hashlib",
        "--hidden-import=json",
        "--hidden-import=datetime",
        "--hidden-import=uuid",
        "--hidden-import=subprocess",
        "--hidden-import=platform",
        "--hidden-import=ctypes",
        "security/fingerprint_unlock_gui.py"
    ]

    print(f"\n执行命令: {' '.join(cmd)}")
    print(f"\n{'='*60}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')
        if result.stdout:
            print("STDOUT:", result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
        print("返回码:", result.returncode)

        if result.returncode == 0:
            exe_path = os.path.join(temp_dir, "许可证激活工具.exe")
            if os.path.exists(exe_path):
                size = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"\n✅ 打包成功！")
                print(f"    文件: {exe_path}")
                print(f"    大小: {size:.2f} MB")

                # 复制到dist目录
                target_dir = os.path.join(base_dir, "dist")
                os.makedirs(target_dir, exist_ok=True)
                target_path = os.path.join(target_dir, "许可证激活工具.exe")

                if os.path.exists(target_path):
                    os.remove(target_path)

                shutil.copy2(exe_path, target_dir)
                print(f"\n✅ 已复制到: {target_path}")

                print(f"\n{'='*60}")
                print("✅ 许可证激活工具打包完成！")
                print(f"    输出位置: {target_path}")
                print(f"\n📋 工具功能:")
                print(f"    1. 查看机器指纹")
                print(f"    2. 激活许可证")
                print(f"    3. 验证激活状态")
                print(f"    4. 解除激活")
                print(f"{'='*60}")

            else:
                print("\n❌ EXE文件未生成！")
        else:
            print("\n❌ 打包失败！")

    except Exception as e:
        print(f"执行出错: {e}")


if __name__ == "__main__":
    build_license_tool()