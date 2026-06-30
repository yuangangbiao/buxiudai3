#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q4 截图 4 个工单的详情弹窗 + 每个 tab"""
import os
import re

from playwright.sync_api import sync_playwright

OUT = r"d:\yuan\不锈钢网带跟单3.0\docs\debug\order_state\screenshots"
os.makedirs(OUT, exist_ok=True)

ORDERS = ["ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"]

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1400, "height": 1100})
    page = context.new_page()
    page.goto("http://127.0.0.1:5003/api/dispatch-center/", timeout=30000)
    page.wait_for_timeout(5000)

    for order in ORDERS:
        print(f"\n[Q4] {order}")
        # 调 viewWorkorderDetail
        try:
            page.evaluate(f"window.viewWorkorderDetail('{order}')")
            page.wait_for_timeout(2500)
        except Exception as e:
            print(f"  ERR view: {e}")
            continue
        page.screenshot(path=os.path.join(OUT, f"{order}_00_default.png"), full_page=True)
        # 点每个 tab
        for tab_name in ["material", "process", "flow", "quality", "repair", "outsource"]:
            try:
                page.evaluate(f"if(typeof switchWoTab==='function'){{switchWoTab(null,'{tab_name}')}}")
                page.wait_for_timeout(400)
            except Exception:
                pass
            page.screenshot(path=os.path.join(OUT, f"{order}_tab_{tab_name}.png"), full_page=True)
        # 关闭弹窗
        page.evaluate("document.querySelectorAll('.modal-close, .close, [data-dismiss=modal]').forEach(b=>b.click())")
        page.wait_for_timeout(500)

    browser.close()
print("\n所有截图保存到:", OUT)
