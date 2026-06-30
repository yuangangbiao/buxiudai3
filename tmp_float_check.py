import math
tests = [
    "abc", "123", "nan", "NaN", "inf", "-inf",
    "not_a_number", "N/A", "None", "null", "undefined"
]
for t in tests:
    try:
        r = float(t)
        print(f"float({t!r}) = {r}, isnan={math.isnan(r) if r != r else False}")
    except ValueError as e:
        print(f"float({t!r}) -> ValueError: {e}")
