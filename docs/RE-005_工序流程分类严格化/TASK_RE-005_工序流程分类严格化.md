# RE-005 工序/流程/物料/质检/外协 分类严格化 — TASK

> **工单号**: RE-005
> **开工日期**: 2026-06-10
> **目标**: 把"工序任务"卡片里实际显示的"流程步骤名"问题彻底修复,严格定义 10 个 data_type 枚举 + 6 张卡片归类,杜绝后续混淆。
> **影响范围**: `data_packages` 表 + `dispatch_center/_core.py` + 前端 `dispatch_center.js` + `dispatch_center_labels.js` + `utils/data_type_contract.py` + 迁移脚本

---

## 一、问题回顾

1. 调度中心工单详情"工序任务"卡片实际显示的是 **流程步骤名**(工单发布/排产制定/...)，而**不是物理工序**(焊接眼镜网/穿曲轴/...)。
2. 根因:`data_type='report'` 这一旧值同时承载了两种语义,API 加载逻辑没有区分。
3. 旧 data_type 大杂烩:`report / material / material_purchase / purchase / quality / quality_inspection / repair / outsource / production / config`,9+ 个标签指向 6 类业务实体,边界模糊。

---

## 二、任务清单(原子化)

| # | 任务 | 状态 | 交付物 |
|---|------|:----:|--------|
| P0 | 阅读 DATA_TYPE_CONTRACT + 确认服务状态 | ✅ | 5003 端口在跑 _core.py v2026-06-10 |
| P1 | 概念区分(工序/流程/物料/质检/外协)梳理 | ✅ | DATA_TYPE_CONTRACT.md §1 |
| P2 | 数据库迁移:47 条 → 46 条新 data_type | ✅ | `migrate_data_type_to_v1.py` 实际执行 0 违反 |
| P3 | 新契约文档 v1.0 | ✅ | `docs/DATA_TYPE_CONTRACT.md` (10 enum + 4 模板) |
| P4 | `_core.py` 加载逻辑按新契约归类 | ✅ | `list_processes` / `workorder_detail` 改写 |
| P5 | 前端改造:`dispatch_center.js` 加 flow_steps 卡片 + tab | ✅ | 6 tab + renderFlowStepTable() |
| P6 | 单测:契约判定 + API 归类回归 | ✅ | 41/41 通过,覆盖率 92% |
| P7 | Playwright 验证 6 张卡片准确 | ✅ | 工单 ORD-202604210004 截图 7 张 |
| P8 | 归档:CODE_WIKI + REGRESSION_REPORT + 决策日志 | ⏳ | 本目录 + REGRESSION_REPORT_P8.md |

---

## 三、新契约一句话总结

```
10 个 data_type 严格枚举:
  process_report / flow_step / flow_production
  material_request / material_pickup / material_buy
  quality_task / equipment_repair / outsource_task
  config

6 张任务卡片(互不重叠):
  工序报工 / 流程进度 / 物料任务 / 质检任务 / 维修任务 / 外协任务
```

---

## 四、关键决策(决策日志)

- D1:**用 B 方案(数据修复)而非 A(容忍)**:旧 data_type 拆得太碎,且让 UI 自适应不可行,坚持契约唯一来源。
- D2:**'report' 拆 5 类**:物理工序 / 流程步骤 / 排产 / 质检 / 物料,用 `content` 字段兜底判定 4 条历史契约违反。
- D3:**物理工序字典唯一**:`process_names` 表为唯一白名单,API 加载时 5min 缓存。
- D4:**流程步骤固定 4 模板**:`PROCESS_FLOW_TEMPLATES` 字典,禁止运行时拼接。
- D5:**前端 tab 与卡片一致**:"工序报工"与"流程进度"分离,杜绝"工序任务"杂烩展示。
- D6:**legacy 兼容保留**:`LEGACY_TO_NEW` 字典保留 1-2 版本过渡期,前端 LABELS 双轨展示。

---

## 五、关键文件路径

| 路径 | 角色 |
|------|------|
| `docs/DATA_TYPE_CONTRACT.md` | 契约文档(v1.0 唯一) |
| `utils/data_type_contract.py` | 契约判定核心模块 |
| `scripts/migrations/migrate_data_type_to_v1.py` | 数据迁移脚本 |
| `mobile_api_ai/dispatch_center/_core.py` | 加载归类逻辑 |
| `mobile_api_ai/static/js/dispatch_center.js` | 前端 6 卡片 + 6 tab |
| `mobile_api_ai/static/js/dispatch_center_labels.js` | 文案 LABELS |
| `tests/unit/utils/test_data_type_contract.py` | 单测(41 用例) |
| `scripts/p7_verify_six_cards.py` | Playwright 验证 |
| `docs/playwright/03_tab_*.png` | 6 张卡片截图证据 |

---

## 六、回归影响

| 维度 | 评估 |
|------|------|
| 数据库 schema | 无变更(只 update data_type 列) |
| API 路径 | 无变更(只多返回 `flow_steps` / `flow_production` 字段) |
| 前端向后兼容 | 双轨(新命名 + 旧值兼容字典) |
| 旧客户端 | 数据正常,UI 不显示新字段 |
| 新客户端 | 享受 6 卡片严格分类 |
| 单测 | 41/41 通过,覆盖率 92% |
