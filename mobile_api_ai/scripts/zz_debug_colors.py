import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import COLORS
print(f"DATA_TYPE_REPORT in COLORS: {'DATA_TYPE_REPORT' in COLORS}")
print(f"COLORS keys: {list(COLORS.keys())}")
print(f"COLORS length: {len(COLORS)}")
if 'DATA_TYPE_REPORT' in COLORS:
    print(f"DATA_TYPE_REPORT value: {COLORS['DATA_TYPE_REPORT']}")
