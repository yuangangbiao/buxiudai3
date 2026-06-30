# INDEX v6.0.1 - 文档索引（6A 6 阶段归档总览）

> **任务名**: 包装入库 ↔ 成品库联动 + planned_qty_formula 公式修复 + log_status_change 6 参修补
> **版本**: v6.0.1（2026-06-16）
> **审计基线**: 100/100

---

## 1. 6A 阶段交付物

### 阶段 1 - Align（对齐）
- [ALIGNMENT_订单号与工序对应检查.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/ALIGNMENT_订单号与工序对应检查.md) — 业务理解 + 边界确认
- [ALIGNMENT_包装入库成品库联动.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/ALIGNMENT_包装入库成品库联动.md) — 包装入库联动需求分析 v2

### 阶段 2 - Architect（架构）
- [DESIGN_公式修复.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/DESIGN_公式修复.md) — 公式修复架构
- [DESIGN_包装入库成品库联动.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/DESIGN_包装入库成品库联动.md) — 包装入库联动架构 v6（含 mermaid 图、接口契约、异常处理）

### 阶段 3 - Atomize（原子化）
- [TASK_包装入库成品库联动.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/TASK_包装入库成品库联动.md) — 9 个原子任务分解

### 阶段 4 - Approve（审批）
- 设计文档 + 用户决策确认（"路径 A, 全部做完在停下来"）

### 阶段 5 - Automate（自动化执行）
- 9 个原子任务全部完成
- 34 个测试用例
- 5 份脚本（修补 + 迁移 + 验证 + 调试 + 端到端）

### 阶段 6 - Assess（评估）
- [ACCEPTANCE_公式修复.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/ACCEPTANCE_公式修复.md) — 8/8 原子任务 + 15/15 公式用例
- [ACCEPTANCE_包装入库联动_v6.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/ACCEPTANCE_包装入库联动_v6.md) — 9/9 任务 + 18/18 测试
- [ACCEPTANCE_Phase6验收.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/ACCEPTANCE_Phase6验收.md) — Phase 6 综合验收

### 阶段 7 - 文档归档
- [FINAL_包装入库联动+公式修复.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/FINAL_包装入库联动+公式修复.md) — 完整总结
- [TODO_包装入库联动+公式修复.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/TODO_包装入库联动+公式修复.md) — 待办事项
- [RELEASE_v6.0.1.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/RELEASE_v6.0.1.md) — 发布说明
- [DEPLOY_v6.0.1.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/DEPLOY_v6.0.1.md) — 部署指南
- **INDEX_v6.0.1.md** — **本文档（6A 6 阶段总览）**

---

## 2. 业务能力清单

| 业务流 | 新增/优化 |
|--------|----------|
| 报工 | QC 强校验 + finished_goods 自动联动 + 报工回退自动反向出库 |
| 库存 | finished_goods 数量自动维护（含旧数据恢复）|
| 发货 | 分批发货逻辑（仓库自动减少 + status 转换）|
| 订单 | 状态机 C 方案（QC → 包装入库 → 发货）|
| 排产 | planned_qty 公式正确（米转毫米+除节距，差 1000 倍修复）|
| 质检 | 桌面端预设 INSPECTION_ITEMS_BY_CATEGORY 实际检查项 |
| 监控 | 5008 同步单一触发 + log_status_change 6 参失败原因记录 |

---

## 3. 关键技术决策

| # | 决策 | 原因 |
|---|------|------|
| 1 | 强校验用 `SELECT FOR UPDATE` | 防止并发报工幻读 |
| 2 | 原子 SQL `quantity = quantity + X` | 防止 read-then-write 竞态 |
| 3 | `with conn.cursor()` 上下文管理器 | 自动关 cursor，避免资源泄漏 |
| 4 | 订单状态用工序名（"包装入库"）| 业务语义清晰，替代仓库名（"成品入库"）|
| 5 | `log_status_change` 6 参 + remark | 兼容 models/process.py 等多处异常分支调用 |

---

## 4. 审计历史

| 轮次 | 评分 | 修补项 | 状态 |
|------|:----:|--------|:----:|
| v1 | 62/100 | 12 | ❌ |
| v2 | 84/100 | 4 | ⚠️ |
| v3 | 83/100 | 2 | ⚠️ |
| v4 | 90/100 | 3 | ⚠️ |
| v5 | 98/100 | 1 | ✅ |
| v6 | 99/100 | 2（FOR UPDATE）| ✅ |
| **v6.0.1** | **100/100** | **0** | **✅** |

---

## 5. 快速导航

- **看改动**: [DESIGN_包装入库成品库联动.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/DESIGN_包装入库成品库联动.md) v6
- **看进度**: [ACCEPTANCE_Phase6验收.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/ACCEPTANCE_Phase6验收.md)
- **看发布**: [RELEASE_v6.0.1.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/RELEASE_v6.0.1.md)
- **看部署**: [DEPLOY_v6.0.1.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/DEPLOY_v6.0.1.md)
- **看待办**: [TODO_包装入库联动+公式修复.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/TODO_包装入库联动+公式修复.md)
- **看总结**: [FINAL_包装入库联动+公式修复.md](file:///d:/yuan/不锈钢网带跟单3.0/docs/订单号与工序对应检查/FINAL_包装入库联动+公式修复.md)
