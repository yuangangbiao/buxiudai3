# EXECUTION_TRACKER - v3.6 量子版执行追踪

> **开始时间**: 2026-07-02
> **总工时**: 80h
> **总任务**: 78 个量子任务
> **阶段**: 4 个 + 1 个发布阶段
> **CI 触发**: 每个阶段结束跑一次

---

## 🎯 4 个阶段 + 1 个发布阶段

### 阶段 1：基础设施（CP-1）
- **任务**: T0.0 ~ T0.7 + T17 ~ T19（17 个量子任务）
- **工时**: 16h
- **CI 检查点**: CP-1

### 阶段 2：核心路由+鉴权（CP-2）
- **任务**: T1 ~ T6.5 + T20 ~ T23（25 个量子任务）
- **工时**: 22h
- **CI 检查点**: CP-2

### 阶段 3：清理+测试+合规（CP-3）
- **任务**: T7 ~ T13 + T24 ~ T27（23 个量子任务）
- **工时**: 20h
- **CI 检查点**: CP-3

### 阶段 4：业务验收+文档（CP-4）
- **任务**: T8.5 ~ T8.9 + T14 ~ T16（13 个量子任务）
- **工时**: 22h
- **CI 检查点**: CP-4

### 阶段 5：分批发布（W1-W3）
- **任务**: 灰度发布（自动化工序）
- **工时**: 0h（按计划）
- **CI 检查点**: W1-CP / W2-CP / W3-CP

---

## 📋 阶段 1 任务清单（17 个量子任务）

| 编号 | 任务 | 工时 | 状态 | CI 验证 |
|------|------|:----:|:----:|---------|
| T0.0 | mysql_storage.py 12 处 DDL 梳理 | 1h | 🔴 pending | grep |
| T0.0b | 在线 DDL 方案（pt-osc/gh-ost）| 2h | 🔴 pending | 文档 |
| T0.0c | enterprise_structure 不再 CREATE | 0.5h | 🔴 pending | 启动测试 |
| T0.5 | approval_records 新建 | 1h | 🔴 pending | 启动测试 |
| T0.5b.1 | process_sub_steps 升级（pt-osc）| 0.3h | 🔴 pending | DESCRIBE |
| T0.5b.2 | material_records 升级 | 0.3h | 🔴 pending | DESCRIBE |
| T0.5b.3 | quality_records 升级 | 0.3h | 🔴 pending | DESCRIBE |
| T0.5b.4 | outsource_records 升级 | 0.2h | 🔴 pending | DESCRIBE |
| T0.5b.5 | repair_records 升级 | 0.2h | 🔴 pending | DESCRIBE |
| T0.5b.6 | approval_records 升级 | 0.2h | 🔴 pending | DESCRIBE |
| T0.5b.7 | production_orders 升级 | 0.2h | 🔴 pending | DESCRIBE |
| T0.5b.8 | schedule_flow_logs 升级 | 0.2h | 🔴 pending | DESCRIBE |
| T0.5b.9 | process_records 升级 | 0.2h | 🔴 pending | DESCRIBE |
| T0.6c | 15 张配套表处理 | 0.5h | 🔴 pending | SHOW TABLES |
| T0.7 | 数据迁移脚本 | 1h | 🔴 pending | 142 行迁移 |
| T17.1 | Grep 列出 global 变量 | 0.5h | 🔴 pending | grep |
| T18.1 | 异常处理器（utils/exception_handler.py）| 0.5h | 🔴 pending | 单元测试 |
| T19.1 | 硬编码密码清除（3 文件）| 0.5h | 🔴 pending | grep |
| **小计** | **17 任务** | **9.6h** | | |

**阶段 1 实际工时**: 约 10h（比原计划 16h 短，因为 T0.5b 9 个量子任务共用 pt-osc 工具准备）

---

## 🔍 CP-1 检查点（阶段 1 完成后）

### 检查项
- [ ] 9 业务表全部加 is_deleted/created_by/updated_by/updated_at 字段
- [ ] 9 业务表 status 字段有 CHECK 约束
- [ ] approval_records 表已创建（含 18 字段）
- [ ] 15 张配套表已标记保留/已 DROP 备份表
- [ ] 数据迁移脚本已执行（142 行已更新）
- [ ] 异常处理器已就位
- [ ] 3 处硬编码密码已清除
- [ ] global 变量已摸底

### CI 命令
```bash
python ci/check_stage_1.py
pytest tests/test_stage_1_ddl.py -v
```

### 失败处理
- 任意 1 项未通过 → 阶段 1 不通过 → 修复后重新跑 CI
