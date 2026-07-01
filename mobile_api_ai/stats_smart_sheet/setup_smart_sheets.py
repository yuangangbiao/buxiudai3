# -*- coding: utf-8 -*-
"""
智能表格创建指南 + TABLE_INDEX.json 填入脚本

使用方法：
1. 先在企业微信手动创建 9 个智能表格（或用 API 创建）
2. 填入每个表格的 docid 和 sheet_id
3. 运行本脚本生成 TABLE_INDEX.json

注意：智能表格创建需要企业微信管理员权限，
在企业微信后台 https://work.weixin.qq.com/ 创建。
"""
import json
import os
import re
from pathlib import Path

# 9 张表的展示名
TABLES = [
    ('production_daily_report',    '工单-生产日报'),
    ('production_monthly_report',  '工单-生产月报'),
    ('workshop_capacity',           '工单-车间产能分析'),
    ('workorder_progress',         '工单-工单进度跟踪'),
    ('substep_report',             '工单-工序报工汇总'),
    ('inventory_weekly_report',     '库存-库存周报'),
    ('inventory_monthly_summary',   '库存-物料收发存汇总'),
    ('inventory_alert',            '库存-库存预警'),
    ('inventory_slow_moving',      '库存-呆滞料分析'),
]


def print_guide():
    """打印创建指南"""
    print("=" * 70)
    print("企业微信智能表格创建指南")
    print("=" * 70)
    print()
    for table_key, display_name in TABLES:
        print(f"📋 [{display_name}]")
        print(f"   docid:  待填入（在企业微信表格 URL 中可见）")
        print(f"   sheet_id: 待填入（创建后获取）")
        print()
    print("=" * 70)
    print("获取方法：")
    print("1. 打开企业微信 → 工作台 → 智能表格")
    print("2. 创建新表格，命名如【生产日报-跟单系统】")
    print("3. 打开表格，URL 类似: https://work.weixin.qq.com/wework_admin/smartsheet/XXXXX")
    print("   XXXXX 就是 docid")
    print("4. 进入表格 → 右上角「...」→「获取表格链接」可看到 sheet_id")
    print("=" * 70)


def interactive_fill():
    """交互式填入 docid/sheet_id"""
    print()
    print("=" * 70)
    print("交互式填入 docid/sheet_id")
    print("=" * 70)
    index = {}
    for table_key, display_name in TABLES:
        print(f"\n📋 {display_name} ({table_key})")
        docid = input("  docid: ").strip()
        sheet_id = input("  sheet_id: ").strip()
        url = input("  表格URL（可选）: ").strip()

        if not docid:
            print("  ⚠️  跳过（未填入）")
            continue

        entry = {'docid': docid, 'sheet_id': sheet_id or docid}
        if url:
            entry['url'] = url
        index[table_key] = entry
        print(f"  ✅ 已记录")

    return index


def generate_json(index: dict) -> str:
    """生成 TABLE_INDEX.json 内容"""
    return json.dumps(index, ensure_ascii=False, indent=2)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='智能表格 docid/sheet_id 填入工具')
    parser.add_argument('--guide', action='store_true', help='仅打印创建指南')
    parser.add_argument('--fill', action='store_true', help='交互式填入')
    parser.add_argument('--output', default='TABLE_INDEX.json', help='输出文件路径')
    parser.add_argument('--input', help='从已有 JSON 文件读取并更新')
    args = parser.parse_args()

    if args.guide:
        print_guide()
        return

    # 读取已有配置（增量更新）
    index = {}
    if args.input and os.path.exists(args.input):
        with open(args.input, encoding='utf-8') as f:
            index = json.load(f)
        print(f"✅ 已从 {args.input} 加载 {len(index)} 条配置")

    if args.fill:
        new_entries = interactive_fill()
        index.update(new_entries)
        print(f"\n✅ 共 {len(index)} 张表已配置")

    # 生成输出
    if index:
        output_path = os.path.join(
            os.path.dirname(__file__), '..', args.output
        )
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(generate_json(index))
        print(f"✅ 已写入 {output_path}")
        print()
        print(generate_json(index))
    else:
        print_guide()


if __name__ == '__main__':
    main()
