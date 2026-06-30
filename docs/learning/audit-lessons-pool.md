# 悲观审计经验池 (Pessimistic Audit Lessons Pool)

> 状态: **已合并** (3 项模式级条目已自动加入检查清单)

## 📋 已合并条目 (自动化检查)

### 🟡 模式 #1: innerHTML 拼接用户数据必须 escapeHtml

| 字段 | 值 |
|------|-----|
| 出现次数 | 1 |
| 触发条件 | 任何 `${user_data}` 插入 `innerHTML` 模板字符串 |
| 防御模式 | `escapeHtml(${o.field})` 或改用 `textContent` |
| 检查脚本 | `grep -n '\${o\.[a-z_]*}' *.html` 全部应含 `escapeHtml` 或 `Number()` |
| 发现日期 | 2026-06-22 |
| 状态 | ✅ 已合并 |

**白名单 (安全)**:
- `style="width:${pct}%"` 中 pct 来自 Math.round() (数字)
- `style="background:${escapeHtml(color)}"` 必须 escape
- `Number(o.field) || 0` 强制转数字

### 🟡 模式 #2: int(request.args) 必须 try/except + 范围校验

| 字段 | 值 |
|------|-----|
| 出现次数 | 1 |
| 触发条件 | `int(request.args.get('limit', N))` 类转换 |
| 防御模式 | `safe_int(value, default, min, max)` 工具函数 |
| 检查脚本 | `grep -n 'int(request.args' *.py` 全部应改为 `safe_int()` |
| 发现日期 | 2026-06-22 |
| 状态 | ✅ 已合并 |

**危险信号**:
- `int(x)` 无 try/except → 攻击者传 `?limit=abc` 直接 500
- 无范围校验 → `?limit=99999999999` 性能崩溃
- 负数/0 → 异常

### 🟢 模式 #3: pagehide + beforeunload 清理 setInterval

| 字段 | 值 |
|------|-----|
| 出现次数 | 1 |
| 触发条件 | `setInterval(..., 30000)` 自动刷新 |
| 防御模式 | `const id = setInterval(...); window.addEventListener('pagehide', () => clearInterval(id))` |
| 检查脚本 | `grep -l 'setInterval' templates/*.html` 全部应含 `pagehide` 清理 |
| 发现日期 | 2026-06-22 |
| 状态 | ✅ 已合并 |

**问题**:
- 页面跳转后 setInterval 仍在跑 → 内存泄漏
- 浏览器返回时旧 interval 与新 interval 冲突

## 📚 待合并条目

(目前 0 条待合并, 下次审计后追加)

## 🛠️ 自动化检查工具

### Python 静态检查
```python
# 检查 1: innerHTML 必须 escapeHtml
for tmpl in glob('templates/*.html'):
    content = read(tmpl)
    for match in re.finditer(r'\$\{o\.[a-z_]+\}', content):
        if not preceded_by_escapeHtml(content, match.start()):
            audit_fail(f"{tmpl}:{match.start()} innerHTML 缺 escapeHtml")

# 检查 2: int(request.args) 必须 safe_int
for py in glob('**/_core.py'):
    content = read(py)
    for match in re.finditer(r'int\(request\.args', content):
        audit_fail(f"{py}:{match.start()} int(request.args) 缺 try/except")

# 检查 3: setInterval 必须有清理
for tmpl in glob('templates/*.html'):
    content = read(tmpl)
    if 'setInterval' in content and 'clearInterval' not in content:
        audit_fail(f"{tmpl}: setInterval 缺 clearInterval 清理")
```

## 📊 模式级触发记录

| 日期 | 模式 | 触发轮次 | 修复状态 |
|------|------|:--------:|:--------:|
| 2026-06-22 | innerHTML XSS | 第 1 轮 | ✅ 已修 |
| 2026-06-22 | int() 崩溃 | 第 1 轮 | ✅ 已修 |
| 2026-06-22 | setInterval 泄漏 | 第 1 轮 | ✅ 已修 |
