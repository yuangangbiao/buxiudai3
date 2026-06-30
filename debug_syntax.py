# -*- coding: utf-8 -*-
import ast

try:
    with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'r', encoding='utf-8') as f:
        code = f.read()
    ast.parse(code)
    print('File parses OK')
except SyntaxError as e:
    print(f'SyntaxError at line {e.lineno}: {e.msg}')
    lines = code.split('\n')
    print(f'Content at that line: {repr(lines[e.lineno-1][:80])}')
    print(f'Previous line: {repr(lines[e.lineno-2][:80])}')
    print(f'Next line: {repr(lines[e.lineno][:80])}')
