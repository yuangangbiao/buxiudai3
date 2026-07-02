# 新员工培训手册 - v3.6 系统

> **适用人员**: 新员工 / 不熟悉系统的老员工
> **最后更新**: 2026-07-02
> **配套视频**: `docs/business/videos/`（待录）

---

## 一、系统全貌

### 1.1 11 业务表

| # | 表名 | 业务含义 | 谁会查 |
|---|------|---------|--------|
| 1 | process_sub_steps | 工序报工（SSOT）| 工人/跟单员 |
| 2 | material_records | 物料备料 | 仓管/跟单员 |
| 3 | quality_records | 质检结果 | 质检员 |
| 4 | outsource_records | 外协任务 | 物流 |
| 5 | repair_records | 设备报修 | 设备维修 |
| 6 | approval_records | 审批任务（**新建**）| 老板/经理 |
| 7 | production_orders | 排产订单 | 生产主管 |
| 8 | schedule_flow_logs | 排产步骤日志 | 生产主管 |
| 9 | process_records | 工序记录 | 生产主管 |
| 10 | tbl_configs | 系统配置 | 运维 |
| 11 | orders | 订单主表 | 跟单员/老板 |

### 1.2 data_type → 表名 路由

11 种 `data_type` 对应 11 张业务表：

| data_type | 业务表 |
|-----------|--------|
| process_report | process_sub_steps |
| material_request / pickup / buy | material_records |
| quality_task | quality_records |
| equipment_repair | repair_records |
| outsource_task | outsource_records |
| flow_production | production_orders |
| flow_step | schedule_flow_logs |
| production | process_records |
| config | tbl_configs |
| approval | approval_records |

---

## 二、字段对照表（最常用）

### 2.1 数量字段

| 业务 | 字段名 | 类型 | 允许 0 | 允许小数 | 示例 |
|------|--------|------|:------:|:--------:|------|
| 物料备料 | planned_qty | int | ❌ | ❌ | 100 |
| 工序报工 | quantity | decimal(10,2) | ❌ | ✅ | 10.5 |
| 工序完成 | completed_qty | decimal(10,2) | ❌ | ✅ | 10.5 |
| 工序合格 | qualified_qty | decimal(10,2) | ❌ | ✅ | 10.0 |
| 质检不良 | defect_qty | int | ✅ | ❌ | 0（合格）|
| 外协数量 | quantity | decimal(12,2) | ❌ | ✅ | 5.5 |
| 报修次数 | quantity | int | ✅ | ❌ | 0（待机）|

### 2.2 状态字段

通用字典（3 态）：
- `pending`（初始）
- `in_progress`（进行中）
- `completed`（完成）

特殊字典：
- 物料：`shortage`（缺料）
- 审批：`approved` / `rejected` / `cancelled`
- 流程日志：`failed`

### 2.3 审计字段

每张业务表都有：
- `created_by` — 创建人
- `created_at` — 创建时间
- `updated_by` — 最后修改人
- `updated_at` — 最后修改时间
- `is_deleted` — 软删除标记

---

## 三、5 类角色操作手册

### 3.1 生产主管 🔴

#### 场景：看排产看板
1. 打开浏览器 → http://5002/production
2. 选择日期范围
3. 一眼看清：已排 / 未排 / 紧迫
4. 点击订单 → 看详情

#### 场景：临时加单
1. 点击「加单」
2. 选择产品 + 数量
3. 系统自动算产能
4. 确认发布 → 工人收到推送

### 3.2 仓管 📦

#### 场景：扫码添加物料
1. 打开手机 → 扫码
2. 选择物料 + 数量
3. **数量必须整数**（如 100，不是 10.5）
4. 提交 → 看到绿色对勾

#### 场景：缺料处理
1. 系统提示「缺料」→ 状态=shortage
2. 联系供应商
3. 物料到货 → 状态改为 pending

### 3.3 质检员 🔍

#### 场景：提交质检结果
1. 打开手机 → 选择订单
2. 输入合格数 + 不良数
3. **不良数 = 0** 允许（合格品）
4. 提交 → 状态=in_progress → completed

#### 场景：不良品追溯
1. 打开「追溯」页面
2. 输入订单号
3. 看到：工序 / 工人 / 班次 / 时间
4. 联系工人返工

### 3.4 物流专员 🚚

#### 场景：录运单号
1. 打开 APP → 选择订单
2. 输入运单号（**自动 UUID，全球唯一**）
3. 提交 → 看到绿色对勾

#### 场景：批量录运单
1. 打开「批量发货」页面
2. 上传 Excel（订单号 + 运单号）
3. 系统自动校验
4. 确认提交

### 3.5 跟单员 📋

#### 场景：老板问进度
1. 打开浏览器 → 订单详情
2. 一眼看到：报工 / 物料 / 质检 / 物流
3. **不用电话**，1 秒答
4. 异常订单自动标红

#### 场景：异常订单提醒
1. 系统推送「XX 订单超期」
2. 打开 → 看原因（物料/工人/质检）
3. 联系相关人处理

---

## 四、3 层验收（每项新功能必走）

### 第 1 层：技术验证（开发自测）
- [ ] 调 API 后查 DB 应为预期值
- [ ] pytest 测试通过

### 第 2 层：业务验证（业务方验收）
- [ ] 老板在浏览器看状态变化
- [ ] 工人在手机看到绿色对勾

### 第 3 层：异常验证（开发自测）
- [ ] 错误提示全中文
- [ ] 不出现 SQL/英文/堆栈信息

---

## 五、常见问题 FAQ

### Q1: 为什么查不到老数据？
**A**: 老数据已迁移到新表。请用新表名查：
- process_sub_steps / material_records / quality_records 等

### Q2: 报工数量报「整数错误」？
**A**: 物料必须整数（如 100），工序可小数（如 10.5）。

### Q3: 运单号已存在？
**A**: 系统用 UUID 全球唯一，**不会重复**。如遇错误，请刷新页面重试。

### Q4: 状态字段显示「待开始」？
**A**: 旧数据已迁移到 `pending`。如仍看到中文，请清缓存。

### Q5: 看不到某订单的派工？
**A**: 派工走 process_sub_steps（不是 data_packages）。请用新接口查。

---

## 六、紧急情况处理

| 情况 | 操作 | 联系人 |
|------|------|--------|
| 系统 500 错误 | 截图 + 报错 → 微信技术主管 | tech_lead |
| 数据错误 | 提供订单号 + 时间 | 老板 |
| 报工冲突 | 重新提交（系统自动提示 409）| 班组长 |
| 物料申请失败 | 检查数量是否整数 | 仓管 |

---

**培训完成！** 如有问题请记录到 `docs/business/feedback.md`，我们会持续改进。
