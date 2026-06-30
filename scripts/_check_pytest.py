"""检查 pytest 是否可用"""
import sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')
try:
    import pytest
    print(f"pytest version: {pytest.__version__}")
except ImportError:
    print("pytest not found")
