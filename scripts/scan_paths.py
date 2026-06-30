# -*- coding: utf-8 -*-
"""扫描 dispatch_center 实际路径"""
import os
from playwright.sync_api import sync_playwright

OUT_DIR = r"d:\yuan\不锈钢网带跟单3.0\docs\playwright"

candidates = [
    "http://127.0.0.1:5003/dispatch_center",
    "http://127.0.0.1:5003/dispatch_center.html",
    "http://127.0.0.1:5003/mobile/dispatch_center/",
    "http://127.0.0.1:5003/dispatch/",
    "http://127.0.0.1:5003/m/dispatch_center/",
    "http://127.0.0.1:5003/mobile_api_ai/dispatch_center/",
    "http://127.0.0.1:5003/mobile_api_ai/static/dispatch_center.html",
    "http://127.0.0.1:5003/static/dispatch_center.html",
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = context.new_page()
    for url in candidates:
        try:
            resp = page.goto(url, timeout=10000, wait_until="domcontentloaded")
            status = resp.status if resp else "NO_RESP"
            title = page.title()
            body_sample = page.evaluate("document.body.innerText")[:200]
            print(f"{url}\n   status={status} title={title!r}\n   body[:200]={body_sample!r}\n")
        except Exception as e:
            print(f"{url}\n   ERR: {e}\n")
    browser.close()
