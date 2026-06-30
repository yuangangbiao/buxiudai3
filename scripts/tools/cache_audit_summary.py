import json
data = json.load(open(r'd:/yuan/不锈钢网带跟单3.0/scripts/tools/cache_audit_report.json', encoding='utf-8'))
results = data['results']
print('====== 缓存覆盖率统计 ======')
total = data['total']
cached = sum(1 for r in results if r['cache_used'])
cacheable_no = sum(1 for r in results if r['category']=='cacheable_get' and not r['cache_used'])
print('扫描接口总数:', total)
print('已用缓存:', cached, '({}%)'.format(cached*100//max(total,1)))
print('可缓存但未缓存:', cacheable_no)
print()
print('====== 主要文件（>=3 路由）======')
by_file = {}
for r in results:
    f = r['file']
    by_file.setdefault(f, {'total': 0, 'cached': 0, 'cacheable_no_cache': 0})
    by_file[f]['total'] += 1
    if r['cache_used']:
        by_file[f]['cached'] += 1
    elif r['category'] == 'cacheable_get':
        by_file[f]['cacheable_no_cache'] += 1
for f, s in sorted(by_file.items()):
    if s['total'] >= 3:
        print('{:60s} {:>3}/{:<3} (可缓存未用: {})'.format(f, s['cached'], s['total'], s['cacheable_no_cache']))

print()
print('====== 高优先级: Top 10 应缓存但未缓存的接口 ======')
items = [r for r in results if r['category']=='cacheable_get' and not r['cache_used']]
for r in items[:10]:
    print('  {}:{} {} {}'.format(r['file'], r['line'], '/'.join(r['methods']), r['rule']))
