# -*- coding: utf-8 -*-
"""
文件归档脚本
将指定文件移动到归档目录
"""
import os
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

# 归档目录映射
ARCHIVE_MAP = {
    # 公式计算旧版本
    '公式计算旧版本': [
        'diagnose_material_calc.py',
        'diagnose_material_calc_v2.py',
        'diagnose_material_calc_v3.py',
        'diagnose_material_calc_v4.py',
        'fix_formula_safe.py',
        'fix_formula_variables.py',
        'simple_calc.py',
        'simulate_calc.py',
        'simulate_full_calc.py',
        'final_simulate.py',
        'full_simulate.py',
        'full_formula.py',
        'fixed_calc.py',
        'find_coefficient.py',
        'find_formula_problems.py',
    ],
    # 检查脚本
    '检查脚本': [
        'check_prod_17.py',
        'check_prod_orders.py',
        'check_productions.py',
        'check_quality_tables.py',
        'check_types.py',
        'check_original_status.py',
        'check_formula_length.py',
        'check_fixable_rules.py',
        'check_db_total.py',
    ],
    # 添加字段脚本
    '添加字段脚本': [
        'add_total_length.py',
        'add_total_length_17.py',
        'add_mesh_pitch.py',
        'add_inspection_seq.py',
        'step1_add_fields.py',
    ],
    # 分析脚本
    '分析脚本': [
        'analyze_all_rules.py',
        'analyze_formula.py',
        'analyze_problem.py',
    ],
    # 验证脚本
    '验证脚本': [
        'verify_calc.py',
        'verify_00623.py',
        'verify_fix.py',
        'verify_total_length.py',
    ],
    # 调试脚本
    '调试脚本': [
        'debug_process_view.py',
        'debug_production.py',
        'debug_stats_view.py',
    ],
    # 测试脚本
    '测试脚本': [
        'test_calc.py',
        'test_calculator.py',
        'test_both.py',
    ],
    # 获取保存脚本
    '获取保存脚本': [
        'get_formula.py',
        'get_formula2.py',
        'get_rule_72.py',
        'save_formula.py',
        'save_rule_72.py',
    ],
    # 修复脚本
    '修复脚本': [
        'fix_order_17_params.py',
        'fix_total_length.py',
    ],
    # 其他脚本
    '其他脚本': [
        'compare_orders.py',
        'extend_and_sync.py',
        'simple_update.py',
    ],
}

# views目录归档
VIEWS_ARCHIVE_MAP = {
    'orders备份': [
        'views/orders/new_order_dialog_backup_v200.py',
    ],
    'dashboard旧版本': [
        'views/dashboard/templates/dashboard_v1.html',
        'views/dashboard/templates/dashboard_v2.html',
        'views/dashboard/templates/dashboard_v3.html',
    ],
}

# 保留的脚本（不归档）
KEEP_SCRIPTS = [
    '__init__.py',
    'order_archive_manager.py',
    'order_cli.py',
    'unarchive_order.py',
    'sync_orders.py',
    'sync_process_rules.py',
    'diagnose_material_calc_v5.py',
    'fix_formula_variables_v2.py',
    'check_all_rules.py',
    'check_quality_rules.py',
    'check_all_orders.py',
    'check_prod_status.py',
    'check_formula.py',
    'save_all_rules.py',
    'check_all_prod_status.py',
    'check_tables.py',
    'test_order_functions.py',
    'check_archive_logic.py',
    'check_archive_filter.py',
    'check_db_formula.py',
    'archive_files.py',  # 当前脚本不归档
]

def archive_scripts():
    """归档scripts目录文件"""
    scripts_dir = PROJECT_DIR / 'scripts'
    archive_dir = PROJECT_DIR / 'archive' / 'scripts'
    
    moved_count = 0
    skipped_count = 0
    
    for category, files in ARCHIVE_MAP.items():
        dest_dir = archive_dir / category
        
        for filename in files:
            src_path = scripts_dir / filename
            
            if src_path.exists():
                # 检查是否应该保留
                if filename in KEEP_SCRIPTS:
                    print(f"⏭️  跳过保留文件: {filename}")
                    skipped_count += 1
                    continue
                
                dest_path = dest_dir / filename
                shutil.move(str(src_path), str(dest_path))
                print(f"📦 移动: {filename} -> {category}/")
                moved_count += 1
            else:
                print(f"⚠️ 文件不存在: {filename}")
    
    print(f"\n📊 scripts目录归档完成: 移动 {moved_count} 个文件, 跳过 {skipped_count} 个文件")

def archive_views():
    """归档views目录文件"""
    archive_dir = PROJECT_DIR / 'archive' / 'views'
    
    moved_count = 0
    
    for category, files in VIEWS_ARCHIVE_MAP.items():
        dest_dir = archive_dir / category
        
        for filepath in files:
            src_path = PROJECT_DIR / filepath
            
            if src_path.exists():
                dest_path = dest_dir / src_path.name
                shutil.move(str(src_path), str(dest_path))
                print(f"📦 移动: {filepath} -> views/{category}/")
                moved_count += 1
            else:
                print(f"⚠️ 文件不存在: {filepath}")
    
    print(f"\n📊 views目录归档完成: 移动 {moved_count} 个文件")

def cleanup_pycache():
    """清理Python缓存文件"""
    pycache_count = 0
    pyc_count = 0
    
    for root, dirs, files in os.walk(PROJECT_DIR):
        # 删除__pycache__目录
        if '__pycache__' in dirs:
            pycache_dir = os.path.join(root, '__pycache__')
            shutil.rmtree(pycache_dir)
            print(f"🗑️ 删除目录: {pycache_dir}")
            pycache_count += 1
        
        # 删除.pyc文件
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = os.path.join(root, file)
                os.remove(pyc_path)
                print(f"🗑️ 删除文件: {pyc_path}")
                pyc_count += 1
    
    print(f"\n📊 缓存清理完成: 删除 {pycache_count} 个 __pycache__ 目录, {pyc_count} 个 .pyc 文件")

def create_archive_readme():
    """创建归档说明文档"""
    readme_content = f"""# 归档目录说明

**归档日期**: {os.path.getctime(str(PROJECT_DIR / 'archive'))}

## 归档内容

### scripts/
- 公式计算旧版本: 15个脚本（diagnose_material_calc_v1-v4等）
- 检查脚本: 9个脚本
- 添加字段脚本: 5个脚本
- 分析脚本: 3个脚本
- 验证脚本: 4个脚本
- 调试脚本: 3个脚本
- 测试脚本: 3个脚本
- 获取保存脚本: 5个脚本
- 修复脚本: 2个脚本
- 其他脚本: 3个脚本

### views/
- orders备份: 1个备份文件
- dashboard旧版本: 3个旧版本模板

## 保留文件

### scripts/目录保留的20个脚本:
1. order_archive_manager.py - 订单归档管理器
2. order_cli.py - 订单命令行工具
3. unarchive_order.py - 取消归档脚本
4. sync_orders.py - 订单数据同步
5. sync_process_rules.py - 工序规则同步
6. diagnose_material_calc_v5.py - 物料计算诊断
7. fix_formula_variables_v2.py - 公式变量修复
8. check_all_rules.py - 规则检查
9. check_quality_rules.py - 质检规则检查
10. check_all_orders.py - 订单检查
11. check_prod_status.py - 生产状态检查
12. check_formula.py - 弹簧网公式检查
13. save_all_rules.py - 规则导出
14. check_all_prod_status.py - 生产状态检查
15. check_tables.py - 表结构检查
16. test_order_functions.py - 订单功能测试
17. __init__.py - 包初始化文件
18. check_archive_logic.py - 归档逻辑检查
19. check_archive_filter.py - 归档过滤检查
20. check_db_formula.py - 数据库公式检查

## 清理内容

- 所有 __pycache__ 目录
- 所有 .pyc 文件

## 注意事项

归档文件保留期限建议为3个月，之后可根据需要删除。
"""
    readme_path = PROJECT_DIR / 'archive' / 'README.md'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"\n📝 创建归档说明: archive/README.md")

def main():
    print("=" * 60)
    print("文件归档脚本")
    print("=" * 60)
    print()
    
    # 归档scripts目录
    print("--- 1/3 归档scripts目录 ---")
    archive_scripts()
    print()
    
    # 归档views目录
    print("--- 2/3 归档views目录 ---")
    archive_views()
    print()
    
    # 清理缓存
    print("--- 3/3 清理Python缓存 ---")
    cleanup_pycache()
    print()
    
    # 创建说明文档
    create_archive_readme()
    print()
    
    print("=" * 60)
    print("归档完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
