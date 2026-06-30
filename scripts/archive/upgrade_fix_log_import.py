# -*- coding: utf-8 -*-
"""
修复工单创建漏洞升级包 v1.0
修复 models/production.py 缺少 log 函数导入的问题
"""

import os
import sys

def get_project_dir():
    """获取项目目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return script_dir

def fix_production_import():
    """修复 production.py 缺少的 import"""
    project_dir = get_project_dir()
    file_path = os.path.join(project_dir, 'models', 'production.py')

    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'from utils.op_logger import log, log_step, log_sql, log_error' in content:
        print("已经修复，无需更新")
        return True

    if 'from constants import ProductionStatus, OrderStatus' in content:
        if 'op_logger' not in content:
            new_import = """from utils.op_logger import log, log_step, log_sql, log_error
"""
            content = content.replace(
                'from constants import ProductionStatus, OrderStatus',
                new_import + 'from constants import ProductionStatus, OrderStatus'
            )

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"已修复: {file_path}")
            return True

    print("未找到需要修复的代码")
    return False

def main():
    print("=" * 60)
    print("修复工单创建漏洞升级包 v1.0")
    print("=" * 60)
    print()

    if fix_production_import():
        print()
        print("=" * 60)
        print("修复完成！请重启主软件。")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("修复失败，请手动检查。")
        print("=" * 60)

if __name__ == '__main__':
    main()
