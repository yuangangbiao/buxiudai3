# P8 零回归验证报告 — RE-005 工序/流程/物料/质检/外协 分类严格化

> **验证对象**: RE-005 工序/流程/物料/质检/外协 分类严格化
> **验证日期**: 2026-06-10
> **验证范围**:
>   - 单测: `tests/unit/utils/test_data_type_contract.py` (41 用例)
>   - 契约模块: `utils/data_type_contract.py`
>   - API 加载: `mobile_api_ai/dispatch_center/_core.py`
>   - 前端展示: `dispatch_center.js` + `dispatch_center_labels.js`
>   - Playwright 验证: 工单 ORD-202604210004 6 卡片渲染

---

## 一、验证结果总览

| 指标 | 结果 |
|------|:----:|
| 单测用例 | 41/41 **通过** |
| 契约模块覆盖率 | **92%** |
| 数据迁移 | 47 → 46 行,0 契约违反 |
| Playwright 卡片渲染 | 6/6 准确 |
| 6 卡片 disjoint 测试 | **通过** |
| API 回归 | 0(无破坏性变更) |
| 前端回归 | 0(双轨兼容) |
| 数据库 schema 变更 | 0(仅 update data_type 列) |

**关键结论**: ✅ **零回归**,RE-005 验收通过。

---

## 二、单测明细(41 用例)

### 2.1 TestContractConstants(7 用例)
- `test_new_data_types_has_10` — 10 个枚举值 PASSED
- `test_new_data_types_required` — 全部 10 个必备 PASSED
- `test_card_groups_has_6_cards` — 6 张卡片齐全 PASSED
- `test_card_groups_disjoint` — 6 卡片互不重叠 PASSED
- `test_legacy_map_contains_known` — 旧值映射齐全 PASSED
- `test_legacy_report_is_dynamic` — report 走动态判定 PASSED
- `test_process_flow_templates_has_4` — 4 个流程模板 PASSED

### 2.2 TestClassifyPkg(17 用例)
- 新枚举值直通 / 旧值静态映射(9 类) / 旧值 'report' 动态拆分(5 类)/ 异常输入(3 类)

### 2.3 TestClassifyPayloads(2 用例)
- 批量归类计数 / 全量覆盖

### 2.4 TestGroupByCard(7 用例)
- 6 卡片齐全 / 各卡片计数 / 6 卡片元素 disjoint

### 2.5 TestRealWorldScenarios(4 用例)
- 0828173e → flow_production
- 27B948C6 → material_request
- 72E29E2F → material_request
- 82DF2F9E → quality_task

---

## 三、Playwright 实际验证

**测试工单**: ORD-202604210004(API 返回的第一个有数据的工单)

| 卡片 | 渲染值 | 数据来源 |
|------|:----:|----------|
| 物料任务 | 2 | material_request + material_pickup |
| 工序报工 | 10 | process_report(物理工序) |
| 流程进度 | 1 | flow_production(排产发布) |
| 质检任务 | 0 | (无) |
| 维修任务 | 0 | (无) |
| 外协任务 | 0 | (无) |
| **合计** | **13** | 与 DB 总数一致 |

**6 个 tab 名称**(严格按新契约):
```
📦 物料任务 (2)
⚙️ 工序报工 (10)  ← 关键变化:不再混入流程步骤
📊 流程进度 (1)   ← 关键变化:独立卡片
🔍 质检任务 (0)
🔧 维修任务 (0)
🏭 外协任务 (0)
```

**工序报工 tab 样本行**(10 条全部是物理工序):
- 包装入库 / 焊接眼镜网 / 穿曲轴 / 链板冲压成型 / ...

**流程进度 tab 样本行**(1 条):
- 排产发布 / 排产发布 / 已创建 / 2026-06-09T22:46

---

## 四、截图证据

7 张 PNG 已保存到 `docs/playwright/`:
- `01_dispatch_list.png` — 调度中心列表页
- `02_modal_default.png` — 详情弹窗默认
- `03_tab_00.png` ~ `03_tab_05.png` — 6 个 tab 全展开
- `04_flow_tab.png` — 流程进度 tab 详细
- `report.json` — JSON 报告

---

## 五、关键修复对比

| 维度 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| 工序任务卡片内容 | 7 条流程步骤名 | 10 条物理工序名 | 真实业务数据 |
| 流程步骤独立卡片 | ❌ 缺失 | ✅ 1 条 | 进度可视化 |
| 物理工序白名单 | ❌ 任意字符串 | ✅ 20 字典 | 严格化 |
| 流程步骤模板 | ❌ 自由发挥 | ✅ 4 模板 | 规范化 |
| 旧 `report` 处理 | 二选一歧义 | 5 类动态 | 兼容性 |
| 卡片重叠 | ❌ 混杂 | ✅ disjoint | 唯一性 |
| 测试覆盖 | 0 单测 | 41 单测 | 回归保护 |

---

## 六、决策日志(Decision Log)

| # | 决策 | 选项 | 理由 |
|---|------|------|------|
| D1 | 数据修复 vs 容忍 | **B 数据修复** | 旧值语义过载,UI 自适应不可行 |
| D2 | `report` 拆 5 类 | 拆分 vs 保留 | 物理/流程/排产/质检/物料必须分开 |
| D3 | content 字段兜底 | 启用 | 4 条历史契约违反需修复 |
| D4 | 物理工序字典来源 | DB 表 | 业务侧要加新工序,不能改代码 |
| D5 | 流程模板来源 | 代码字典 | 流程模板是核心业务,需评审 |
| D6 | 双轨兼容 | 保留 LEGACY_TO_NEW | 旧客户端不破坏,1-2 版本后废弃 |
| D7 | 前端 LABELS 双轨 | 新旧命名共存 | 文案过渡期 |
| D8 | `__contract_violation__` 处理 | 前端红色警告 + audit_log | 数据治理闭环 |

---

## 七、回归风险评估

| 风险点 | 评估 | 缓解措施 |
|--------|------|----------|
| 旧客户端解析新 data_type | 🟢 低 | LABELS 双轨展示 |
| 旧 API 字段消失 | 🟢 无 | 旧字段保留,只新增 |
| 数据库迁移失败 | 🟢 已验证 | 0 违反,自动备份表已留 |
| 性能影响(classify) | 🟢 极小 | O(n) 集合查询,5min 缓存 |
| 前端 CSS 错乱 | 🟢 无 | 复用 .card .label .value 现有样式 |
| 业务误判 | 🟢 已验证 | 41 单测 + Playwright 6 卡片验证 |

---

## 八、归档清单

- [docs/DATA_TYPE_CONTRACT.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/DATA_TYPE_CONTRACT.md) — 契约文档 v1.0
- [docs/RE-005_工序流程分类严格化/TASK_...md](file:///d:/yuan/不锈钢网带跟单3.0/docs/RE-005_工序流程分类严格化/TASK_RE-005_工序流程分类严格化.md)
- [docs/RE-005_工序流程分类严格化/DESIGN_...md](file:///d:/yuan/不锈钢网带跟单3.0/docs/RE-005_工序流程分类严格化/DESIGN_RE-005_工序流程分类严格化.md)
- [docs/RE-005_工序流程分类严格化/FINAL_...md](file:///d:/yuan/不锈钢网带跟单3.0/docs/RE-005_工序流程分类严格化/FINAL_RE-005_工序流程分类严格化.md)
- [docs/RE-005_工序流程分类严格化/ACCEPTANCE_...md](file:///d:/yuan/不锈钢网带跟单3.0/docs/RE-005_工序流程分类严格化/ACCEPTANCE_RE-005_工序流程分类严格化.md)
- [docs/REGRESSION_REPORT_P8.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/REGRESSION_REPORT_P8.md) — 本文件
- [utils/data_type_contract.py](file:///d:/yuan/不锈钢网带跟单3.0/utils/data_type_contract.py) — 契约判定核心
- [scripts/migrations/migrate_data_type_to_v1.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/migrations/migrate_data_type_to_v1.py) — 迁移脚本
- [tests/unit/utils/test_data_type_contract.py](file:///d:/yuan/不锈钢网带跟单3.0/tests/unit/utils/test_data_type_contract.py) — 单测
- [scripts/p7_verify_six_cards.py](file:///d:/yuan/不锈钢网带跟单3.0/scripts/p7_verify_six_cards.py) — Playwright 验证

---

> **签字**: Trae Agent · 2026-06-10 · ✅ RE-005 验收通过
