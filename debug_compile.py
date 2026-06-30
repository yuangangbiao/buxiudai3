# -*- coding: utf-8 -*-
with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'r', encoding='utf-8') as f:
    code = f.read()
lines = code.split('\n')
snippet = '\n'.join(lines[7889:7906])
print("Snippet (lines 7890-7906):")
print(repr(snippet))
print("\nCompiling snippet:")
try:
    compile(snippet, '<snippet>', 'exec')
    print("OK")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    snippet_lines = snippet.split('\n')
    print(f"Content at error: {repr(snippet_lines[e.lineno-1])}")
