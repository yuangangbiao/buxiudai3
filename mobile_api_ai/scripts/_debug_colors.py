import sys, os

# 模拟 dispatch_center.py 的 sys.path 配置
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PARENT_DIR = os.path.dirname(_PROJECT_ROOT)
sys.path.insert(0, _PARENT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from core.config import COLORS
print(f"DATA_TYPE_REPORT in COLORS: {'DATA_TYPE_REPORT' in COLORS}")
keys = list(COLORS.keys())
print(f"COLORS keys (last 8): {keys[-8:]}")
print(f"COLORS total: {len(keys)}")
if 'DATA_TYPE_REPORT' in COLORS:
    print(f"DATA_TYPE_REPORT = {COLORS['DATA_TYPE_REPORT']}")
