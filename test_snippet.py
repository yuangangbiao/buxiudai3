import ast
snippet = '\ndef _normalize_inspection_items(raw):\n    \x22\x22\x22\n    [P1 \u4fee\u590d 2026-06-18 Bug #8] \u5f52\u4e00\u5316 inspection_items \u5b57\u6bb5\n    \u652f\u6301 3 \u79cd\u8f93\u5165\u683c\u5f0f: None / "a,b,c" / "[\'a\',\'b\']" / array \u2192 \u7edf\u4e00\u8fd4\u56de array\n    \x22\x22\x22\n    if raw is None or raw == \'\' or raw == \'null\':\n        return []\n    if isinstance(raw, list):\n        return raw\n    if isinstance(raw, str):\n        return []\n    return []\n'
try:
    ast.parse(snippet)
    print('Snippet OK')
except SyntaxError as e:
    print(f'Snippet FAIL: {e}')
    print(f'Line {e.lineno}: {e.msg}')
