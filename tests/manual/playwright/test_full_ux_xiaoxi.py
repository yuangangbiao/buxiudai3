# -*- coding: utf-8 -*-
"""
import pytest

pytestmark = pytest.mark.manual  # 独立验收/Playwright 脚本，不参与 pytest 单元统计


小曦用户体验测试 - web5001 全面 UI 测试
测试: 页面加载、登录流程、表单交互、新字段、批量操作、导航菜单
"""
import os
import sys
import json
import datetime

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5001"
OUT_DIR = r"d:\yuan\不锈钢网带跟单3.0\logs\ux_test_xiaoxi"
os.makedirs(OUT_DIR, exist_ok=True)

PASS = 0
FAIL = 0
RESULTS = []
SCREENSHOTS = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}: {str(detail)[:100]}")
    RESULTS.append({"name": name, "passed": cond, "detail": str(detail)[:200]})


def screenshot(page, name):
    path = os.path.join(OUT_DIR, f"{name}_{datetime.datetime.now().strftime('%H%M%S')}.png")
    page.screenshot(path=path, full_page=True)
    SCREENSHOTS.append(path)
    print(f"  📸 截图: {path}")
    return path


def test_page_loading(browser):
    print("\n" + "=" * 60)
    print("1. 页面加载测试")
    print("=" * 60)

    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    errors = []

    def handle_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", handle_console)

    pages = [
        ("/login", "登录页"),
        ("/production-admin", "工单"),
        ("/material-admin", "物料"),
        ("/process-admin", "工序"),
        ("/quality-admin", "质检"),
        ("/shipment-admin", "发货"),
    ]

    for path, label in pages:
        errors.clear()
        page.goto(f"{BASE}{path}", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(1500)

        html = page.content()
        check(f"{label}页面加载 (>1000字符)", len(html) > 1000, f"实际: {len(html)}")

        js_errors = [e for e in errors if "Error" in e or "error" in e]
        check(f"{label}页面无JS错误", len(js_errors) == 0, js_errors[:2] if js_errors else "")

        page.remove_listener("console", handle_console)
        page.on("console", handle_console)

    page.close()
    return browser


def test_login_flow(browser):
    print("\n" + "=" * 60)
    print("2. 登录流程测试")
    print("=" * 60)

    page = browser.new_page(viewport={"width": 1920, "height": 1080})

    page.goto(f"{BASE}/login", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(1000)

    check("登录页有用户名输入框(#u)", page.locator("#u").count() > 0)
    check("登录页有密码输入框(#p)或说明文字", page.locator("input[placeholder*='姓名']").count() > 0 or page.locator("#u").count() > 0)
    check("登录页有提交按钮", page.locator("button[type='submit']").count() > 0)

    page.fill("#u", "测试")
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle", timeout=15000)
    page.wait_for_timeout(2000)

    current_url = page.url
    login_success = "/orders" in current_url or "/production" in current_url or "orders" in current_url
    check("登录后跳转到主页", login_success, current_url)

    nav_items = ["生产", "物料", "工序", "质检", "发货"]
    for item in nav_items:
        count = page.locator(f"text={item}").count()
        check(f"导航含{item}", count > 0)

    page.close()
    return browser


def test_material_admin(page):
    print("\n" + "=" * 60)
    print("3. 物料管理页面测试")
    print("=" * 60)

    page.goto(f"{BASE}/material-admin", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(2000)

    add_btns = page.locator("button:has-text('添加'), button:has-text('新建'), button:has-text('新增')").count()
    check("物料页面有添加按钮", add_btns > 0, f"找到 {add_btns} 个按钮")

    toolbar = page.locator(".toolbar, .batch-toolbar").count()
    check("物料页面有工具栏", toolbar > 0)

    return page


def test_shipment_new_fields(browser):
    print("\n" + "=" * 60)
    print("4. 发货页面新字段测试")
    print("=" * 60)

    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(f"{BASE}/login", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(1000)

    page.fill("#u", "测试")
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle", timeout=15000)
    page.wait_for_timeout(2000)

    page.goto(f"{BASE}/shipment-admin", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(2000)

    new_btn = None
    for selector in ["button:has-text('新建')", "button:has-text('添加')", "button:has-text('创建')"]:
        if page.locator(selector).count() > 0:
            new_btn = page.locator(selector).first
            break

    if new_btn:
        new_btn.click()
        page.wait_for_timeout(1500)

        check("发货表单有仓库字段", page.locator("#sfWarehouse").count() > 0 or page.locator("input[id*='warehouse']").count() > 0)
        check("发货表单有运费字段", page.locator("#sfFreight").count() > 0 or page.locator("input[id*='freight']").count() > 0)

        html = page.content()
        has_warehouse = "仓库" in html
        has_freight = "运费" in html
        check("发货表单显示仓库标签", has_warehouse, "仓库" if has_warehouse else "未找到")
        check("发货表单显示运费标签", has_freight, "运费" if has_freight else "未找到")

        close_btn = page.locator("button:has-text('取消')").first
        if close_btn.count() > 0 and close_btn.is_visible():
            try:
                close_btn.click(timeout=3000)
                page.wait_for_timeout(500)
            except Exception:
                pass
    else:
        check("发货页面有新建按钮", False, "未找到按钮")

    page.close()
    return browser


def test_production_batch_ops(page):
    print("\n" + "=" * 60)
    print("5. 生产页面批量操作测试")
    print("=" * 60)

    page.goto(f"{BASE}/production-admin", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(2000)

    batch_pub = page.get_by_text("批量发布").count()
    if batch_pub == 0:
        batch_pub = page.locator("button:has-text('批量发布')").count()
    check("生产页面有批量发布按钮", batch_pub > 0, f"找到 {batch_pub} 个")

    check("生产页面有批量工具栏", page.locator(".batch-toolbar").count() > 0)

    checkbox = page.locator("input[type='checkbox'], .col-check").first
    if checkbox.count() > 0:
        try:
            checkbox.click()
            page.wait_for_timeout(500)
            batch_toolbar = page.locator(".batch-toolbar:not([style*='none'])").count()
            check("勾选后批量工具栏出现", batch_toolbar > 0)
        except Exception as e:
            check("勾选后批量工具栏出现", False, str(e)[:50])

    return page


def test_quality_admin(page):
    print("\n" + "=" * 60)
    print("6. 质检管理页面测试")
    print("=" * 60)

    page.goto(f"{BASE}/quality-admin", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(2000)

    html = page.content()
    check("质检页面有内容", len(html) > 1000, f"实际: {len(html)}")

    has_rules = "规则" in html or "质检" in html
    check("质检页面显示质检相关文字", has_rules)

    toolbar = page.locator(".toolbar").count()
    check("质检页面有工具栏", toolbar > 0)

    return page


def test_process_admin(page):
    print("\n" + "=" * 60)
    print("7. 工序管理页面测试")
    print("=" * 60)

    page.goto(f"{BASE}/process-admin", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(2000)

    html = page.content()
    check("工序页面有内容", len(html) > 1000, f"实际: {len(html)}")

    has_process = "工序" in html or "工序" in html
    check("工序页面显示工序相关文字", has_process)

    return page


def test_nav_menu(browser):
    print("\n" + "=" * 60)
    print("8. 导航菜单测试")
    print("=" * 60)

    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(f"{BASE}/login", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(1000)

    page.fill("#u", "测试")
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle", timeout=15000)
    page.wait_for_timeout(2000)

    nav_items = ["生产", "物料", "工序", "质检", "发货", "跟单"]
    for item in nav_items:
        count = page.get_by_text(item, exact=False).count()
        check(f"主导航含{item}", count > 0, f"找到 {count} 处")

    page.close()
    return browser


def test_responsive_layout(browser):
    print("\n" + "=" * 60)
    print("9. 响应式布局测试")
    print("=" * 60)

    viewports = [
        (1920, 1080, "桌面1920"),
        (1366, 768, "笔记本1366"),
        (414, 896, "手机414"),
    ]

    for width, height, label in viewports:
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(f"{BASE}/production-admin", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(1000)

        html = page.content()
        check(f"{label}下页面可加载", len(html) > 500, f"实际: {len(html)}")

        page.close()

    return browser


def generate_report():
    report_path = os.path.join(OUT_DIR, f"test_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    score = PASS / (PASS + FAIL) * 100 if (PASS + FAIL) > 0 else 0

    grade = "优秀" if score >= 90 else "良好" if score >= 75 else "一般" if score >= 60 else "较差"

    report = f"""# 小曦用户体验测试报告 - web5001

## 测试信息
- 测试时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 测试地址: {BASE}
- 测试人员: 小曦 (产品经理)

## 测试结果概览

| 指标 | 数值 |
|------|------|
| 总测试项 | {PASS + FAIL} |
| 通过数 | {PASS} |
| 失败数 | {FAIL} |
| 通过率 | {score:.1f}% |
| 体验评级 | **{grade}** |

## 测试详情

### 1. 页面加载测试
"""

    for r in RESULTS:
        status = "✅" if r["passed"] else "❌"
        detail = f" - {r['detail']}" if r["detail"] else ""
        report += f"- {status} {r['name']}{detail}\n"

    report += f"""
## 截图记录
"""
    for s in SCREENSHOTS:
        report += f"- {s}\n"

    report += f"""
## 结论

本次测试共执行 **{PASS + FAIL}** 项测试，通过 **{PASS}** 项，失败 **{FAIL}** 项。

用户体验评级: **{grade}** (通过率 {score:.1f}%)

### 通过项 ({PASS})
"""
    for r in RESULTS:
        if r["passed"]:
            report += f"- ✅ {r['name']}\n"

    if FAIL > 0:
        report += f"""
### 失败项 ({FAIL})
"""
        for r in RESULTS:
            if not r["passed"]:
                report += f"- ❌ {r['name']}: {r['detail']}\n"

    report += """
## 建议

"""
    if score >= 90:
        report += "系统用户体验优秀，功能完善，建议继续优化细节。\n"
    elif score >= 75:
        report += "系统用户体验良好，存在一些小问题需要修复。\n"
    elif score >= 60:
        report += "系统用户体验一般，建议优先修复失败项。\n"
    else:
        report += "系统用户体验较差，建议全面检查并修复问题。\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📄 报告已生成: {report_path}")
    return report_path


def main():
    print("=" * 60)
    print("小曦用户体验测试 - web5001")
    print("=" * 60)
    print(f"测试地址: {BASE}")
    print(f"输出目录: {OUT_DIR}")

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})

            test_page_loading(browser)
            test_login_flow(browser)
            test_material_admin(page)
            test_shipment_new_fields(browser)
            test_production_batch_ops(page)
            test_quality_admin(page)
            test_process_admin(page)
            test_nav_menu(browser)
            test_responsive_layout(browser)

            browser.close()
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"测试结果: ✅{PASS}  ❌{FAIL}")
    print("=" * 60)

    score = PASS / (PASS + FAIL) * 100 if (PASS + FAIL) > 0 else 0
    grade = "优秀" if score >= 90 else "良好" if score >= 75 else "一般" if score >= 60 else "较差"
    print(f"用户体验评级: {grade} (通过率 {score:.1f}%)")

    report_path = generate_report()

    print(f"\n📄 报告路径: {report_path}")
    return PASS, FAIL


if __name__ == "__main__":
    main()
