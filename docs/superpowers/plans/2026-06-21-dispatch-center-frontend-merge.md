# 调度中心前端内联 JS 合并实施计划

> **For agentic workers:** 使用 `superpowers:executing-plans` 或逐任务执行。

**目标**：将 `dispatch_center.html` L1549~L2315 的 62 个内联 JS 函数合并到 `static/js/dispatch_center.js` 末尾，删除 HTML 中的内联脚本块。

**架构**：HTML 保留外联 JS 引用，内联回归测试函数移入外部 JS 文件，版本戳更新强制刷新。

**关键文件**：
- `mobile_api_ai/templates/dispatch_center.html` — 删除内联脚本（L1549~L2315）
- `mobile_api_ai/static/js/dispatch_center.js` — 追加 62 函数 + 6 API 常量，更新版本戳

---

## 实施步骤

### Task 1：读取内联 JS 内容

**文件**：`dispatch_center.html` L1549~L2315

- [ ] **Step 1: 确认内联 JS 起始行**

确认 `dispatch_center.html` L1549 是 `<script>` 标签开始。

- [ ] **Step 2: 读取内联 JS 内容**

使用 Read 工具读取 `dispatch_center.html` L1549~L2315。预期：
- L1549: `<script>`
- L1550: `function safeFetch(...)`
- L2313: `function closeSrHistoryModal()...`
- L2315: `</script>`

- [ ] **Step 3: 确认 HTML 文件总行数**

使用 Read 工具读取 `dispatch_center.html` 最后 5 行。预期：
- L2316: 空行
- L2317: `</body>`
- L2318: `</html>`

---

### Task 2：读取外部 JS 末尾

**文件**：`dispatch_center.js` 末尾

- [ ] **Step 1: 读取 dispatch_center.js 末尾**

使用 Read 工具读取 `dispatch_center.js` L4876~L4882。预期：
- L4876: `// === 初始化 ===`
- L4881: `switchTab('overview');`

---

### Task 3：合并 JS 到外部文件

**文件**：`dispatch_center.js`

- [ ] **Step 1: 在 dispatch_center.js 末尾追加内容**

使用 SearchReplace 工具，在 `// === 初始化 ===`（L4876）之前插入：

```javascript

// === 回归测试模块 ===
// 从 dispatch_center.html L1549~L2315 迁移，2026-06-21

var QI_API = '/api/quality-inspection';
var RR_API = '/api/report_record';
var QR_API = '/api/quality_record';
var MR_API = '/api/material_record';
var OR_API = '/api/outsource_record';
var SR_API = '/api/schedule_record';

function safeFetch(url, options) {
  return fetch(url, options).then(function(r) {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).catch(function(e) {
    console.error('请求失败:', url, e);
    alert('❌ 网络请求失败，请稍后重试');
    throw e;
  });
}
function sf(url, options, fallbackMsg) {
  return safeFetch(url, options).catch(function(e) {
    if (fallbackMsg) alert(fallbackMsg);
    return null;
  });
}
function safeJson(r) {
  return r.ok ? r.json() : r.json().then(function(d) { throw Object.assign(new Error(d.message || '请求失败'), { response: r }); }).catch(function(e) { throw e; });
}
```

然后追加所有 62 个函数（从 L1582 `loadQualityTab` 到 L2313 `closeSrHistoryModal`）。

**注意**：完整内容直接从 HTML 文件中复制，不要手动输入。使用 Read 工具读取后拼接。

---

### Task 4：更新 HTML 清除内联脚本

**文件**：`dispatch_center.html`

- [ ] **Step 1: 确认 HTML 中内联脚本块边界**

确认：
- L1548: `<script src="/static/js/dispatch_center.js?v=20260617.1" defer></script>`
- L1549: `<script>`（内联脚本开始）
- L2315: `</script>`（内联脚本结束）
- L2316: 空行

- [ ] **Step 2: 删除内联脚本块**

使用 SearchReplace 工具，将以下内容从 HTML 中删除（L1549~L2315）：

原始内容（L1549~L2315）：

```html
<script>
[62个函数 + 6个API常量]
</script>
```

替换为：空行

- [ ] **Step 3: 更新 dispatch_center.js 版本戳**

将 `dispatch_center.html` L1548 中的 `?v=20260617.1` 更新为 `?v=20260621.1`。

---

### Task 5：验证

- [ ] **Step 1: 语法检查**

运行：`py -m py_compile mobile_api_ai/templates/dispatch_center.html`（HTML 非 Python，无需编译，跳过）

- [ ] **Step 2: 确认 HTML 行数减少**

使用 grep 或 wc 确认 `dispatch_center.html` 行数从 2318 行减少到约 1548 行（减少约 767 行）。

- [ ] **Step 3: 确认 dispatch_center.js 行数增加**

使用 wc 确认 `dispatch_center.js` 从 4882 行增加到约 5650 行（增加约 767 行）。

- [ ] **Step 4: 确认文件结构正确**

在 HTML 中搜索 `safeFetch`，确认只有外部 JS 引用，无内联版本。
在 HTML 中搜索 `</script>`，确认只有 3 处（L1542、L1546、L1547），无内联脚本残留。

---

### Task 6：提交

```bash
git add mobile_api_ai/templates/dispatch_center.html mobile_api_ai/static/js/dispatch_center.js
git commit -m "refactor(dispatch_center): 合并内联回归测试JS到外部文件"
```
