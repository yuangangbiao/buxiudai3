"""Check type annotation coverage for project Python files."""
import ast
import os
import sys
from pathlib import Path


def get_annotation_coverage(filepath: str) -> float:
    """Calculate the percentage of functions with type annotations."""
    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    functions = [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    if not functions:
        return 100.0

    annotated = 0
    for func in functions:
        has_return = func.returns is not None
        has_args = any(a.arg.annotation for a in func.args.args if a.arg != 'self')
        if has_return or has_args:
            annotated += 1

    return annotated / len(functions) * 100


def main():
    threshold = float(os.getenv('ANNOTATION_THRESHOLD', '50'))
    exclude_dirs = {'tests', '.venv', 'venv', '__pycache__', 'node_modules', '.git'}
    exclude_suffixes = {'_pb2.py', '_pb2_grpc.py'}

    failed = []

    for pyfile in sorted(Path('.').rglob('*.py')):
        parts = set(pyfile.parts)
        if parts & exclude_dirs:
            continue
        if any(pyfile.name.endswith(s) for s in exclude_suffixes):
            continue

        rate = get_annotation_coverage(str(pyfile))
        if rate < threshold:
            failed.append((pyfile, rate))

    if failed:
        for f, r in failed:
            print(f'FAIL: {f}: {r:.1f}% (threshold={threshold}%)')
        print(f'\nSummary: {len(failed)} file(s) below threshold')
        sys.exit(1)

    print(f'OK: All files meet annotation coverage threshold={threshold}%')


if __name__ == '__main__':
    main()
