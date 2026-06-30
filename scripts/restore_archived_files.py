# -*- coding: utf-8 -*-
"""
文件恢复脚本
将归档目录中的文件恢复到原始位置
"""
import os
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

def restore_scripts():
    """恢复scripts目录文件"""
    scripts_dir = PROJECT_DIR / 'scripts'
    archive_dir = PROJECT_DIR / 'archive' / 'scripts'
    
    restored_count = 0
    
    # 遍历归档目录下的所有子目录
    for category_dir in archive_dir.iterdir():
        if category_dir.is_dir():
            category_name = category_dir.name
            
            # 移动该分类下的所有文件
            for file_path in category_dir.iterdir():
                if file_path.is_file():
                    dest_path = scripts_dir / file_path.name
                    
                    # 如果目标文件已存在，先删除
                    if dest_path.exists():
                        print(f"⚠️  目标已存在，覆盖: {file_path.name}")
                    
                    shutil.move(str(file_path), str(dest_path))
                    print(f"📦 恢复: {file_path.name} <- {category_name}/")
                    restored_count += 1
    
    print(f"\n📊 scripts目录恢复完成: 恢复 {restored_count} 个文件")

def restore_views():
    """恢复views目录文件"""
    archive_dir = PROJECT_DIR / 'archive' / 'views'
    
    restored_count = 0
    
    # 遍历归档目录下的所有子目录
    for category_dir in archive_dir.iterdir():
        if category_dir.is_dir():
            category_name = category_dir.name
            
            # 移动该分类下的所有文件
            for file_path in category_dir.iterdir():
                if file_path.is_file():
                    # 根据分类确定目标路径
                    if category_name == 'orders备份':
                        dest_path = PROJECT_DIR / 'views' / 'orders' / file_path.name
                    elif category_name == 'dashboard旧版本':
                        dest_path = PROJECT_DIR / 'views' / 'dashboard' / 'templates' / file_path.name
                    else:
                        dest_path = PROJECT_DIR / 'views' / file_path.name
                    
                    # 如果目标文件已存在，先删除
                    if dest_path.exists():
                        print(f"⚠️  目标已存在，覆盖: {dest_path}")
                    
                    shutil.move(str(file_path), str(dest_path))
                    print(f"📦 恢复: {dest_path.relative_to(PROJECT_DIR)} <- {category_name}/")
                    restored_count += 1
    
    print(f"\n📊 views目录恢复完成: 恢复 {restored_count} 个文件")

def main():
    print("=" * 60)
    print("文件恢复脚本")
    print("=" * 60)
    print()
    
    # 恢复scripts目录
    print("--- 1/2 恢复scripts目录 ---")
    restore_scripts()
    print()
    
    # 恢复views目录
    print("--- 2/2 恢复views目录 ---")
    restore_views()
    print()
    
    print("=" * 60)
    print("恢复完成！所有文件已恢复到原始位置。")
    print("=" * 60)

if __name__ == "__main__":
    main()
