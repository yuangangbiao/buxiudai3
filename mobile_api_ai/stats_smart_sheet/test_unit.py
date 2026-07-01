# -*- coding: utf-8 -*-
"""
单元测试运行脚本（mock 模式，无需真实数据库）

用法：
    python test_unit.py                    # 运行全部测试
    python test_unit.py -v                 # 详细输出
    python test_unit.py TestProductionLines  # 只跑特定测试类
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest

# 导入测试模块
from stats_smart_sheet.tests import test_stats_smart_sheet

# 构建测试套件
loader = unittest.TestLoader()
suite = unittest.TestSuite()

# 按优先级加载测试类
test_classes = [
    test_stats_smart_sheet.TestProductionLines,     # C-2.6 产线映射
    test_stats_smart_sheet.TestComputeHash,          # 哈希函数
    test_stats_smart_sheet.TestFieldMapping,         # 字段映射
    test_stats_smart_sheet.TestConfigIntegrity,      # 配置完整性
    test_stats_smart_sheet.TestConcurrencyControl,   # H-5 并发控制
    test_stats_smart_sheet.TestPushWithRetry,        # H-4 重试机制
    test_stats_smart_sheet.TestDBQueries,            # SQL 查询
]

for cls in test_classes:
    suite.addTests(loader.loadTestsFromTestCase(cls))

# 运行
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# 输出摘要
print()
print("=" * 60)
print("测试摘要")
print("=" * 60)
print(f"  运行: {result.testsRun}")
print(f"  成功: {result.testsRun - len(result.failures) - len(result.errors)}")
print(f"  失败: {len(result.failures)}")
print(f"  错误: {len(result.errors)}")

if result.wasSuccessful():
    print()
    print("✅ 全部测试通过！模块质量合格。")
else:
    print()
    print("❌ 有测试失败，请检查上述输出。")
    for test, trace in result.failures + result.errors:
        print(f"\n--- 失败: {test} ---")
        print(trace)

sys.exit(0 if result.wasSuccessful() else 1)
