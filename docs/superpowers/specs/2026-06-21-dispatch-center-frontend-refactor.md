# 调度中心前端结构重构设计方案

**版本**：v2.0（审计修正版）
**日期**：2026-06-21
**审计轮次**：第 1 轮悲观审计 → 发现方案对现状判断有误，已完全重写

---

## 一、实际现状（审计核实）

### 文件结构

```
dispatch_center.html      ← 2318 行
  L1~1541   HTML 结构 + 外联 CSS/JS 引用
  L1542~1545 内联配置脚本（API_BASE 等，5 行）
  L1549~L2315 内联回归测试 JS（767 行，62 个函数）

static/js/dispatch_center.js   ← 4882 行，100 个函数
  L1~222   基础设施（CONFIG、CACHE、Loading、Toast、Modal）
  L223~4882 核心 JS（switchTab、API、refresh、render 等 100 个函数）

static/css/dispatch_center.css ← 已有外联 CSS
```

### 已完成（无需重复做）

| 项目 | 状态 |
|------|------|
| CSS 外联 | ✅ 已有 `/static/css/dispatch_center.css` |
| JS 外联 | ✅ 已有 `/static/js/dispatch_center.js` |
| HTML 结构纯化 | ✅ HTML 无内联 `<style>` 块 |
| Tab 切换逻辑 | ✅ `switchTab()` 在外部 JS L223 |

### 实际需要做的事

**仅 1 步**：把 `dispatch_center.html` L1549~L2318 的 **62 个回归测试函数**合并到 `static/js/dispatch_center.js` 末尾，删除 HTML 中的内联 `<script>` 块。

### 62 个函数清单

```
safeFetch         (L1550)  — 工具函数
sf               (L1562)  — 工具函数
safeJson         (L1572)  — 工具函数
loadQualityTab   (L1582)  — 质检管理
loadQualityRecords (L1583) — 质检管理
reviewQi         (L1611)  — 质检管理
showQiVersions   (L1618)  — 质检管理
showQiDetail     (L1626)  — 质检管理
closeQiModal     (L1659)  — 质检管理
qiChangeFilter   (L1662)  — 质检管理
loadScheduleTab  (L1670)  — 排产
loadMaterialDc   (L1702)  — 物料
loadReportRecords (L1741) — 报工记录
resetReportRecordFilter (L1841)
openRrEditModal  (L1848)
closeRrEditModal (L1861)
submitRrUpdate   (L1866)
openRrWithdrawModal (L1901)
closeRrWithdrawModal (L1911)
submitRrWithdraw (L1916)
openRrHistoryModal (L1934)
closeRrHistoryModal (L1977)
loadQualityRegression (L1987)  — 质检回归
resetQualityRegressionFilter (L2047)
openQrEditModal  (L2048)
closeQrEditModal (L2055)
submitQrUpdate   (L2056)
openQrWithdrawModal (L2064)
closeQrWithdrawModal (L2068)
submitQrWithdraw (L2069)
openQrHistoryModal (L2076)
closeQrHistoryModal (L2096)
loadMaterialRegression (L2104) — 物料回归
resetMaterialRegressionFilter (L2158)
openMrEditModal  (L2159)
closeMrEditModal (L2165)
submitMrUpdate   (L2166)
openMrWithdrawModal (L2172)
closeMrWithdrawModal (L2173)
submitMrWithdraw (L2174)
openMrHistoryModal (L2175)
closeMrHistoryModal (L2176)
loadOutsourceRegression (L2184) — 外协回归
resetOutsourceRegressionFilter (L2238)
openOrEditModal  (L2239)
closeOrEditModal (L2240)
submitOrUpdate   (L2242)
openOrWithdrawModal (L2243)
closeOrWithdrawModal (L2244)
submitOrWithdraw (L2245)
openOrHistoryModal (L2246)
closeOrHistoryModal (L2247)
loadScheduleRegression (L2253) — 排产回归
resetScheduleRegressionFilter (L2305)
openSrEditModal  (L2306)
closeSrEditModal (L2307)
submitSrUpdate   (L2308)
openSrWithdrawModal (L2309)
closeSrWithdrawModal (L2310)
submitSrWithdraw (L2311)
openSrHistoryModal (L2312)
closeSrHistoryModal (L2313)
```

---

## 二、重构目标

1. **消除 HTML 内联脚本**：删除 `dispatch_center.html` L1549~L2318 的 `<script>` 块（保留 L1542~L1548 的配置脚本）
2. **JS 统一到外部文件**：`dispatch_center.js` 成为唯一 JS 来源
3. **保持功能 100% 不变**：62 个函数逻辑原样迁移，无改动

---

## 三、实施步骤

### Step 1：提取 + 合并（预估 30 分钟）

```
1a: 读取 dispatch_center.html L1549~L2315 内容
1b: 读取 dispatch_center.js 末尾，确认文件结构
1c: 将 62 个函数追加到 dispatch_center.js 末尾
1d: 在函数前插入注释分隔：// === 回归测试模块 ===
1e: 保留 safeFetch/sf/safeJson（它们是回归函数依赖的工具）
```

### Step 2：清理 HTML 内联脚本（预估 15 分钟）

```
2a: 删除 dispatch_center.html L1549~L2315 的 <script>...</script> 块
2b: 保留 L1542~L1548（API_BASE / CONTAINER_CENTER_BASE / dispatch_center_labels.js / WECHAT_CLOUD_API_KEY）
2c: 确认 defer 加载顺序正确（dispatch_center.js defer → 内联配置 → 其他脚本）
```

### Step 3：功能验证（预估 30 分钟）

```
3a: 打开浏览器，访问调度中心
3b: 点击所有 24 个 Tab，确认切换正常
3c: 测试回归测试 Tab 的筛选/编辑/撤回/历史功能
3d: 检查浏览器控制台无 Error 级别错误
```

---

## 四、需要一并迁移的 API 常量

6 个 API 路径常量分散在 62 个函数之间，迁移时必须一并带走：

| 常量 | 行号 | 值 |
|------|------|-----|
| `QI_API` | L1579 | `/api/quality-inspection` |
| `RR_API` | L1736 | `/api/report_record` |
| `QR_API` | L1982 | `/api/quality_record` |
| `MR_API` | L2099 | `/api/material_record` |
| `OR_API` | L2179 | `/api/outsource_record` |
| `SR_API` | L2250 | `/api/schedule_record` |

迁移时这 6 行常量加到 62 个函数之前。

## 五、风险控制

| 风险 | 缓解 |
|------|------|
| 6 个 API 常量丢失 | 与 62 个函数一并迁移 |
| 外部 JS 浏览器缓存 | 追加 `?v=20260621` 版本戳 |
| 函数名冲突 | 全部 62 个函数名唯一，无冲突 |
| 内联 `window.API_BASE` 等配置丢失 | L1542~L1548 配置脚本保留在 HTML 中 |

---

## 六、工作量估算

| 步骤 | 时间 | 风险 |
|------|------|------|
| Step 1: 提取合并 | 30 分钟 | 低 |
| Step 2: 清理 HTML | 15 分钟 | 低 |
| Step 3: 功能验证 | 30 分钟 | 中 |
| **合计** | **~75 分钟** | |
