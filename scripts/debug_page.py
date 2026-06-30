# -*- coding: utf-8 -*-
"""调试脚本:抓取 dispatch_center 页面 HTML 找按钮"""
import os
from playwright.sync_api import sync_playwright

OUT_DIR = r"d:\yuan\不锈钢网带跟单3.0\docs\playwright"
os.makedirs(OUT_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = context.new_page()

    page.goto("http://127.0.0.1:5003/api/dispatch-center/", timeout=30000)
    page.wait_for_timeout(5000)  # 等待渲染

    # 抓取 HTML
    html = page.content()
    with open(os.path.join(OUT_DIR, "page.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML length: {len(html)}")

    # 抓取所有按钮
    buttons = page.query_selector_all("button")
    print(f"Buttons: {len(buttons)}")
    for i, b in enumerate(buttons[:30]):
        text = b.inner_text().strip() if b.inner_text() else ""
        onclick = b.get_attribute("onclick") or ""
        print(f"  [{i}] text={text!r} onclick={onclick[:80]!r}")

    # 抓取标题
    title = page.title()
    print(f"Title: {title}")

    # 抓取 body 文本
    body_text = page.evaluate("document.body.innerText")
    print(f"Body text (first 500): {body_text[:500]!r}")

    page.screenshot(path=os.path.join(OUT_DIR, "debug.png"), full_page=True)
    browser.close()
