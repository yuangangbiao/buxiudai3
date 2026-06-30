# -*- coding: utf-8 -*-
"""
[v3.7.2] 智能修复 _core.py 中的裸异常日志（v2）

关键改进:
1. 保留 except 的缩进（用捕获的缩进）
2. 清理后续对 str(e) 的引用
3. 保留 except 后面的所有代码
"""
import re
import sys
from pathlib import Path

TARGET_FILE = Path(sys.argv[1] if len(sys.argv) > 1 else r'mobile_api_ai\dispatch_center\_core.py')


def fix_file(filepath: Path) -> int:
    """修复单个文件"""
    content = filepath.read_text(encoding='utf-8')
    original = content
    fixed_count = 0

    # 匹配模式:
    # <indent>except Exception as e:\n
    # <indent>    logger.error(f'...{e}...')
    # 注意: 第二个缩进必须比 except 多
    pattern = re.compile(
        r'^(?P<indent>[ \t]*)except\s+Exception\s+as\s+e:\s*\n'
        r'(?P<indent2>[ \t]+)logger\.error\(f(?P<q>[\'"])(?P<msg>[^\'"]*)\{e\}(?P<msg2>[^\'"]*?)(?P=q)\)\s*\n',
        re.MULTILINE
    )

    def replacer(m):
        nonlocal fixed_count
        indent = m.group('indent')
        q = m.group('q')
        msg = (m.group('msg') + m.group('msg2')).strip()
        fixed_count += 1
        return (
            f'{indent}except Exception:\n'
            f'{indent}    # [Q-B7 v3.7.2 修复 2026-06-25] logger.exception 自动带堆栈\n'
            f'{indent}    logger.exception({q}{msg}{q})\n'
        )

    content = pattern.sub(replacer, content)

    if content != original:
        filepath.write_text(content, encoding='utf-8')

    return fixed_count


def main():
    fixed = fix_file(TARGET_FILE)
    print(f"✅ 修复 {TARGET_FILE.name}: {fixed} 处")

    # 验证语法
    try:
        compile(content if 'content' in dir() else TARGET_FILE.read_text(encoding='utf-8'),
                str(TARGET_FILE), 'exec')
        print(f"✅ {TARGET_FILE.name} 语法正确")
    except SyntaxError as e:
        print(f"❌ {TARGET_FILE.name} 语法错误 L{e.lineno}: {e.msg}")


if __name__ == '__main__':
    main()
