"""提取 dispatch_center.html 中的 CSS/JS 到 static/ 目录"""
import re, os

html_path = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\templates\dispatch_center.html'
static_dir = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\static'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()
    lines = html.split('\n')

print(f'总行数: {len(lines)}')

# 1. 提取 CSS (lines 7-168, 不含<style>标签)
css_start = 7   # 0-indexed: line 8
css_end = 168   # 0-indexed: line 169
css_content = '\n'.join(lines[css_start:css_end])

os.makedirs(os.path.join(static_dir, 'css'), exist_ok=True)
css_path = os.path.join(static_dir, 'css', 'dispatch_center.css')
with open(css_path, 'w', encoding='utf-8') as f:
    f.write(css_content)
print(f'CSS 已提取: {css_path} ({len(css_content)} chars)')

# 2. 提取 JS (lines 710-3005, 不含<script>标签)
js_start = 710   # 0-indexed: line 711
js_end = 3005     # 0-indexed: line 3006
js_content = '\n'.join(lines[js_start:js_end])

# 修复硬编码 IP: http://124.223.57.82:5003 替换为相对路径
# route mapping:
#   /api/dispatch/repair-*  → /api/dispatch-center/repair-*
#   /api/dispatch-center/*  → /api/dispatch-center/*
count_before = js_content.count('124.223.57.82')
js_content = js_content.replace(
    'http://124.223.57.82:5003/api/dispatch/repair-categories',
    '/api/dispatch-center/repair-categories'
)
js_content = js_content.replace(
    'http://124.223.57.82:5003/api/dispatch/repair-records',
    '/api/dispatch-center/repair-records'
)
js_content = js_content.replace(
    'http://124.223.57.82:5003/api/dispatch-center/outsource-records',
    '/api/dispatch-center/outsource-records'
)
js_content = js_content.replace(
    'http://124.223.57.82:5003/api/dispatch-center/outsource-config',
    '/api/dispatch-center/outsource-config'
)
count_after = js_content.count('124.223.57.82')
print(f'硬编码 IP 替换: {count_before} -> {count_after} 处')

os.makedirs(os.path.join(static_dir, 'js'), exist_ok=True)
js_path = os.path.join(static_dir, 'js', 'dispatch_center.js')
with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content)
print(f'JS 已提取: {js_path} ({len(js_content)} chars)')

# 3. 输出替换后的 HTML
# 保留: <!DOCTYPE html>...<head>...<style>替换为<link>...  </head><body>HTML...</body></html>
new_html_lines = []

in_style = False
in_script = False
for i, line in enumerate(lines):
    stripped = line.strip()

    # 跳过 <style> 到 </style> 之间的内容
    if stripped.startswith('<style>'):
        in_style = True
        new_html_lines.append(line.replace('<style>',
            '<link rel="stylesheet" href="/static/css/dispatch_center.css">'))
        continue
    if in_style and stripped == '</style>':
        in_style = False
        continue
    if in_style:
        continue

    # 跳过 <script> 到 </script> 之间的内容
    if stripped.startswith('<script>'):
        in_script = True
        # 添加 defer script 引用和 base URL 配置
        new_html_lines.append('  <script>window.API_BASE = window.API_BASE || "";</script>')
        new_html_lines.append('  <script src="/static/js/dispatch_center.js" defer></script>')
        continue
    if in_script and stripped == '</script>':
        in_script = False
        continue
    if in_script:
        continue

    new_html_lines.append(line)

new_html = '\n'.join(new_html_lines)

html_out_path = html_path  # 直接覆写原文件
with open(html_out_path, 'w', encoding='utf-8') as f:
    f.write(new_html)
print(f'HTML 已更新: {html_out_path} ({len(new_html_lines)} lines)')

print('\n=== DONE ===')
