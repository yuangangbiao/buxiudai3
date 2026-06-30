#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib.request, json
url = "http://127.0.0.1:5002/api/v4/work_order?page=1&size=50"
try:
    r = urllib.request.urlopen(url, timeout=5)
    data = json.loads(r.read().decode("utf-8"))
    items = data.get("items", data.get("data", []))
    print(f"5002 work_order 数量: {len(items)}")
    target = ["ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"]
    cnt = 0
    for it in items:
        if not isinstance(it, dict): continue
        d = it.get("doc_data", it.get("data", it.get("content", {})))
        if isinstance(d, str):
            try: d = json.loads(d)
            except: d = {}
        for o in target:
            if isinstance(d, dict) and (d.get("order_no") == o or d.get("related_order") == o or it.get("order_no") == o or it.get("related_order") == o):
                cnt += 1
                print(f"  [{it.get('id','')[:16]:16s}] type={it.get('doc_type',''):15s} st={it.get('status',''):10s} order={d.get('order_no') or d.get('related_order') or it.get('order_no','')}")
                break
    print(f"  4 工单相关: {cnt} 条")
except Exception as e:
    print(f"5002 ERR: {e}")
