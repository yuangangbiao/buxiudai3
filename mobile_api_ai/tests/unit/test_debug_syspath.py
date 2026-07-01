import sys, os
import pytest

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
app = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def test_syspath_order():
    lines = []
    for i, p in enumerate(sys.path):
        try:
            is_root = os.path.exists(p) and os.path.samefile(p, root)
        except (FileNotFoundError, OSError):
            is_root = False
        label = '<<< ROOT' if is_root else ('<<< APP' if p == app else '')
        lines.append(f'  [{i}] {p} {label}')
    result = '\n'.join(lines)
    print(f'\nROOT={root}\nAPP={app}\n' + result)
    import constants
    print(f'\nconstants from: {constants.__file__}')
    assert hasattr(constants, 'OrderStatus'), f'Missing OrderStatus in {constants.__file__}'
