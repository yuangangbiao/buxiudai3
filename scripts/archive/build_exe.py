
# -*- coding: utf-8 -*-
"""
打包库存管理系统为 EXE
"""
import subprocess
import sys
import os
import shutil

def main():
    base_dir = r"d:\yuan\不锈钢网带跟单3.0"
    os.chdir(base_dir)
    
    # 清理旧的临时目录
    temp_dir = os.path.join(base_dir, "temp_complete_exe")
    build_dir = os.path.join(base_dir, "temp_build_complete")
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    
    os.makedirs(temp_dir)
    
    cmd = [
        r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
        "--onefile",
        "--windowed",
        "--name=库存管理系统客户端",
        "--icon=inventory.ico",
        f"--distpath={temp_dir}",
        f"--workpath={build_dir}",
        "--clean",
        "--hidden-import=pymysql",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=tkinter.filedialog",
        "inventory_manager_complete.py"
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk')
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        print("返回码:", result.returncode)
        
        if result.returncode == 0:
            exe_path = os.path.join(temp_dir, "库存管理系统客户端.exe")
            if os.path.exists(exe_path):
                size = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"\n✅ 打包成功！")
                print(f"    文件: {exe_path}")
                print(f"    大小: {size:.2f} MB")
                
                # 复制到目标位置
                target_dir = r"F:\智能跟单系统\库存管理系统\客户端"
                target_path = os.path.join(target_dir, "库存管理系统客户端.exe")
                
                if os.path.exists(target_path):
                    os.remove(target_path)
                
                shutil.copy2(exe_path, target_dir)
                print(f"\n✅ 已复制到: {target_path}")
                
                # 复制配置文件
                config_src = os.path.join(base_dir, "inventory_config.json")
                config_dst = os.path.join(target_dir, "inventory_config.json")
                if os.path.exists(config_src):
                    shutil.copy2(config_src, config_dst)
                    print(f"✅ 已复制配置文件: {config_dst}")
                
                # 验证
                if os.path.exists(target_path):
                    print(f"\n✅ 完整性检查通过！")
                    print(f"    客户端EXE: {os.path.getsize(target_path) / (1024 * 1024):.2f} MB")
                    if os.path.exists(config_dst):
                        print(f"    配置文件: {os.path.getsize(config_dst) / 1024:.2f} KB")
            else:
                print("\n❌ EXE文件未生成！")
        else:
            print("\n❌ 打包失败！")
            
    except Exception as e:
        print(f"执行出错: {e}")

if __name__ == "__main__":
    main()
