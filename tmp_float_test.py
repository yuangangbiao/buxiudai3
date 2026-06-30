import math
print("float('abc'):", float('abc'))
print("float('nan'):", float('nan'))
print("math.isnan(float('nan')):", math.isnan(float('nan')))
try:
    r = float('not_a_number')
    print("float('not_a_number'):", r, "isnan:", math.isnan(r))
except ValueError as e:
    print("ValueError:", e)
