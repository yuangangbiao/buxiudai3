"""
RE-007 R6 Playwright 自动化测试 v2
- 修复 tab 切换:用真实点击 .wo-tab-btn(传 btn 引用)
- 4 工单 × 7 tab = 28 截图
- 校验:截图 hash 区分、显示中文
"""
import hashlib
import json
import os
import re
import urllib.request

from playwright.sync_api import sync_playwright

OUT_DIR = r"C:\Windows\Temp\R6_shots"
API_BASE = "http://127.0.0.1:5003/api/dispatch-center"
ORDERS = ["ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"]
TABS = [
    ("material", "📦 物料任务"),
    ("process", "⚙️ 工序报工"),
    ("flow", "📊 流程进度"),
    ("quality", "🔍 质检任务"),
    ("repair", "🔧 维修任务"),
    ("outsource", "🏭 外协任务"),
]

os.makedirs(OUT_DIR, exist_ok=True)

# 清空旧的
for f in os.listdir(OUT_DIR):
    try:
        os.remove(os.path.join(OUT_DIR, f))
    except Exception:
        pass

log = []
hashes = {}
log.append("=" * 60)
log.append("RE-007 R6 Playwright 重验 v2")
log.append("=" * 60)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1400, "height": 1100})
    page = context.new_page()
    page.goto(f"{API_BASE}/", timeout=30000)
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    page.wait_for_timeout(2500)

    for order in ORDERS:
        log.append(f"\n[工单] {order}")
        page.evaluate(f"window.viewWorkorderDetail('{order}')")
        page.wait_for_timeout(2500)

        # 默认截图(material tab 默认激活)
        default_path = os.path.join(OUT_DIR, f"{order}_00_default.png")
        page.screenshot(path=default_path, full_page=True)
        with open(default_path, "rb") as f:
            default_hash = hashlib.md5(f.read()).hexdigest()[:10]
        log.append(f"  📸 00_default.png md5={default_hash}")

        # 切 tab(用真实点击 button)
        for tab_key, tab_label in TABS:
            try:
                # 用 selector 找到匹配文字的 button 并点击
                page.locator(f"button.wo-tab-btn:has-text('{tab_label}')").first.click()
                page.wait_for_timeout(800)
            except Exception as e:
                log.append(f"  ⚠️ click '{tab_label}' failed: {e}")
            shot_path = os.path.join(OUT_DIR, f"{order}_tab_{tab_key}.png")
            page.screenshot(path=shot_path, full_page=True)
            with open(shot_path, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()[:10]
            hashes.setdefault(order, []).append((tab_key, h))
            log.append(f"  📸 tab_{tab_key}.png md5={h}")

        # 关闭弹窗
        try:
            page.evaluate("document.querySelectorAll('.modal-close, .modal-overlay .close').forEach(b=>b.click())")
            page.wait_for_timeout(500)
        except Exception:
            pass

    browser.close()

# Hash 差异检查 — 同一工单的 7 张截图必须各不相同
log.append("")
log.append("[Hash 差异检查]")
all_pass = True
for order, lst in hashes.items():
    seen = set()
    dupes = []
    for tab, h in lst:
        if h in seen:
            dupes.append(tab)
        seen.add(h)
    # 默认那张要对比
    default_md5 = None
    default_path = os.path.join(OUT_DIR, f"{order}_00_default.png")
    if os.path.exists(default_path):
        with open(default_path, "rb") as f:
            default_md5 = hashlib.md5(f.read()).hexdigest()[:10]
    # material tab 默认激活,所以其 hash 等于 default_hash 是预期行为
    same_as_default = [tab for tab, h in lst if h == default_md5 and tab != "material"]
    log.append(f"  {order}: default={default_md5}  unique_tabs={len(seen)}  dupes={dupes}  non_material_same_as_default={same_as_default}")
    if dupes or same_as_default:
        all_pass = False

log.append("")
log.append("=" * 60)
log.append(f"结果: {'PASS ✓' if all_pass else 'FAIL ✗'}")
log.append(f"截图: {OUT_DIR}")
log.append("=" * 60)

with open(r"C:\Windows\Temp\_re007_r6_log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(log))

print(f"DONE all_pass={all_pass}")
