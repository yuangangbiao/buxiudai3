#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查所有 Python 文件的括号/符号配对完整性"""
import os
import tokenize
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCLUDE_DIRS = {'云端更新包', '云端更新包_v1.0', '云端更新包_v1.1', '云端部署包', '__pycache__', '.git'}

PAIRS = {
    '(': ')', '[': ']', '{': '}',
}
OPENING = set(PAIRS.keys())
CLOSING = set(PAIRS.values())


def check_file(filepath):
    """使用 tokenize 逐 token 检查括号配对"""
    errors = []
    try:
        with open(filepath, 'rb') as f:
            tokens = list(tokenize.tokenize(f.readline))
    except Exception as e:
        return [(0, f'无法 tokenize: {e}')]

    stack = []
    for tok in tokens:
        if tok.type in (tokenize.ENDMARKER, tokenize.COMMENT, tokenize.STRING):
            continue
        if tok.type not in (tokenize.OP,):
            continue

        for ch in tok.string:
            if ch in OPENING:
                stack.append((ch, tok.start[0], tok.start[1]))
            elif ch in CLOSING:
                if not stack:
                    errors.append((tok.start[0], f'多余的闭合符号 "{ch}"'))
                else:
                    expected = PAIRS[stack[-1][0]]
                    if ch != expected:
                        open_ch, open_line, open_col = stack.pop()
                        errors.append((tok.start[0], f'符号不匹配: 第{open_line}行 "{open_ch}" 与 第{tok.start[0]}行 "{ch}" 不配对'))
                    else:
                        stack.pop()

    for ch, line, col in stack:
        expected = PAIRS[ch]
        errors.append((line, f'未闭合的符号 "{ch}" (期待 "{expected}")'))

    return errors


def check_triple_quotes_via_tokenize(filepath):
    """使用 tokenize 准确检查三引号是否成对"""
    errors = []
    try:
        with open(filepath, 'rb') as f:
            tokens = list(tokenize.tokenize(f.readline))
    except Exception as e:
        return []

    triple_double = 0
    triple_single = 0

    for tok in tokens:
        if tok.type == tokenize.STRING:
            raw = tok.string
            if raw.startswith(('"""', 'f"""', 'b"""', 'r"""')):
                if raw.endswith('"""'):
                    triple_double += 1
                else:
                    triple_double += 0.5
            elif raw.startswith(("'''", "f'''", "b'''", "r'''")):
                if raw.endswith("'''"):
                    triple_single += 1
                else:
                    triple_single += 0.5

    if int(triple_double) != triple_double:
        errors.append((0, '""" 三引号字符串未完整闭合'))
    if int(triple_single) != triple_single:
        errors.append((0, "''' 三引号字符串未完整闭合"))

    return errors


def main():
    all_errors = []
    checked = 0

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if not f.endswith('.py'):
                continue
            filepath = os.path.join(root, f)
            relpath = os.path.relpath(filepath, BASE_DIR)
            checked += 1

            errs = check_file(filepath)
            errs += check_triple_quotes_via_tokenize(filepath)

            if errs:
                all_errors.append((relpath, errs))

    print(f'已检查 {checked} 个文件\n')
    if not all_errors:
        print('全部通过 :) 括号/符号配对完美')
        return

    print(f'发现 {len(all_errors)} 个文件存在问题:\n')
    for path, errs in all_errors:
        print(f'  [{path}]')
        for line, msg in errs:
            loc = f' 第{line}行' if line else ''
            print(f'    {loc} {msg}')
        print()

    total_issues = sum(len(errs) for _, errs in all_errors)
    print(f'总计: {total_issues} 个问题')
    sys.exit(1)


if __name__ == '__main__':
    main()
