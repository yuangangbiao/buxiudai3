# Bug 狩猎 R1 - P0 修复方案（更新版）

> 创建时间: 2026-06-18
> 状态: Align 阶段 - 已对齐
> 涉及文件: 4 个
> 涉及 Bug: 5 个 P0

---

## 根因精确定位（基于 28053 条 process_sub_steps 实际数据）

### Bug #1+#2 真实根因（关键发现）

- **`process_sub_steps.process_code` 100% 为空**（28053/28053）
- 根因链：
  1. `app.py:323` 调 `get_process_code(step_name)` 内存函数查 process_code
  2. step_name 是中文（"原材料准备"/"质量检验"）→ get_process_code 查不到 → 返空字符串
  3. `mysql_storage.py:1175-1185` 去重逻辑走分支 2（`process_code IS NULL OR process_code=''`）
  4. 第二次报工 → 命中已有行 → **不插入** + 但仍 `+qty_delta` 到 data_packages（**这是真正 bug**）
  5. 第三次报工 → 仍命中 → 仍累加

### Bug #4 真实根因

- `cc.get_sub_steps(order_no)` 查 process_sub_steps 时没 JOIN process_records
- 正确 JOIN 键：`pr.process_name = s.step_name`（不是 process_code，因为 process_code 100% 空）

### Bug #5 真实根因（反虚高发现）

- `_core.py:2511` SQL 引用了**不存在**的字段：`title`/`content`/`data_type`
- 实际 data_packages 字段：id, order_no, related_order, related_process, pkg_type, qty, completed_qty, status
- 该端点**直接 500 报错**——不是 spec/unit 字段空的问题
- 真实数据源是 `order_materials`（16 条，带 spec/unit）

### Bug #14 根因

- `legacy_routes.py:126` spec 降级为 product_name
- 1 行修复

---

## 修复方案（用户已确认）

| Bug | 方案 | 关键文件 | 改动行数 |
|-----|------|---------|----------|
| #1+#2 | 去重命中不累加 completed_qty | [mysql_storage.py:1216](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/storage/mysql_storage.py#L1216) | ~3 |
| #4 | LEFT JOIN process_records（ON pr.process_name=s.step_name） | legacy_routes.py:get_sub_steps | ~5 |
| #5 | 改查 order_materials 表（去掉 title/content/data_type 引用） | [_core.py:2511-2567](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py#L2511-L2567) | ~30 |
| #14 | spec 字段不再降级为 product_name | [legacy_routes.py:126](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/legacy_routes.py#L126) | 1 |

## 验收标准

| Bug | 验证命令 | 预期 |
|-----|---------|------|
| #1+#2 | 同一 order+step 重复报工 3 次（无 batch_no）| data_packages.completed_qty = 第一次的 quantity（不累加）|
| #4 | 调 /api/dashboard 看 sub_steps | processName 字段不再为空 |
| #5 | GET /api/dispatch-center/material/requirements | HTTP 200，spec/unit 字段有值或显式空 |
| #14 | GET /api/dashboard 看 expectedOrders[].spec | spec 与 product_name 不全等 |

## 不变更部分

- 5003 调度中心架构
- 5008 移动端架构
- 报工入口路径 /api/process_sub_step
- process_sub_steps 主表结构
- 现有所有路由

## 风险

- Bug #1+#2 修复后，旧脏数据不会自动清理（2000万+ 的 completed_qty 仍在）
- 需要写清理脚本作为后续任务
