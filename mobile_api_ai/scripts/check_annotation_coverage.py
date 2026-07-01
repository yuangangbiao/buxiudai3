import ast
import sys
from pathlib import Path


def count_functions_with_annotations(source: str):
    tree = ast.parse(source)
    total = 0
    annotated = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total += 1
            has_return = node.returns is not None
            has_params = all(
                arg.annotation is not None
                for arg in node.args.args
                if arg.arg not in ('self', 'cls')
            )
            if has_return and has_params:
                annotated += 1
    return total, annotated


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_annotation_coverage.py <filepath> [--min <threshold>]")
        sys.exit(1)
    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"Error: file not found: {filepath}")
        sys.exit(1)
    min_threshold = None
    if '--min' in sys.argv:
        idx = sys.argv.index('--min')
        if idx + 1 < len(sys.argv):
            min_threshold = float(sys.argv[idx + 1])
    source = filepath.read_text(encoding='utf-8')
    total, annotated = count_functions_with_annotations(source)
    coverage = (annotated / total * 100) if total > 0 else 100.0
    print(f"Total functions: {total}")
    print(f"Annotated functions: {annotated}")
    print(f"Coverage: {coverage:.1f}%")
    if min_threshold is not None and coverage < min_threshold:
        print(f"FAIL: Coverage {coverage:.1f}% < minimum {min_threshold:.1f}%")
        sys.exit(1)
    print("PASS")


if __name__ == '__main__':
    main()
