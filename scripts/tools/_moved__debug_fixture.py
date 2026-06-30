"""Debug test for mock_get_connection fixture"""
import sys, os
_proj = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _proj)

try:
    from tests.unit.conftest import mock_get_connection
except (ImportError, TypeError):
    for _k in list(sys.modules.keys()):
        if _k.startswith('tests.') or _k.startswith('mobile_api_ai.tests.'):
            sys.modules.pop(_k, None)
    import tests.unit.conftest as _c
    mock_get_connection = _c.mock_get_connection

from unittest.mock import MagicMock, patch


class FakeMonkeypatch:
    def setattr(self, path, fn):
        import importlib
        parts = path.rsplit('.', 1)
        mod = importlib.import_module(parts[0])
        setattr(mod, parts[1], fn)


def test_debug():
    mp = FakeMonkeypatch()
    fixture = mock_get_connection(mp)
    print(f"Fixture created: {fixture}")
    mock_patch = fixture("utils.process_templates.get_connection")
    print(f"mock_patch: {mock_patch}")
    from utils.process_templates import delete_process_template
    result = delete_process_template("test_template")
    print(f"delete_process_template result: {result}")
    mock_conn = mock_patch.return_value
    print(f"mock_conn.commit.called: {mock_conn.commit.called}")
    assert mock_conn.commit.called, "delete_process_template should have called commit"
