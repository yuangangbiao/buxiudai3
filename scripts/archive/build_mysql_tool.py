# -*- coding: utf-8 -*-
"""
MySQL数据库工具打包脚本
"""
import subprocess
import sys
import os
import shutil


def build_mysql_tool():
    """打包MySQL数据库工具"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    print(f"{'='*60}")
    print(f"MySQL数据库工具打包脚本")
    print(f"打包目录: {base_dir}")
    print(f"{'='*60}")

    # 清理旧的临时目录
    temp_dir = os.path.join(base_dir, "temp_build_mysql_tool")
    build_dir = os.path.join(base_dir, "build_mysql_tool")

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
        "--name=MySQL数据库工具",
        f"--distpath={temp_dir}",
        f"--workpath={build_dir}",
        "--clean",
        "--hidden-import=pymysql",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.scrolledtext",
        "--add-data=.env.example;.",
        "mysql_tool.py"
    ]

    print(f"\n执行命令: {' '.join(cmd)}")
    print(f"\n{'='*60}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')
        print("STDOUT:", result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
        print("返回码:", result.returncode)

        if result.returncode == 0:
            exe_path = os.path.join(temp_dir, "MySQL数据库工具.exe")
            if os.path.exists(exe_path):
                size = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"\n✅ 打包成功！")
                print(f"    文件: {exe_path}")
                print(f"    大小: {size:.2f} MB")

                # 复制到dist目录
                target_dir = os.path.join(base_dir, "dist")
                os.makedirs(target_dir, exist_ok=True)
                target_path = os.path.join(target_dir, "MySQL数据库工具.exe")

                if os.path.exists(target_path):
                    os.remove(target_path)

                shutil.copy2(exe_path, target_dir)
                print(f"\n✅ 已复制到: {target_path}")

                print(f"\n{'='*60}")
                print("✅ MySQL数据库工具打包完成！")
                print(f"    输出位置: {target_path}")
                print(f"\n📋 工具功能:")
                print(f"    1. MySQL连接测试")
                print(f"    2. 数据库初始化（创建表结构）")
                print(f"    3. 修改Root密码")
                print(f"    4. 创建应用用户")
                print(f"    5. 授予/撤销数据库权限")
                print(f"    6. 查看所有用户")
                print(f"    7. 查看所有数据库")
                print(f"    8. 查看表结构")
                print(f"{'='*60}")

            else:
                print("\n❌ EXE文件未生成！")
        else:
            print("\n❌ 打包失败！")

    except Exception as e:
        print(f"执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    build_mysql_tool()
    input("\n按回车键退出...")