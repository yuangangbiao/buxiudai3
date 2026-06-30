with open('tests/unit/core/test_error_codes_complete.py', 'rb') as f:
    data = f.read()
text = data.decode('utf-8')
import re

# Find all triple-double-quote occurrences
triple_double = list(re.finditer(r'"""', text))
print(f'Triple-double quote occurrences: {len(triple_double)}')
for m in triple_double:
    line = text[:m.start()].count('\n') + 1
    print(f'  Line {line}, pos {m.start()}')

# Find all triple-single-quote occurrences
triple_single = list(re.finditer(r"'''", text))
print(f'Triple-single quote occurrences: {len(triple_single)}')
for m in triple_single:
    line = text[:m.start()].count('\n') + 1
    print(f'  Line {line}, pos {m.start()}')

# Show lines 265-290
lines = text.split('\n')
print("\nLines 265-290:")
for i in range(264, min(290, len(lines))):
    print(f'{i+1}: {lines[i]!r}')
