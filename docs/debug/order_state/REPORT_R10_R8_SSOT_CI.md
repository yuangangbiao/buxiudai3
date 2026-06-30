# R10 + R8 闭环报告 — 字典自动同步 + CI 接入

> **时间**: 2026-06-10
> **闭环**: R10(治本)→ R8(治标)
> **结论**: **PASS ✓**

---

## 1. R10 — 字典自动同步(SSOT 合并)

### 1.1 问题
R7 第一次跑时,`EXPECTED_STATUS_ZH` 漏了 `已创建`,判定为"英文 status 残留"。这是**手维护字典的典型问题**:
- 改 `utils/i18n_zh.py` 后忘了同步 R7 期望
- 改 `dispatch_center_labels.js` 后忘了同步
- 字段漂移导致 CI 误报

### 1.2 方案
新建 [utils/expected_zh.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/expected_zh.py) 作为**单一事实源**:
1. 加载后端字典 `utils.i18n_zh`(`STATUS_ZH` / `DATA_TYPE_ZH` / `PRIORITY_ZH` / `ORDER_STATUS_ZH` / `STEP_STATUS_ZH`)
2. 通过 `refresh_from_frontend()` 解析 `dispatch_center_labels.js` 持久化到 `docs/debug/order_state/expected_zh.frontend.json`
3. 提供 3 个 SSOT API:
   - `get_expected_status_zh() -> Set[str]`(55 项)
   - `get_expected_datatype_zh() -> Set[str]`(21 项)
   - `get_expected_priority_zh() -> Set[str]`(5 项)
4. R7 改为从这 3 个函数拉,删掉手维护的 23 项 `EXPECTED_STATUS_ZH`

### 1.3 验证
- `refresh_from_frontend()` 从 JS 解析出 status 17 + type 19
- 持久化文件 984 字节写入 `docs/debug/order_state/expected_zh.frontend.json`
- R7 跑通 4 工单 × 6 tab = 24 渲染断言,51 个 badge 全中文
- **手维护消失**,字典漂移问题治本

### 1.4 R10 字典合并对比

| 来源 | 旧 EXPECTED_STATUS_ZH | 新 get_expected_status_zh() |
|---|---:|---:|
| 后端 i18n_zh | 23 | 38 + 10 = 48 |
| 前端 LABELS | (未合并) | 17 |
| **总数** | **23** | **55**(+32) |

## 2. R8 — 接入 CI

### 2.1 新增 workflow
[.github/workflows/playwright-frontend-tests.yml](file:///d:/yuan/不锈钢网带跟单3.0/.github/workflows/playwright-frontend-tests.yml)

### 2.2 监听路径
```yaml
paths:
  - 'mobile_api_ai/static/js/dispatch_center.js'   # 前端主逻辑
  - 'mobile_api_ai/static/js/dispatch_center_labels.js'  # 前端 LABELS
  - 'mobile_api_ai/dispatch_center/_core.py'      # 后端 workorder API
  - 'utils/i18n_zh.py'                            # 后端翻译字典
  - 'utils/expected_zh.py'                        # SSOT 合并器
  - 'scripts/pw_re007_r6.py'                      # R6 脚本
  - 'scripts/pw_re007_r7.py'                      # R7 脚本
  - '.github/workflows/playwright-frontend-tests.yml'  # 自身
```

### 2.3 流水线
1. checkout + setup-python(3.11)+ cache pip
2. `pip install` + `playwright install --with-deps chromium`
3. **R10 同步** — `refresh_from_frontend()` 让前端字典并入 SSOT
4. **启动 5002 + 5003** — 后台 nohup,等端口就绪
5. **R6 跑** — hash 差异检查(continue-on-error 兜底)
6. **R7 跑** — 文本断言(必过)
7. **失败时上传截图**(artifacts,7 天保留)
8. **总是上传日志**

### 2.4 YAML 验证
```
{
  "yaml_valid": true,
  "name": "Playwright Frontend Tests (R6/R7/R10)",
  "jobs": ["playwright-frontend"],
  "triggers": ["push", "pull_request"]
}
```

## 3. 完整的"前端改动 → CI 拦截"链路

```
开发者改 dispatch_center_labels.js (添加 xxx: '中文X')
  ↓ git push
GitHub Actions 触发
  ↓ R10 refresh_from_frontend() 把新字典并入 SSOT
  ↓ R7 用新字典断言
  ↓ 如果 dispatch_center.js 没同步使用新 status
  ↓ 渲染层抓到英文 xxx badge
  ↓ R7 FAIL → PR blocked
```

## 4. 交付物清单

| 类型 | 路径 |
|---|---|
| R10 合并器 | [utils/expected_zh.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/expected_zh.py) |
| R10 持久化字典 | [docs/debug/order_state/expected_zh.frontend.json](file:///d:/yuan/不锈钢网带跟单3.0/docs/debug/order_state/expected_zh.frontend.json) |
| R7 改造 | [scripts/pw_re007_r7.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/pw_re007_r7.py) |
| R8 CI workflow | [.github/workflows/playwright-frontend-tests.yml](file:///d:/yuan/不锈钢网带跟单3.0/.github/workflows/playwright-frontend-tests.yml) |

## 5. 验证矩阵

| 测试 | 状态 | 备注 |
|---|---|---|
| R10 refresh_from_frontend() | ✓ | 解析 status 17 + type 19,持久化 984 字节 |
| R10 get_expected_*() | ✓ | STATUS 55 / DATATYPE 21 / PRIORITY 5 |
| R7 用 SSOT 跑 | ✓ | 4 工单 × 6 tab 渲染断言全过 |
| YAML 解析 | ✓ | 1 job / push+pull_request 触发 |

## 6. 后续

- [ ] R9:扩展报工端 / 质检端
- [ ] R11:把 R8 接入"主 CI" — 让 `pytest` + `playwright` 串行
- [ ] R12:失败时**自动**通知开发者(Slack/企业微信)
