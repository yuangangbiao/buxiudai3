# -*- coding: utf-8 -*-
"""直接通过 API 拿 order_no,然后 JS 调 viewWorkorderDetail"""
import json
import os
import re
import urllib.request

from playwright.sync_api import sync_playwright

OUT = r"d:\yuan\不锈钢网带跟单3.0\docs\playwright"
os.makedirs(OUT, exist_ok=True)

# 1. 调 list_processes API 拿 order_no
url = "http://127.0.0.1:5003/api/dispatch-center/processes?page=1&size=5"
try:
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))
    print(f"[API] code={data.get('code')}, top keys: {list(data.keys())}")
    payload = data.get("data", {})
    if isinstance(payload, list):
        procs = payload
    elif isinstance(payload, dict):
        procs = payload.get("processes") or payload.get("list") or payload.get("items") or []
    else:
        procs = []
    print(f"[API] processes: {len(procs)}")
    order_no = None
    for p in procs:
        if p.get("order_no"):
            order_no = p["order_no"]
            break
    print(f"[API] 第一个 order_no = {order_no}")
    if not order_no:
        with open(os.path.join(OUT, "api_response.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("保存到 api_response.json")
        exit(1)
except Exception as e:
    print(f"[API ERR] {e}")
    exit(1)

# 2. Playwright 打开页面 + 调 viewWorkorderDetail
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = context.new_page()

    page.goto("http://127.0.0.1:5003/api/dispatch-center/", timeout=30000)
    page.wait_for_timeout(5000)
    page.screenshot(path=os.path.join(OUT, "01_dispatch_list.png"), full_page=True)
    print("[1] 列表页截图")

    # 调 viewWorkorderDetail
    page.evaluate(f"window.viewWorkorderDetail('{order_no}')")
    page.wait_for_timeout(3000)
    page.screenshot(path=os.path.join(OUT, "02_modal_default.png"), full_page=True)
    print(f"[2] 工单 {order_no} 详情弹窗已截图")

    # 3. 提取 6 张卡片
    cards = page.query_selector_all(".modal .cards .card")
    summary = []
    for c in cards:
        label = c.query_selector(".label")
        value = c.query_selector(".value")
        if label and value:
            summary.append({"label": label.inner_text().strip(),
                            "value": value.inner_text().strip()})
    print("[3] 卡片摘要:")
    for s in summary:
        print(f"     {s['label']}: {s['value']}")

    # 4. 提取 6 个 tab
    tabs = page.query_selector_all(".wo-tab-btn")
    tab_list = [t.inner_text().strip() for t in tabs]
    print(f"[4] Tab 列表: {tab_list}")

    # 5. 点击每个 tab 截图
    for i, tab in enumerate(tabs):
        try:
            tab.click(timeout=5000)
            page.wait_for_timeout(700)
            txt = tab.inner_text().strip()
            print(f"     tab[{i}] {txt}")
        except Exception as e:
            print(f"     tab[{i}] click failed: {e}")
        page.screenshot(path=os.path.join(OUT, f"03_tab_{i:02d}.png"), full_page=True)

    # 6. 提取每个 tab 的内容行数
    print("[6] 各 tab 内容行数:")
    for card_id in ["wo-tab-material", "wo-tab-process", "wo-tab-flow",
                    "wo-tab-quality", "wo-tab-repair", "wo-tab-outsource"]:
        el = page.query_selector(f"#{card_id}")
        if not el:
            print(f"     {card_id}: 元素不存在")
            continue
        page.evaluate(f"document.getElementById('{card_id}').style.display='block'")
        page.wait_for_timeout(200)
        rows = el.query_selector_all("tbody tr")
        # 取前 3 行的内容
        sample = []
        for r in rows[:3]:
            cells = r.query_selector_all("td")
            sample.append([c.inner_text().strip() for c in cells])
        print(f"     {card_id}: {len(rows)} 行, 样本: {sample[:1]}")

    # 7. 流程进度 tab 详细截图
    flow_tab = page.query_selector(".wo-tab-btn[onclick*=\"'flow'\"]")
    if not flow_tab:
        flow_tab = page.query_selector(".wo-tab-btn:has-text('流程进度')")
    if flow_tab:
        flow_tab.click()
        page.wait_for_timeout(800)
        page.screenshot(path=os.path.join(OUT, "04_flow_tab.png"), full_page=True)
        print("[7] 流程进度 tab 截图")

    # 8. 保存 JSON 报告
    report = {
        "order_no": order_no,
        "summary_cards": summary,
        "tab_list": tab_list,
        "expected_6_tabs": ["物料任务", "工序报工", "流程进度", "质检任务", "维修任务", "外协任务"],
    }
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("[8] 报告保存")

    browser.close()
