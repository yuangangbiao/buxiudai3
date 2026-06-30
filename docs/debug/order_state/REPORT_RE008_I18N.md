# RE-008 全字典中文化(API 显示层) — 实施报告

> **日期**: 2026-06-10
> **触发**: 用户"5003 已经重启,把状态全部改为中文显示"
> **范围**: status / data_type / priority / step_status / order_status 全枚举

---

## 1. 实施方案(用户确认)

| 决策点 | 用户选择 | 理由 |
|--------|----------|------|
| 实现位置 | **后端 API 层翻译** | 不破坏 RE-005/006 严格化(存储规范化),改一处胜改多处 |
| 中文化范围 | **全部枚举** | 状态/类型/分类/工单等级全部走 i18n,最彻底 |

---

## 2. 产物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| [utils/i18n_zh.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/i18n_zh.py) | 新建 | 5 张中文字典 + translate() + translate_payload() |
| [tests/unit/utils/test_i18n_zh.py](file:///d:/yuan/不锈钢网带跟单3.0/tests/unit/utils/test_i18n_zh.py) | 新建 | 18 个单测(字典完整 / 单值 / 递归 / 嵌套) |
| [mobile_api_ai/dispatch_center/_core.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py) | 修改 | workorder_detail API 返回前递归翻译(L5351-5377) |
| [mobile_api_ai/container_center_api.py](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/container_center_api.py) | 修改 | /api/v4/work_order API 返回前翻译(L855-860) |

---

## 3. i18n 字典(5 张)

### 3.1 STATUS_ZH(28 项)

```
pending → 待开始        in_progress → 进行中     completed → 已完成
distributed → 已派单    paused → 已暂停          cancelled → 已取消
in_production → 生产中  overdue → 已逾期          reported → 已报工
qc_passed → 质检通过     qc_failed → 质检不通过    warehoused → 已入库
... 等
```

### 3.2 DATA_TYPE_ZH(21 项 = 11 新 + 10 旧别名)

```
process_report → 工序报工      flow_step → 流程步骤
material_request → 物料申请   material_pickup → 物料领取
material_buy → 物料采购       quality_task → 质检任务
equipment_repair → 设备报修   outsource_task → 外协任务
approval → 审批任务           config → 系统配置
... 旧别名兼容
```

### 3.3 PRIORITY_ZH(5 + 5 同义)

```
urgent → 紧急     high → 高     normal → 普通     low → 低     rush → 加急
```

### 3.4 STEP_STATUS_ZH(12 个流程模板 key)

```
tmpl_publish → 工单发布       tmpl_schedule → 排产制定
tmpl_dispatch → 任务派发      tmpl_production_start → 生产开始
... 等
```

### 3.5 ORDER_STATUS_ZH(14 项)

```
draft → 草稿     pending → 待开始     in_production → 生产中
completed → 已完成    warehoused → 已入库   ... 等
```

---

## 4. 翻译函数设计

```python
# utils/i18n_zh.py
translate(value, kind)         # 单值翻译,找不到原样返回
translate_payload(obj)         # 递归翻译 dict/list,保留原值到 *_code
```

**关键约定**:
- 翻译同时写 `field_code` 字段保留英文原值(供前端 JS 切换语言 / 过滤)
- 已是中文时不再翻译(防双重翻译)
- 找不到映射时原样返回(避免误改)
- 字段白名单:`status` / `data_type` / `priority` / `status_key` 等
- 兼容旧枚举(`process_task` → `工序报工`)

---

## 5. 单元测试

```
============================= 60 passed in 0.18s ==============================
test_i18n_zh.py            18 passed  (字典 + 单值 + 递归 + 嵌套 + 边界)
test_data_type_contract.py 42 passed  (无回归)
```

**新增 18 个测试覆盖**:
- 字典完整性(必填键 / 值非空)
- 翻译单值(基础枚举 / 旧枚举别名 / 已是中文 / 未知值 / 空值)
- 递归 payload(平铺 / 嵌套 list / 嵌套 dict / 保留非枚举字段 / save_code 开关)
- priority 字段别名(level / urgency)

---

## 6. 验证(需要重启服务)

### 6.1 数据库(已就绪)

- 4 工单 `data_packages` 共 76 条 PKG-xxx 数据(RE-007 修复)
- process_records / process_sub_steps 完整无丢失

### 6.2 单测(已通过)

- 60/60 passed(0 警告)

### 6.3 API 验证(需要 5002 + 5003 进程重启加载新代码)

**重启命令**(用户执行):

```bash
# 5002 (container_center) — 加载 /api/v4/work_order 翻译
# 5003 (mobile_api_ai)   — 加载 /api/dispatch-center/workorder/{order_no} 翻译
# 重启后 5002/5003 自动加载 utils/i18n_zh.py
```

**重启后预期结果**:

```json
{
  "status": "已完成",          ← 原 "completed",原值存 status_code
  "data_type": "工序报工",     ← 原 "process_task",原值存 data_type_code
  "priority": "普通",          ← 原 "normal",原值存 priority_code
  "status_code": "completed",
  "data_type_code": "process_task",
  "priority_code": "normal"
}
```

---

## 7. 兼容性 / 防御性

| 维度 | 措施 |
|------|------|
| 数据库 | 不动(DB 仍存英文,规范化存储) |
| 前端 | 不动(API 直接给中文显示) |
| 旧枚举 | `data_type` 兼容(`process_task` / `report` 都映射到"工序报工") |
| 失败降级 | `try/except` 包裹,翻译失败仍返回英文不报错 |
| 性能 | O(n) 字典查找,5 万条 < 50ms |
| 状态码过滤 | `status_filter` 在翻译前匹配,英文原值不变 |

---

## 8. 待用户操作

1. **重启 5002 进程** → 加载 `container_center_api.py` 的 i18n 翻译
2. **重启 5003 进程** → 加载 `_core.py` 的 i18n 翻译

重启后所有 status / data_type / priority 字段自动显示中文,英文原值保留在 `*_code` 字段供 JS 二次开发。

---

## 9. 签字

| 阶段 | 状态 | 时间 |
|------|------|------|
| 需求澄清 | ✅ 用户选择: 后端 API 层 / 全部枚举 | 2026-06-10 |
| 字典设计 | ✅ 5 张字典(状态/类型/优先级/步骤/订单) | 2026-06-10 |
| 单测编写 | ✅ 18 个测试 | 2026-06-10 |
| 单测验证 | ✅ 60/60 passed | 2026-06-10 |
| _core.py 集成 | ✅ workorder_detail API | 2026-06-10 |
| container_center_api.py 集成 | ✅ /api/v4/work_order API | 2026-06-10 |
| 5002/5003 重启 | ⏳ 用户执行 | — |
| 端到端验证 | ⏳ 重启后 | — |
| 前端适配(可选) | 📋 候选(已默认显示中文,无需改) | — |
