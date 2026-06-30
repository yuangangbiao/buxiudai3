"""直接运行 test_required_raises_on_none"""
import sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')

import pytest

result = pytest.main([
    '-xvs',
    'tests/unit/utils/test_validators.py::test_required_raises_on_none',
    '--tb=long',
    '-p', 'no:cacheprovider',
])
print(f"Exit: {result}")
