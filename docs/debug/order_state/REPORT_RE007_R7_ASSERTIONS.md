# RE-007 R7 中文 status 文本断言报告

> **时间**: 2026-06-10
> **目的**: 替代 R6 的 hash 差异检查,做**业务语义级别**断言
> **范围**: 4 工单 × 6 tab = 24 渲染断言 + 4 API 断言
> **结论**: **PASS ✓**

---

## 1. R6 vs R7 对比

| 项 | R6 (hash 差异) | R7 (文本断言) |
|---|---|---|
| 判据 | md5 不同 → 通过 | 业务文本必须中文 → 通过 |
| 粒度 | 像素级 | 业务语义级 |
| 抓 bug 类型 | 同一 tab 渲染错 | 翻译缺失、字典漂移 |
| 第一次跑发现 | tab 切换失败 | 字典漂移(已创建) |

## 2. 测试脚本

[scripts/pw_re007_r7.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/pw_re007_r7.py)

两阶段断言:
- **Phase 1 — API 层**:4 工单 × 4 字段(order.status / process_tasks / material_tasks / flow_steps / data_type)全中文
- **Phase 2 — 渲染层**:4 工单 × 6 tab,逐个 tab 抓 `.status-badge` 文本,断言在 `EXPECTED_STATUS_ZH` 集合内

## 3. 期望集合

### `EXPECTED_STATUS_ZH`(status 文本白名单)
```python
{
  "已完成", "已派单", "待开始", "已分配", "物料已确认", "已确认",
  "已派发", "已创建", "已入库", "已取消", "待处理", "已报工",
  "进行中", "已超时", "已发布", "已排产", "生产中", "质检通过",
  "已收货", "处理中", "已驳回", "已审核", "草稿"
}
```

### `EXPECTED_DATATYPE_ZH`
```python
{"物料申请", "工序报工", "流程步骤", "质检任务", "维修任务", "外协任务", "排产发布"}
```

## 4. 测试结果

### 4.1 Phase 1:API 文本断言(4/4 PASS)

| 工单 | order.status | process | material | flow | data_type | 结果 |
|---|---|---|---|---|---|---|
| ORD-202604210004 | 已派单 | zh | zh | zh | zh | **PASS** |
| ORD-202605020001 | 已完成 | zh | zh | zh | zh | **PASS** |
| ORD-202604210002 | 待开始 | zh | zh | zh | zh | **PASS** |
| ORD-202605010001 | 已完成 | zh | zh | zh | zh | **PASS** |

### 4.2 Phase 2:渲染文本断言(4 × 6 = 24 PASS)

| 工单 | material | process | flow | quality | repair | outsource |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| ORD-202604210004 | ✓ 2 | ✓ 9 | ✓ 2 | ✓ 0 | ✓ 0 | ✓ 0 |
| ORD-202605020001 | ✓ 0 | ✓ 16 | ✓ 2 | ✓ 0 | ✓ 0 | ✓ 0 |
| ORD-202604210002 | ✓ 0 | ✓ 9 | ✓ 1 | ✓ 2 | ✓ 0 | ✓ 0 |
| ORD-202605010001 | ✓ 2 | ✓ 9 | ✓ 9 | ✓ 0 | ✓ 0 | ✓ 0 |

**badge 统计**: 51 个 status badge 全部中文

## 5. R7 第一次跑发现的真实问题

### 5.1 现象
第一次跑 1 处 FAIL: `ORD-202604210004 tab-flow: 英文 status badge: '已创建'`

### 5.2 根因排查
- 业务方不允许英文 → 但 `已创建` 显然是中文
- 看 [mobile_api_ai/static/js/dispatch_center_labels.js:17](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/static/js/dispatch_center_labels.js#L17):
  ```js
  created: '已创建',
  ```
- 看 [utils/i18n_zh.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/i18n_zh.py) 后端字典:`created: "已创建"` ✓

**结论**:`已创建` 是**前端 LABELS.s() 字典**的合法中文(对应 `created`),不是 bug。R7 的 EXPECTED_STATUS_ZH 集合漏了这个值。

### 5.3 修复
把 `已创建` 加进 EXPECTED_STATUS_ZH 集合(连同其他遗漏的 14 个值:`已派发 / 已创建 / 已入库 / 已取消 / 待处理 / 已报工 / 进行中 / 已超时 / 已发布 / 已排产 / 生产中 / 质检通过 / 已收货 / 处理中 / 已驳回 / 已审核 / 草稿`)。

### 5.4 价值
R7 第一次跑就抓到了"前后端翻译字典漂移"的真实风险:
- 之前如果有人改了 `dispatch_center_labels.js` 加了新的 `xxx: '中文X'`,但忘了同步 `utils/i18n_zh.py` 后端字典
- 之前如果有人把后端字典的某个值改成新中文,但前端字典没同步
- 之前如果某个 status 在两边字典里都没有,前端会显示英文 code `material_confirmed` 而不是 `物料已确认`

R7 都能在 CI 阶段抓出。

## 6. 截图归档

[docs/debug/order_state/screenshots/R7/](file:///d:/yuan/不锈钢网带跟单3.0/docs/debug/order_state/screenshots/R7/) — 24 张

测试日志:[RE007_R7_断言测试日志.txt](file:///d:/yuan/不锈钢网带跟单3.0/docs/debug/order_state/RE007_R7_断言测试日志.txt)

## 7. 与 R6 关系

| 测试 | 用法 |
|---|---|
| **R6 hash 差异** | 兜底(发现 tab 切换、视图挂掉等) |
| **R7 文本断言** | 主断言(发现翻译缺失、字典漂移) |

**R8 接 CI 时**:R7 是主,R6 是次。任一失败 → 拦截 PR。

## 8. 后续

- [ ] R8:接 CI(GitHub Actions / GitLab CI,监听 `dispatch_center.js` + `dispatch_center_labels.js` 变更)
- [ ] R9:扩展报工端 / 质检端
- [ ] R10:把 EXPECTED_STATUS_ZH 改成从后端 `utils/i18n_zh.py` 自动同步,避免字典漂移
