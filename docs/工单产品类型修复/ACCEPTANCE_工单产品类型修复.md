# ACCEPTANCE — 工单产品类型修复

> **任务名**：workorder-product-type-fix
> **方案**：B+C 并行
> **创建日期**：2026-06-09
> **最后更新**：2026-06-09（骨架，待执行后填充）

---

## 完成度（动态更新）

> **完成度公式**：已完成的验收标准数 / 总验收标准数

| 阶段 | 完成度 | 主线目标 | 状态 |
|------|--------|---------|------|
| Phase 0 上下文对齐 | 6/6 (100%) | ✅ 完成 | 已完成 |
| Phase 1 需求分析 | 14/14 功能点定义 | ✅ 完成 | 已完成 |
| Phase 2 设计 + 审计 + 决策 | 91/100 分 + 0 CRITICAL | ✅ 完成 | 已完成 |
| Phase 3 任务原子化 | 18/18 任务定义 | ✅ 完成 | 已完成 |
| T1 DDL: work_order_history | 代码+commit ✅ / 实机验证 ⏸️ | 部分完成 | **已 commit，挂起** |
| Phase 4 编码（T2-T18） | 0/17 任务 | ⏸️ 挂起 | **暂停等环境** |
| Phase 5 测试 | 0/12 边界用例 | ⏳ 待启动 | 待执行 |
| Phase 6 悲观审计 | 0/100 分 | ⏳ 待启动 | 待执行 |
| Phase 7 零回归 | 0/393 路由对比 | ⏳ 待启动 | 待执行 |
| Phase 8 验收 | — | ⏳ 待启动 | 待执行 |
| Phase 9 归档 | — | ⏳ 待启动 | 待执行 |

**当前总体完成度**：5/9 阶段完成（56%），T1 代码完成+commit 完成，**实机验证挂起**

---

## 主线目标

| # | 目标 | 状态 |
|---|------|------|
| 1 | 修复存量数据（ORD-202604210004 等所有漂移订单） | ⏳ 待启动 |
| 2 | 止血未来增量（产品类型禁止隐式覆盖） | ⏳ 待启动 |
| 3 | 监控告警 5 类事件推送到 苑岗彪 企微 | ⏳ 待启动 |
| 4 | E2E 集成测试 100% 通过 | ⏳ 待启动 |
| 5 | P6 悲观审计 100 分 + 0 全部等级 | ⏳ 待启动 |

---

## 已验证项（按 T 编号累积）

| 任务 | 状态 | 证据 |
|------|------|------|
| T1 (DDL) | ✅ 代码 / ⏸️ 验证 | commit `8995e883`，3 文件 291 行 |
| T2 (supersede 实现) | ⏳ | — |
| T3 (publish_report 集成) | ⏳ | — |
| T4 (publish_material 集成) | ⏳ | — |
| T5 (register 只读) | ⏳ | — |
| T6 (confirm_schedule 不覆盖) | ⏳ | — |
| T7 (auto_publish 补 product_type) | ⏳ | — |
| T8 (process_v2 修语法错) | ⏳ | — |
| T9 (change_product_type API) | ⏳ | — |
| T10 (sync_bridge 事件) | ⏳ | — |
| T11 (扫描脚本) | ⏳ | — |
| T12 (修复脚本) | ⏳ | — |
| T13 (监控埋点) | ⏳ | — |
| T14 (告警接收人) | ⏳ | — |
| T15 (E2E 测试) | ⏳ | — |
| T16 (路由基线对比) | ⏳ | — |
| T17 (悲观审计) | ⏳ | — |
| T18 (验收归档) | ⏳ | — |

---

## 阻塞项

| # | 阻塞项 | 影响 | 缓解 |
|---|--------|------|------|
| 1 | 🚨 **本机 Python 进程 0xC0000409 崩溃** | T1 实机验证 + T2-T18 全部挂起 | 用户在能跑 Python 的环境跑前测+迁移；详见 [.workbuddy/docs/features/workorder-product-type-fix/ENV_DEBUG.md](file:///d:/yuan/不锈钢网带跟单3.0/.workbuddy/docs/features/workorder-product-type-fix/ENV_DEBUG.md) |
| 2 | 苑岗彪 企微 userid 未确认 | T14 实施受阻 | 启动前从 operators 表查询或在企微后台获取 |
| 3 | work_order_history 双写路径未确认 | T1 DDL 受阻 | 确认 MySQL + SQLite 两个连接字符串均可用 |
| 4 | 并发 register 真实场景压测环境 | T17 审计覆盖度 | 在测试环境用 10 线程 × 100 次复现 |

**当前优先级**：先解阻塞 #1（环境问题），其他阻塞依赖 #1 解决后启动。

---

## 下一刀（可立即执行）

**环境修复前不要启动新任务**。

环境修复后，按以下顺序恢复：
1. **T1 验证**：跑前测 7/7 → 跑 `run.py status` → 备份 → upgrade → downgrade → 重新 upgrade
2. **T5+T6+T7+T8 并行小任务**：register 只读 / confirm_schedule 不覆盖 / auto_publish 补 product_type / process_v2 修语法
3. **T2**：BaseStorage.supersede_old_tasks 实现 + 单测
4. **T3+T4**：publish_report / publish_material 集成 supersede
5. **T11+T12**：扫描+修复脚本（dry-run）
6. **T9+T10**：change_product_type API + sync_bridge 事件
7. **T13+T14**：监控告警 5 点埋点 + 苑岗彪企微
8. **T15+T16+T17+T18**：E2E + 路由基线 + 悲观审计 + 验收归档

---

## 已知风险（不扣分，仅记录）

详见 [SPEC.md §附录 C - 风险与开放问题](file:///d:/yuan/不锈钢网带跟单3.0/.workbuddy/docs/features/workorder-product-type-fix/SPEC.md)
8 项已识别风险（R1-R8），均有缓解策略。

**新增风险 R9**：本机执行环境与生产环境（Mac）不一致，可能导致本地不可复现的 bug。建议在生产环境 Mac 上做最终 E2E 验证。

---

## 验收签字（P8 时填写）

| 角色 | 签字 | 日期 |
|------|------|------|
| 产品负责人 | _ | _ |
| 技术负责人 | _ | _ |
| QA 负责人 | _ | _ |
| 运维负责人 | _ | _ |