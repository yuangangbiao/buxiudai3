# -*- coding: utf-8 -*-
"""解析 coverage.xml 并输出详细覆盖率报告"""

import xml.etree.ElementTree as ET
from collections import defaultdict

tree = ET.parse('coverage.xml')
root = tree.getroot()

total_stmts = int(root.get('lines-valid', 0))
total_covered = int(root.get('lines-covered', 0))
total_rate = float(root.get('line-rate', 0)) * 100
total_uncovered = total_stmts - total_covered

# 已知的 package → source 映射
# coverage.py 的 source 列表依次对应 4 个 source 目录
# package '.' 中的 filename 不带前缀，来自第一个 source (core/)
# package 'database' 中的 filename 以 database/ 为前缀，来自 models/
# package 'storage' 中的 filename 以 storage/ 为前缀，来自 utils/
# package 'validation' 中的 filename 以 validation/ 为前缀，来自 utils/
PKG_PREFIX_MAP = {
    '.': 'core/',
    'database': 'models/',
    'storage': 'utils/',
    'validation': 'utils/',
    'services': 'services/',
}

modules = []

for pkg in root.findall('.//package'):
    pkg_name = pkg.get('name')
    prefix = PKG_PREFIX_MAP.get(pkg_name, '')
    for cls in pkg.findall('classes/class'):
        fn = cls.get('filename')
        full = prefix + fn
        # <class> 没有 lines-valid / lines-covered 属性
        # 必须从 <lines> > <line> 子元素中统计
        all_lines = cls.findall('lines/line')
        covered_lines = [l for l in all_lines if l.get('hits') == '1']
        stmts = len(all_lines)
        covered = len(covered_lines)
        if stmts > 0:
            rate = covered / stmts * 100
            modules.append((full, stmts, covered, rate))

modules.sort(key=lambda x: x[3])

need_90 = int(total_stmts * 0.9 - total_covered)

print(f'{'='*80}')
print(f'  覆盖率分析报告')
print(f'  {"总模块数:":>16} {len(modules)}')
print(f'  {"总语句数:":>16} {total_stmts}')
print(f'  {"已覆盖:":>16} {total_covered}')
print(f'  {"未覆盖:":>16} {total_uncovered}')
print(f'  {"总覆盖率:":>16} {total_rate:.2f}%')
print(f'  {"目标90%需覆盖:":>16} {need_90} 行')
print(f'{'='*80}')

# ============================================================
# 1. 按覆盖率排序（全部模块）
# ============================================================
print()
print('─' * 80)
print('1. 覆盖率最低的模块（全部）')
print('─' * 80)
print(f'{"覆盖率":>7} {"语句":>5} {"未覆盖":>5}  文件')
print('─' * 80)
for fn, stmts, covered, rate in modules:
    print(f'{rate:6.2f}% | {stmts:4d} | {stmts-covered:4d} | {fn}')

# ============================================================
# 2. 按目录分组统计
# ============================================================
print()
print('─' * 80)
print('2. 按目录分组统计')
print('─' * 80)
dirs = defaultdict(lambda: {'stmts': 0, 'covered': 0, 'files': 0})
for fn, stmts, covered, rate in modules:
    parts = fn.split('/')
    top = parts[0] if len(parts) > 1 else '(root)'
    dirs[top]['stmts'] += stmts
    dirs[top]['covered'] += covered
    dirs[top]['files'] += 1

print(f'{"覆盖率":>7} {"目录":<22} {"语句":>6} {"未覆盖":>6} {"文件数":>5}')
print('─' * 80)
sorted_dirs = sorted(dirs.keys(), key=lambda k: dirs[k]['covered'] / dirs[k]['stmts'] if dirs[k]['stmts'] > 0 else 0)
for d in sorted_dirs:
    s = dirs[d]
    r = s['covered'] / s['stmts'] * 100 if s['stmts'] > 0 else 0
    print(f'{r:6.2f}% | {d:<22} | {s["stmts"]:5d} | {s["stmts"]-s["covered"]:5d} | {s["files"]:5d}')
print(f'{"":6s} | {"总计":<22} | {total_stmts:5d} | {total_uncovered:5d} | {len(modules):5d}')

# ============================================================
# 3. 高性价比目标
# ============================================================
print()
print('─' * 80)
print('3. 高性价比目标（文件小且覆盖率低 → 单位语句提升最大）')
print('─' * 80)
print(f'{"性价比":>7} {"覆盖率":>7} {"语句":>5} {"未覆盖":>5}  文件')
print('─' * 80)
scored = []
for fn, stmts, covered, rate in modules:
    if stmts <= 3:
        continue
    # 性价比 = (100 - 当前覆盖率) / 语句数，即覆盖该文件每行能提升的百分比点数
    efficiency = (100 - rate) / stmts if stmts > 0 else 0
    scored.append((efficiency, fn, stmts, covered, rate))
scored.sort(key=lambda x: -x[0])
for eff, fn, stmts, covered, rate in scored[:80]:
    print(f'{eff:6.3f}% | {rate:6.2f}% | {stmts:4d} | {stmts-covered:4d} | {fn}')

# ============================================================
# 4. 达到 90% 覆盖率的路线图
# ============================================================
target_90 = int(total_stmts * 0.9)
need_cover_90 = target_90 - total_covered

print()
print('═' * 80)
print(f'4. 达到 90% 覆盖率路线图')
print(f'   目标: {target_90}/{total_stmts} 行覆盖')
print(f'   当前: {total_covered} 行覆盖')
print(f'   缺口: {need_cover_90} 行')
print('═' * 80)

# 4a. 覆盖率 0% 的模块
zero_modules = sorted([m for m in modules if m[3] == 0], key=lambda x: -x[1])
zero_total = sum(m[1] for m in zero_modules)
print(f'\n  覆盖率 0% 的模块: {len(zero_modules)} 个, 共 {zero_total} 行')
for fn, stmts, covered, rate in zero_modules:
    print(f'    {rate:6.2f}% | {stmts:4d} 行 | {fn}')

# 4b. 覆盖率 0-30% 的模块（不含0%）
low_modules = sorted([m for m in modules if 0 < m[3] < 30], key=lambda x: x[3])
low_total = sum(m[1] for m in low_modules)
print(f'\n  覆盖率 0-30% 的模块: {len(low_modules)} 个, 共 {low_total} 行')
for fn, stmts, covered, rate in low_modules:
    print(f'    {rate:6.2f}% | {stmts:4d} 行 | {fn}')

# 4c. 覆盖率 30-70% 的模块（次优目标）
mid_modules = sorted([m for m in modules if 30 <= m[3] < 70], key=lambda x: x[3])
mid_total = sum(m[1] for m in mid_modules)
print(f'\n  覆盖率 30-70% 的模块: {len(mid_modules)} 个, 共 {mid_total} 行')
for fn, stmts, covered, rate in mid_modules:
    print(f'    {rate:6.2f}% | {stmts:4d} 行 | {fn}')

# 4d. 覆盖率 70%+ 的模块（最后冲刺）
high_modules = sorted([m for m in modules if 70 <= m[3] < 100], key=lambda x: x[3])
high_total = sum(m[1] for m in high_modules)
print(f'\n  覆盖率 70-99% 的模块: {len(high_modules)} 个, 共 {high_total} 行')
for fn, stmts, covered, rate in high_modules:
    print(f'    {rate:6.2f}% | {stmts:4d} 行 | {fn}')

# 4e. 覆盖率 100% 的模块
hundred_modules = [m for m in modules if m[3] == 100]
print(f'\n  覆盖率 100% 的模块: {len(hundred_modules)} 个')

# ============================================================
# 5. 评估与建议
# ============================================================
print()
print('═' * 80)
print('5. 策略评估')
print('═' * 80)

# 阶段1：覆盖0%模块
covered_if_zero = zero_total
rate_after_zero = (total_covered + covered_if_zero) / total_stmts * 100
print(f'\n  Phase 1: 覆盖所有 0% 模块')
print(f'    +{covered_if_zero} 行 → 覆盖率 {rate_after_zero:.2f}%')
print(f'    目标差距: {need_cover_90 - covered_if_zero} 行仍缺')

# 阶段2：覆盖0% + 0-30%模块
covered_if_low = zero_total + low_total
rate_after_low = (total_covered + covered_if_low) / total_stmts * 100
print(f'\n  Phase 2: 覆盖所有 0% + 0-30% 模块')
print(f'    +{covered_if_low} 行 → 覆盖率 {rate_after_low:.2f}%')
print(f'    目标差距: {max(0, need_cover_90 - covered_if_low)} 行仍缺')

# 阶段3：覆盖0% + 0-30% + 部分30-70%模块
print(f'\n  Phase 3: 继续覆盖 30-70% 模块到 90%+')
print(f'    仍需 {need_cover_90 - covered_if_low} 行')
print(f'    30-70% 模块共 {mid_total} 行可覆盖')
