# RE-007 R6 Playwright 自动化测试报告

> **测试时间**: 2026-06-10
> **执行人**: TRAE 全栈结对编程
> **范围**: ORD-202604210004 / ORD-202605020001 / ORD-202604210002 / ORD-202605010001
> **工具**: Playwright + Chromium(headless=True,1400×1100)
> **结论**: **PASS ✓**(4 工单 × 7 视图 = 28 截图,0 重复 / 0 异常相同)

---

## 1. 测试脚本

[scripts/pw_re007_r6.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/pw_re007_r6.py)

- API 烟测 + Playwright 截图 + Hash 差异检查
- 截图归档:`docs/debug/order_state/screenshots/R6/`
- 测试日志:`docs/debug/order_state/RE007_R6_自动化测试日志.txt`

## 2. 测试步骤

1. 启动 Chromium,viewport 1400×1100
2. 访问 `http://127.0.0.1:5003/api/dispatch-center/`
3. 等待 2500ms 渲染
4. 对每个工单:
   - 触发 `viewWorkorderDetail(orderNo)` 弹窗
   - 等 2500ms
   - 截图默认视图(物料 tab 激活)
   - 依次点击 6 个 tab 按钮:`物料任务 / 工序报工 / 流程进度 / 质检任务 / 维修任务 / 外协任务`
   - 每个 tab 截图,等 800ms
   - 关闭弹窗
5. 校验:同一工单的 7 张截图 hash 必须唯一(默认 vs material 相同是预期)

## 3. 结果

### 3.1 API 烟测

| 工单 | order.status | material | process | flow | quality |
|---|---|---:|---:|---:|---:|
| ORD-202604210004 | 已派单 | 2 | 9 | 1 | 0 |
| ORD-202605020001 | 已完成 | 0 | 16 | 2 | 0 |
| ORD-202604210002 | 待开始 | 0 | 9 | 1 | 2 |
| ORD-202605010001 | 已完成 | 2 | 9 | 9 | 0 |

✅ 4 工单 API 全部 200,数据分布合理

### 3.2 Playwright 截图 Hash 差异

| 工单 | default md5 | unique_tabs | dupes | 异常相同 |
|---|---|---:|:---:|:---:|
| ORD-202604210004 | 027639cffb | 6 | 0 | 0 |
| ORD-202605020001 | 99f7ae0dfe | 6 | 0 | 0 |
| ORD-202604210002 | 48531d5f91 | 6 | 0 | 0 |
| ORD-202605010001 | 304ad0805f | 6 | 0 | 0 |

**总截图数**: 4 × 7 = **28 张**
**差异化**: 6 unique tabs × 4 orders = 24 张差异化 + 4 张 default = material 重复
**结论**: ✅ tab 切换全部生效,5 个非默认 tab 视图各不相同

### 3.3 关键修复点

| # | 问题 | 修复 |
|---|---|---|
| 1 | `switchWoTab(null, 'process')` 报错 btn 为 null | 改用 `page.locator('button.wo-tab-btn:has-text("...")').first.click()` |
| 2 | 6 个 tab 截图 hash 全部跟默认相同 | tab 切换真实生效后,5 个非默认 tab 全部差异化 |
| 3 | material tab 跟 default md5 相同被误判为 FAIL | 在 hash 校验中排除 material tab(material 默认激活,相同是预期) |

## 4. 截图清单

`docs/debug/order_state/screenshots/R6/`

```
ORD-202604210002_00_default.png      (122 KB)
ORD-202604210002_tab_flow.png        (121 KB)
ORD-202604210002_tab_material.png    (121 KB)
ORD-202604210002_tab_outsource.png   (121 KB)
ORD-202604210002_tab_process.png     (121 KB)
ORD-202604210002_tab_quality.png     (121 KB)
ORD-202604210002_tab_repair.png      (121 KB)
ORD-202604210004_00_default.png      (129 KB)
ORD-202604210004_tab_flow.png        (128 KB)
ORD-202604210004_tab_material.png    (128 KB)
ORD-202604210004_tab_outsource.png   (128 KB)
ORD-202604210004_tab_process.png     (128 KB)
ORD-202604210004_tab_quality.png     (128 KB)
ORD-202604210004_tab_repair.png      (128 KB)
ORD-202605010001_00_default.png      (131 KB)
ORD-202605010001_tab_flow.png        (130 KB)
ORD-202605010001_tab_material.png    (130 KB)
ORD-202605010001_tab_outsource.png   (130 KB)
ORD-202605010001_tab_process.png     (130 KB)
ORD-202605010001_tab_quality.png     (130 KB)
ORD-202605010001_tab_repair.png      (130 KB)
ORD-202605020001_00_default.png      (123 KB)
ORD-202605020001_tab_flow.png        (123 KB)
ORD-202605020001_tab_material.png    (123 KB)
ORD-202605020001_tab_outsource.png   (123 KB)
ORD-202605020001_tab_process.png     (123 KB)
ORD-202605020001_tab_quality.png     (123 KB)
ORD-202605020001_tab_repair.png      (123 KB)
```

## 5. 自动化测试新增规则

✅ **前端需要做自动化测试**(用户新规生效,2026-06-10)
✅ 调度中心工单详情弹窗的 6 个 tab 必须可自动化切换
✅ 截图差异作为"前端 bug 检测"基线 — 同一工单的不同视图应当 hash 不同

## 6. 后续

- [ ] R7:加入 4 工单 + 中文 status 文本断言(替代 hash 差异)
- [ ] R8:把 R6/R7 接入 CI(每次 dispatch_center.js 改动自动跑)
- [ ] R9:扩展覆盖报工端 / 质检端
