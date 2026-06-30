# -*- coding: utf-8 -*-
"""
用原生 coverage API 执行 operator 的完整测试并输出准确覆盖率。
绕过 pytest-cov 的 import 时序问题。
"""
import coverage
cov = coverage.Coverage(source=["models"])
cov.start()

# 现在 import — coverage 已经启动
from models.operator import OperatorDAO, OperatorLogDAO

# 手动执行两个测试文件的所有逻辑
from tests.unit.models.test_operator import *
from tests.unit.models.test_operator_depth import *

# 收集覆盖率
cov.stop()
cov.save()
total = cov.report(["models/operator.py"], show_missing=True)
print(f"\n=== OPERATOR TOTAL: {total:.1f}% ===")
