# -*- coding: utf-8 -*-
"""分析 Tab HTML 内容区的 API 调用，确定 JS 函数归属"""
import re

with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\templates\dispatch_center.html', encoding='utf-8') as f:
    content = f.read()
lines = content.split('\n')

# 24 个 Tab ID 和名称（手动核实，无 false positive）
TABS = [
    'overview', 'operators', 'tasks', 'messages', 'processes', 'rules',
    'process-config', 'monitor', 'cloud', 'repairs', 'outsource',
    'warehousing', 'feedback', 'quality-inspect', 'report-records',
    'quality-regression', 'material-regression', 'outsource-regression',
    'schedule-regression', 'schedule', 'material-dc', 'order-status',
    'system-config', 'sync-queue'
]

# 找每个 tab-content 的起止行
tab_sections = {}
current_tab = None
for i, l in enumerate(lines):
    m = re.search(r'id="tab-([\w-]+)"', l)
    if m:
        current_tab = m.group(1)
        tab_sections[current_tab] = {'start': i+1, 'end': len(lines)}
for tab in tab_sections:
    later = [(t, tab_sections[t]['start']) for t in tab_sections if t != tab and tab_sections[t]['start'] > tab_sections[tab]['start']]
    if later:
        later.sort(key=lambda x: x[1])
        tab_sections[tab]['end'] = later[0][1] - 1

# 统计每个 Tab 的 API 调用
print("Tab 内容区 API 调用分析:")
print(f"{'Tab':<25} {'行范围':<15} {'行数':<6} {'API调用':<6} {'内联样式':<6} {'子div':<6}")
print("-" * 70)
for tab, info in tab_sections.items():
    section = '\n'.join(lines[info['start']-1:info['end']-1])
    api_calls = len(re.findall(r'fetch\(|\.get\(|\.post\(', section))
    inline_styles = len(re.findall(r'style="', section))
    sub_divs = len(re.findall(r'<div', section))
    print(f"{tab:<25} L{info['start']}~L{info['end']:<6} {info['end']-info['start']:<4} {api_calls:<6} {inline_styles:<6} {sub_divs:<6}")

print()
print("总行数分布:")
total_tab_lines = sum(info['end']-info['start'] for info in tab_sections.values())
print(f"  Tab HTML 区域: ~{total_tab_lines} 行 (L47~L1139)")
print(f"  JS 区域: ~776 行 (L1542~L2318)")
print(f"  其他: ~46 行 (头部+侧边栏)")
