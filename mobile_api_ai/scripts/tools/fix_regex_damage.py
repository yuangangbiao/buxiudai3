import re

fp = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center.py'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

fixes = [
    # Fix 1: line 571 - get_status
    ("_get_client().query__get_cached_work_orders(page=1, size=5000)result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])",
     "result = _get_cached_work_orders(page=1, size=5000)\n        packages = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])"),

    # Fix 2: line 631 - list_tasks
    ("_get_client().query_documents('work_orde_get_cached_work_orders(page=1, size=5000)(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])",
     "_get_cached_work_orders(page=1, size=5000)\n        packages = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])"),

    # Fix 3: lines 1107-1108 - list_devices
    ("packages = _get_client().query_documents('work_order', page=1, size=2000)\n        for pkg i_get_cached_work_orders(page=1, size=2000)           if device_id:",
     "packages = _get_cached_work_orders(page=1, size=2000)\n        for pkg in (packages or []):\n            device_id = pkg.get('device_id', '')\n            if device_id:"),

    # Fix 4: lines 1154-1156 - get_device_tasks
    ("packages = _get_client().query_documents('work_order', page=1, size=2000)\n        for pkg in packages:\n        _get_cached_work_orders(page=1, size=2000)continue",
     "packages = _get_cached_work_orders(page=1, size=2000)\n        for pkg in packages:\n            if status_filter and pkg.get('status') != status_filter:\n                continue"),

    # Fix 5: lines 1436-1438 - list_processes
    ("result = _get_client().query_documents('work_order', page=1, size=5000)\n        records = _extract_items(result)\n        for reco_get_cached_work_orders(page=1, size=5000)              continue",
     "result = _get_cached_work_orders(page=1, size=5000)\n        records = _extract_items(result)\n        for record in records:\n            doc_data = _get_doc_data(record)"),

    # Fix 6: lines 1751-1752 - list_repair_records
    ("result = _get_client().query_documents('work_order', page=1, size=1000)\n        all_pkgs = result if isinstance(result, list) else (result.get('items_get_cached_work_orders(page=1, size=1000))",
     "result = _get_cached_work_orders(page=1, size=1000)\n        all_pkgs = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])"),

    # Fix 7: lines 1778-1779 - complete_repair_record
    ("result = _get_client().query_documents('work_order', page=1, size=1000)\n    pkg_dicts = result if isinstance(result, list) else (result.get('items', result.get('data', [_get_cached_work_orders(page=1, size=1000)for p in pkg_dicts if p.get('id') == record_id and p.get('data_type') == 'repair'), None)",
     "result = _get_cached_work_orders(page=1, size=1000)\n    pkg_dicts = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])\n    target = next((p for p in pkg_dicts if p.get('id') == record_id and p.get('data_type') == 'repair'), None)"),

    # Fix 8: lines 1787-1788 - _get_outsource_records
    ("result = _get_client().query_documents('work_order', page=1, size=2000)\n    pkg_dicts = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(re_get_cached_work_orders(page=1, size=2000)('data_type') == 'outsource'",
     "result = _get_cached_work_orders(page=1, size=2000)\n    pkg_dicts = result if isinstance(result, list) else (result.get('items', result.get('data', [])) if isinstance(result, dict) else [])\n    return [p for p in pkg_dicts if p.get('data_type') == 'outsource'"),

    # Fix 9: lines 1833-1835 - get_outsource_record
    ("pkg_dicts = _get_client().query_documents('work_order', page=1, size=2000) or []\n    target = next((p for p in pkg_dicts if p.get('id') == record_id and p.get('data_type') == 'outsource'), None)\n    if not target_get_cached_work_orders(page=1, size=2000)  return jsonify({'code': 0, 'data': target})",
     "pkg_dicts = _get_cached_work_orders(page=1, size=2000) or []\n    target = next((p for p in pkg_dicts if p.get('id') == record_id and p.get('data_type') == 'outsource'), None)\n    if not target:\n        return jsonify({'code': 404, 'message': '未找到外协记录'})\n    return jsonify({'code': 0, 'data': target})"),

    # Fix 10: line 1844-1847 - assign_outsource_record
    ("pkg_dicts = _get_client().query_documents('work_order', page=1, size=2000) or []\n    target = next((p for p in pkg_dicts if p.get('id') == record_id and p.get('data_type') == 'outsource'), None)\n    if not target:\n        return jso_get_cached_work_orders(page=1, size=2000)ribute(record_id, operator_id)",
     "pkg_dicts = _get_cached_work_orders(page=1, size=2000) or []\n    target = next((p for p in pkg_dicts if p.get('id') == record_id and p.get('data_type') == 'outsource'), None)\n    if not target:\n        return jsonify({'code': 404, 'message': '未找到外协记录'})\n    return jsonify({'code': 0, 'message': _get_client().assign_task_operator('work_order', record_id, operator_id)}"),
]

count = 0
for old, new in fixes:
    if old in content:
        content = content.replace(old, new)
        count += 1
        print(f'Fixed: {old[:60]}...')
    else:
        print(f'NOT FOUND: {old[:60]}...')
        # Try to find similar
        idx = content.find(old[:20])
        if idx >= 0:
            print(f'  Context around match: ...{content[idx:idx+150]}...')

with open(fp, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\nApplied {count} fixes')
