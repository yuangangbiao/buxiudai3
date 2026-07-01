import ast
with open('dispatch_center.py', 'r', encoding='utf-8') as f:
    ast.parse(f.read())
print('[OK] dispatch_center.py')
