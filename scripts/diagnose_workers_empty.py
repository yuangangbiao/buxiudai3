# -*- coding: utf-8 -*-
"""
Workers 表为空原因分析 + 持久化解决方案
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 70)
print("🔍 Workers 表为空原因分析")
print("=" * 70)
print()

# 1. 分析根因
print("=" * 70)
print("1️⃣  根本原因分析")
print("=" * 70)

print("""
问题时间线:
┌────────────────────────────────────────────────────────────────┐
│ 2026-06-10 (F6 P9)                                             │
│   ❌ enterprise_structure 表被 DROP                             │
│   📝 决策: 改用 enterprise_structure.json 替代                  │
│   ⚠️  但 workers 表的填充逻辑未同步更新                         │
├────────────────────────────────────────────────────────────────┤
│ 之后添加操作员时                                                 │
│   📝 _save_operators() 会写入三个地方:                          │
│     1. enterprise_structure.json ✅                             │
│     2. operators.json ✅                                       │
│     3. workers 表 ✅                                           │
│                                                                │
│   但如果 enterprise_structure.json 没有 operators 字段          │
│   登录代码 (container_center_api.py) 无法读取                    │
├────────────────────────────────────────────────────────────────┤
│ 我的修复 (2026-06-15)                                           │
│   ✅ 修改 container_center_api.py                              │
│   ✅ _load_operators_from_workers() 直接从 workers 表读取       │
│   ⚠️  但 workers 表可能为空!                                    │
└────────────────────────────────────────────────────────────────┘

workers 表为空的常见原因:
┌────────────────────────────────────────────────────────────────┐
│ 原因 1: 调度中心添加操作员时 _save_operators() 未被调用        │
│   - 直接编辑 JSON 文件而非通过 UI 添加                          │
│   - 数据库迁移时未同步                                           │
├────────────────────────────────────────────────────────────────┤
│ 原因 2: enterprise_structure.json 缺少 operators 字段          │
│   - 我的修复前, enterprise_structure.json 只有空结构             │
│   - {"departments": [], "users": [], "operators": {}} ❌       │
│   - 需要 {"departments": [...], "users": [...], "operators": {..}} ✅│
├────────────────────────────────────────────────────────────────┤
│ 原因 3: workers 表从未被初始化                                   │
│   - 旧的 container_config.py 可能从未写入 workers 表            │
│   - MySQL 初始化脚本可能未创建该表                              │
└────────────────────────────────────────────────────────────────┘
""")

# 2. 检查当前数据源
print("=" * 70)
print("2️⃣  检查当前数据源")
print("=" * 70)

try:
    # 检查 enterprise_structure.json
    es_file = PROJECT_ROOT / 'mobile_api_ai' / 'data' / 'enterprise_structure.json'
    if es_file.exists():
        with open(es_file, 'r', encoding='utf-8') as f:
            es_data = json.load(f)
        operators = es_data.get('operators', {})
        print(f"\n📄 enterprise_structure.json:")
        print(f"   - 路径: {es_file}")
        print(f"   - operators 字段: {'有 ' + str(len(operators)) + ' 条' if operators else '❌ 缺失或为空'}")

        if operators:
            print("   操作员列表:")
            for op_id, op_info in operators.items():
                name = op_info.get('name', '')
                role = op_info.get('role', '')
                enabled = op_info.get('enabled', True)
                status = '✅' if enabled else '❌'
                print(f"     {status} {op_id}: {name} ({role})")
    else:
        print(f"\n❌ enterprise_structure.json 不存在: {es_file}")

    # 检查 operators.json
    op_file = PROJECT_ROOT / 'operators.json'
    if op_file.exists():
        with open(op_file, 'r', encoding='utf-8') as f:
            op_data = json.load(f)
        print(f"\n📄 operators.json:")
        print(f"   - 路径: {op_file}")
        print(f"   - 操作员数量: {len(op_data)} 条")

        if op_data:
            print("   操作员列表:")
            for op_id, op_info in op_data.items():
                name = op_info.get('name', '')
                role = op_info.get('role', '')
                print(f"     ✅ {op_id}: {name} ({role})")
    else:
        print(f"\n❌ operators.json 不存在: {op_file}")

    # 检查 workers 表
    print(f"\n📄 MySQL workers 表:")
    print("   - 需要运行 check_workers_table.py 查看")

except Exception as e:
    print(f"\n❌ 检查失败: {e}")

# 3. 持久化解决方案
print("\n" + "=" * 70)
print("3️⃣  持久化解决方案")
print("=" * 70)

print("""
方案 A: 通过调度中心添加操作员 (推荐 - 正常途径)
═══════════════════════════════════════════════════════════════════

步骤 1: 访问调度中心
  http://localhost:5003
  → 👥 操作员管理 → + 新增操作员

步骤 2: 重启 5008 服务
  python mobile_api_ai/container_center_api.py

步骤 3: 测试登录
  POST http://localhost:5008/api/auth/login
  {"operator_id": "OP001"}

───────────────────────────────────────────────────────────────────

方案 B: 确保调度中心添加操作员时同步到 workers 表
═══════════════════════════════════════════════════════════════════

当前代码 container_config.py _save_operators() 已经会写入 workers 表:
  ✅ INSERT INTO workers ... ON DUPLICATE KEY UPDATE

只要通过调度中心 UI 添加操作员，数据会自动同步!

───────────────────────────────────────────────────────────────────

方案 C: 修改 _load_operators_from_workers() 读取多个数据源
═══════════════════════════════════════════════════════════════════

如果 workers 表为空，fallback 到 enterprise_structure.json

已在 container_center_api.py 实现:
  1. 优先从 workers 表读取
  2. 如果为空，fallback 到 enterprise_structure.json
""")

# 4. 推荐操作
print("=" * 70)
print("4️⃣  推荐操作步骤")
print("=" * 70)

print("""
当前状态检查结果:
  enterprise_structure.json: 需要确认是否有 operators 字段
  workers 表: 需要运行 check_workers_table.py 确认

推荐立即执行:
═══════════════════════════════════════════════════════════════════

1. 运行诊断脚本 (如已运行可跳过)
   python scripts/check_workers_table.py

2. 如果 workers 表为空，通过调度中心添加操作员
   访问 http://localhost:5003 → 👥 操作员管理 → + 新增操作员

3. 如果 enterprise_structure.json 缺少 operators
   # 编辑文件添加 operators 字段，或
   # 通过调度中心 UI 添加操作员

4. 重启 5008 服务
   python mobile_api_ai/container_center_api.py

5. 测试登录
   POST http://localhost:5008/api/auth/login
   {"operator_id": "OP001"}
""")

print("=" * 70)
print("分析完成")
print("=" * 70)
