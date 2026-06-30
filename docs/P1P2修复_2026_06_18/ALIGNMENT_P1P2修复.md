# Bug 狩猎 R1 - P1+P2 修复方案

> 创建时间: 2026-06-18
> 状态: Align 阶段 - 已对齐
> 涉及文件: 3 个
> 涉及 Bug: 8 个 (4 P1 + 4 P2)

---

## 根因精确定位

### Bug #6 production-orders 字段空 [legacy_routes.py:703-714](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/legacy_routes.py#L703-L714)
- 硬编码 `material: ''` / `spec: ''` / `planStart: ''`
- `flowType: o.get('flow_type', '')` 但 process_records.flow_type 100% 空
- `assignedTo` 来源 packages.target_operator（也是空）

### Bug #7 质检 id/orderName 100% 空 [_core.py:7268-7328](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center/_core.py#L7268-L7328)
- SQL `SELECT * FROM container_center.quality_records` → 直接 DictCursor 返回
- 字段 id/orderName 不存在（表里 id 是整数，orderName 应来自关联查询）

### Bug #8 inspectionItems 3 种格式
- container_center 端点 /api/quality 序列化时未归一化

### Bug #14 dashboard 字段三重重复 [legacy_routes.py:122-133](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/legacy_routes.py#L122-L133)
- 同一订单返回 `orderId` + `order_no` 重复
- `material` + `spec` + `name` 三重（material=name=product_name, spec=''）

### Bug #10 scan-info 405 [legacy_routes.py:209](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/legacy_routes.py#L209)
- `methods=['GET']` 只注册 GET

### Bug #11 老板 KPI 全 0 [legacy_routes.py:88-103](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/api/legacy_routes.py#L88-L103)
- pending/processing/completed 算 process_records（实际只有 7 条）
- 应该算 production_orders（5 条都有 status）

### Bug #12 字段名错 [app.py:298](file:///d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/app.py#L298)
- 报工需要 step_name + operator，但报工可能用 process_code + operator_name
- 需加兼容

### Bug #13 dashboard 字段重复 (id+orderNo)
- 同 #14 的 orderId+order_no 重复

---

## 修复方案（用户已确认）

| Bug | 方案 | 关键文件 | 改动行数 |
|-----|------|---------|----------|
| #6 | production-orders JOIN production_orders 表补字段 | legacy_routes.py:703-714 | ~30 |
| #7 | 质量记录补全 id（生成 UUID）/ orderName（JOIN orders） | _core.py:7268-7328 | ~15 |
| #8 | inspectionItems 归一化为统一 array 格式 | _core.py:7268-7328 | ~10 |
| #14+#13 | 输出层去重：order_no 删 / material+spec 用真实字段 | legacy_routes.py:122-133 | ~10 |
| #10 | scan-info 加 POST methods | legacy_routes.py:209 | 1 |
| #11 | 聚合 SQL 改查 production_orders | legacy_routes.py:88-103 | ~15 |
| #12 | 报工兼容 process_code + operator_name | app.py:298 | ~5 |
| #13 | dashboard 字段去重 | legacy_routes.py:122-133 | （含 #14） |

## 验收标准

| Bug | 验证命令 | 预期 |
|-----|---------|------|
| #6 | GET /api/production-orders | material/spec/planStart/flowType/assignedTo 字段有真实值（不再 100% 空） |
| #7 | GET /api/dispatch-center/quality | id 字段非空（生成 UUID），orderName 有值 |
| #8 | GET /api/dispatch-center/quality | inspectionItems 100% 为 array 格式 |
| #14+#13 | GET /api/dashboard | 返回字段去重，order_no 不再单独出现 |
| #10 | POST /api/scan-info | HTTP 200 |
| #11 | GET /api/dashboard | pendingOrders/processingOrders 反映真实订单数（不是 0） |
| #12 | POST /api/process_sub_step 用 process_code/operator_name | HTTP 200 |

## 不变更部分

- 报工主路径 /api/process_sub_step 字段不变
- 调度中心架构
- 移动端架构
- process_sub_steps / process_records 主表结构
