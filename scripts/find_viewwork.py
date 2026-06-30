# -*- coding: utf-8 -*-
"""找 viewWorkorderDetail 调用位置"""
import os
from playwright.sync_api import sync_playwright

OUT = r"d:\yuan\不锈钢网带跟单3.0\docs\playwright"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = context.new_page()

    page.goto("http://127.0.0.1:5003/api/dispatch-center/", timeout=30000)
    page.wait_for_timeout(6000)

    # 抓所有 onclick
    all_onclicks = page.evaluate("""
        () => Array.from(document.querySelectorAll('[onclick]'))
            .map(el => ({tag: el.tagName, text: el.innerText ? el.innerText.slice(0, 30) : '',
                         onclick: (el.getAttribute('onclick') || '').slice(0, 100)}))
    """)
    print(f"Total onclicks: {len(all_onclicks)}")
    # 过滤 viewWork
    related = [o for o in all_onclicks if "viewWork" in o["onclick"] or "工单" in o["text"]]
    print(f"viewWork related: {len(related)}")
    for r in related[:20]:
        print(" ", r)

    # 看下拉卡片里有没有
    page.wait_for_timeout(3000)
    related2 = page.evaluate("""
        () => Array.from(document.querySelectorAll('[onclick]'))
            .filter(el => /viewWorkorderDetail/.test(el.getAttribute('onclick') || ''))
            .map(el => el.getAttribute('onclick'))
    """)
    print(f"After wait viewWorkorderDetail: {len(related2)}")
    for r in related2[:5]:
        print(" ", r)

    browser.close()
