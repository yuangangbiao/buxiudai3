
# -*- coding: utf-8 -*-
"""
打包库存管理系统（带批量出入库和打印功能）- 确保正确版本
"""
import os
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 检查inventory_manager_complete.py是否存在
main_file = os.path.join(BASE_DIR, "inventory_manager_complete.py")
if not os.path.exists(main_file):
    print(f"错误：未找到 {main_file}")
    exit(1)

print("=" * 70)
print("  库存管理系统 - EXE打包")
print("=" * 70)
print()
print(f"主程序: {main_file}")
print()

# 先测试主程序是否能正常导入
print("[1/5] 测试主程序...")
test_cmd = ['python', '-c', 'from inventory_manager_complete import InventoryGUI; print("主程序模块加载成功")']
test_result = subprocess.run(test_cmd, capture_output=True, text=True, encoding='gbk', cwd=BASE_DIR)
if test_result.returncode != 0:
    print(f"[FAIL] 主程序测试失败: {test_result.stderr}")
    exit(1)
print("    [OK] 主程序模块加载成功")

# 清理旧目录
TEMP_DIR = os.path.join(BASE_DIR, "final_inventory_exe")
BUILD_DIR = os.path.join(BASE_DIR, "final_inventory_build")

print()
print("[2/5] 清理临时目录...")
if os.path.exists(TEMP_DIR):
    shutil.rmtree(TEMP_DIR)
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)
os.makedirs(TEMP_DIR)
print("    [OK] 清理完成")

# 打包命令
print()
print("[3/5] 开始打包...")
print("    注意：打包过程需要2-5分钟，请耐心等待...")
print()

cmd = [
    r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\Scripts\pyinstaller.exe",
    "--onefile",
    "--windowed",
    "--name=库存管理系统",
    f"--distpath={TEMP_DIR}",
    f"--workpath={BUILD_DIR}",
    "--clean",
    "--hidden-import=pymysql",
    "--hidden-import=tkinter",
    "--hidden-import=tkinter.ttk",
    "--hidden-import=tkinter.messagebox",
    "--hidden-import=tkinter.filedialog",
    "--hidden-import=openpyxl",
    "--hidden-import=inventory_db_complete",
    "--hidden-import=inventory_print",
    "--hidden-import=inventory_backup",
    "inventory_manager_complete.py"
]

result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk', cwd=BASE_DIR)

if result.returncode == 0:
    print("[OK] 打包成功！")
    exe_path = os.path.join(TEMP_DIR, "库存管理系统.exe")
    
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"    文件: {exe_path}")
        print(f"    大小: {size:.2f} MB")
        
        # 复制到目标位置
        TARGET_DIR = r"F:\智能跟单系统\库存管理系统\客户端"
        print()
        print("[4/5] 复制到目标位置...")
        
        if not os.path.exists(TARGET_DIR):
            os.makedirs(TARGET_DIR)
        
        target_path = os.path.join(TARGET_DIR, "库存管理系统.exe")
        if os.path.exists(target_path):
            os.remove(target_path)
        
        shutil.copy2(exe_path, target_path)
        print(f"    [OK] 已复制到: {target_path}")
        
        # 复制配置文件
        config_src = os.path.join(BASE_DIR, "inventory_config.json")
        config_dst = os.path.join(TARGET_DIR, "inventory_config.json")
        if os.path.exists(config_src):
            shutil.copy2(config_src, config_dst)
            print(f"    [OK] 已复制配置文件")
        
        # 验证
        print()
        print("[5/5] 验证完整性...")
        
        if os.path.exists(target_path):
            file_size = os.path.getsize(target_path) / (1024 * 1024)
            print("    [OK] EXE文件存在")
            print(f"    [OK] 文件大小: {file_size:.2f} MB")
            
            if os.path.exists(config_dst):
                print("    [OK] 配置文件存在")
            
            print()
            print("=" * 70)
            print("  ✅ 库存管理系统 EXE 打包完成！")
            print("=" * 70)
            print()
            print(f"📁 EXE文件位置: {target_path}")
            print()
            print("🎯 功能包含:")
            print("  ✅ 批量入库（支持商品搜索、自动计算金额）")
            print("  ✅ 批量出库（库存检查、库存警告）")
            print("  ✅ 库存查询与管理")
            print("  ✅ 打印功能")
            print("  ✅ 数据备份与恢复")
            print("  ✅ MySQL数据库连接")
            print()
            print("🚀 使用方法:")
            print("  1. 双击「库存管理系统.exe」启动")
            print("  2. 配置数据库连接（如果需要）")
            print("  3. 开始使用批量出入库功能")
            print()
            print("=" * 70)
        else:
            print("[FAIL] EXE文件未复制成功！")
    else:
        print("[FAIL] EXE文件未生成！")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
else:
    print("[FAIL] 打包失败！")
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
