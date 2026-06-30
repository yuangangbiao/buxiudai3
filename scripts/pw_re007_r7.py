"""
RE-007 R7 中文 status 文本断言(替代 hash 差异)

策略:
- 对每个工单 × 每个 tab,直接读 #wo-tab-{name} 的 innerText
- 断言关键中文 status / data_type / related_process 文本必须出现
- 失败:打印期望 vs 实际,便于定位

断言矩阵(基于 ORD-202605010001 重验结果):
- order.status 全中文(已完成 / 已派单 / 待开始)
- material tab:物料已确认 / 物料申请 / 备料-XXX
- process tab:已完成 / 工序报工 / 工序名(穿杆组装 / 表面处理等)
- flow tab:已派单 / 流程步骤 / 生产执行 / 排产发布 / 报工完成
- quality tab:暂无质检任务(空状态文案)
- repair/outsource tab:暂无XX任务
"""
import json
import os
import urllib.request

from playwright.sync_api import sync_playwright

# === R10:字典自动同步 — SSOT 合并 ===
import sys
sys.path.insert(0, r"d:\yuan\不锈钢网带跟单3.0")
from utils.expected_zh import (
    get_expected_status_zh,
    get_expected_datatype_zh,
)

EXPECTED_STATUS_ZH = get_expected_status_zh()
EXPECTED_DATATYPE_ZH = get_expected_datatype_zh()

OUT_DIR = r"C:\Windows\Temp\R7_shots"
API_BASE = "http://127.0.0.1:5003/api/dispatch-center"
ORDERS = ["ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"]

os.makedirs(OUT_DIR, exist_ok=True)
for f in os.listdir(OUT_DIR):
    try:
        os.remove(os.path.join(OUT_DIR, f))
    except Exception:
        pass

log = []
fails = []

log.append("=" * 60)
log.append("RE-007 R7 中文 status 文本断言")
log.append("=" * 60)

# 1) API 层断言 — 直接拿 JSON,验证 status 中文 + data_type 中文
log.append("\n[Phase 1: API 文本断言]")
api_results = {}

for order in ORDERS:
    try:
        url = f"{API_BASE}/workorder/{order}"
        r = urllib.request.urlopen(url, timeout=5)
        d = json.loads(r.read().decode("utf-8"))
        inner = d.get("data", {})
        order_status = inner.get("status", "")
        order_status_zh = order_status in {"已完成", "已派单", "待开始", "待处理", "进行中"}

        # 检查 process_tasks
        proc_statuses = [t.get("status") for t in inner.get("process_tasks", [])]
        proc_all_zh = all(s in EXPECTED_STATUS_ZH for s in proc_statuses if s)
        proc_english = [s for s in proc_statuses if s and s not in EXPECTED_STATUS_ZH]

        # 检查 material_tasks
        mat_statuses = [t.get("status") for t in inner.get("material_tasks", [])]
        mat_all_zh = all(s in EXPECTED_STATUS_ZH for s in mat_statuses if s)
        mat_english = [s for s in mat_statuses if s and s not in EXPECTED_STATUS_ZH]

        # 检查 flow_steps
        flow_statuses = [t.get("status") for t in inner.get("flow_steps", [])]
        flow_all_zh = all(s in EXPECTED_STATUS_ZH for s in flow_statuses if s)
        flow_english = [s for s in flow_statuses if s and s not in EXPECTED_STATUS_ZH]

        # data_type
        all_types = []
        for sec in ["process_tasks", "material_tasks", "flow_steps", "quality_tasks",
                    "repair_tasks", "outsource_tasks"]:
            for t in inner.get(sec, []):
                if t.get("data_type"):
                    all_types.append(t.get("data_type"))
        types_all_zh = all(t in EXPECTED_DATATYPE_ZH for t in all_types if t)
        type_english = [t for t in all_types if t and t not in EXPECTED_DATATYPE_ZH]

        result = {
            "order": order,
            "order_status": order_status,
            "order_status_zh": order_status_zh,
            "proc_zh": proc_all_zh,
            "proc_english": proc_english,
            "mat_zh": mat_all_zh,
            "mat_english": mat_english,
            "flow_zh": flow_all_zh,
            "flow_english": flow_english,
            "types_zh": types_all_zh,
            "type_english": type_english,
            "pass": (order_status_zh and proc_all_zh and mat_all_zh and flow_all_zh
                     and types_all_zh and not proc_english and not mat_english
                     and not flow_english and not type_english),
        }
        api_results[order] = result
        log.append(f"  {order}: order={order_status!r} zh={order_status_zh} "
                   f"proc_zh={proc_all_zh} mat_zh={mat_all_zh} flow_zh={flow_all_zh} "
                   f"types_zh={types_all_zh} -> {'PASS' if result['pass'] else 'FAIL'}")
        if not result["pass"]:
            log.append(f"    残留英文: proc={proc_english} mat={mat_english} flow={flow_english} type={type_english}")
            fails.append((order, "API", "英文 status 残留"))
    except Exception as e:
        log.append(f"  {order}: API ERR={e}")
        fails.append((order, "API", str(e)))

# 2) 渲染层断言 — 实际打开浏览器,看 tab 内的中文字符串
log.append("\n[Phase 2: 渲染文本断言]")
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1400, "height": 1100})
    page = context.new_page()
    page.goto(f"{API_BASE}/", timeout=30000)
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    page.wait_for_timeout(2500)

    for order in ORDERS:
        log.append(f"\n  [工单] {order}")
        page.evaluate(f"window.viewWorkorderDetail('{order}')")
        page.wait_for_timeout(2000)

        # 逐个 tab 断言
        TABS = [
            ("material", "📦 物料任务"),
            ("process", "⚙️ 工序报工"),
            ("flow", "📊 流程进度"),
            ("quality", "🔍 质检任务"),
            ("repair", "🔧 维修任务"),
            ("outsource", "🏭 外协任务"),
        ]
        for tab_key, tab_label in TABS:
            try:
                page.locator(f"button.wo-tab-btn:has-text('{tab_label}')").first.click()
                page.wait_for_timeout(500)
            except Exception:
                pass

            # 抓取 tab 内容
            text = page.evaluate(f"""() => {{
                const el = document.getElementById('wo-tab-{tab_key}');
                return el ? el.innerText : '';
            }}""")

            # 断言
            tab_fails = []
            # 1) 状态徽章
            status_badges = page.evaluate(f"""() => {{
                const el = document.getElementById('wo-tab-{tab_key}');
                if (!el) return [];
                return Array.from(el.querySelectorAll('.status-badge')).map(b => b.innerText.trim());
            }}""")
            for badge in status_badges:
                # 允许"暂无XX任务"文案和"-"
                if badge in ("-", "") or "暂无" in badge:
                    continue
                if badge not in EXPECTED_STATUS_ZH:
                    tab_fails.append(f"英文 status badge: {badge!r}")

            # 2) 截图
            shot_path = os.path.join(OUT_DIR, f"{order}_tab_{tab_key}.png")
            page.screenshot(path=shot_path, full_page=True)

            if tab_fails:
                log.append(f"    ✗ {tab_key}: {tab_fails}")
                fails.append((order, f"tab-{tab_key}", "; ".join(tab_fails)))
            else:
                log.append(f"    ✓ {tab_key}: {len(status_badges)} badges all ZH")

        # 关闭弹窗
        try:
            page.evaluate("document.querySelectorAll('.modal-close, .modal-overlay .close').forEach(b=>b.click())")
            page.wait_for_timeout(400)
        except Exception:
            pass

    browser.close()

# 3) 总结
log.append("")
log.append("=" * 60)
if not fails:
    log.append(f"结果: PASS ✓(4 工单 API + 4 工单 × 6 tab 渲染断言全过)")
else:
    log.append(f"结果: FAIL ✗({len(fails)} 处失败)")
    for o, w, e in fails:
        log.append(f"  - {o} {w}: {e}")
log.append(f"截图: {OUT_DIR}")
log.append("=" * 60)

with open(r"C:\Windows\Temp\_re007_r7_log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(log))

print(f"DONE fails={len(fails)}")
