# DESIGN - P1+P2 修复设计

> 创建时间: 2026-06-18

---

## 1. 修复架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    修改前 / 修改后对比                       │
└─────────────────────────────────────────────────────────────┘

【Bug #10】POST /api/scan-info
────────────────────────────────────────────────
修改前: @bp.route('/api/scan-info', methods=['GET'])
        POST 请求 → 405 Method Not Allowed
修改后: @bp.route('/api/scan-info', methods=['GET', 'POST'])
        兼容 GET (?code=X) 和 POST (form/code body)

【Bug #12】报工字段名兼容
────────────────────────────────────────────────
修改前:
  step_name = body.get('step_name', '').strip()
  operator = body.get('operator', '').strip()
  → process_code/operator_name 报工失败
修改后:
  step_name = (body.get('step_name') or body.get('process_name') or body.get('process_code') or '').strip()
  operator = (body.get('operator') or body.get('operator_name') or body.get('worker') or '').strip()
  → 字段名兼容, 优先级 step_name > process_code; operator > operator_name

【Bug #6】production-orders 字段补全
────────────────────────────────────────────────
修改前: material/spec/planStart 全部硬编码 ''
修改后: 批量 JOIN production_orders (po_map), 字段:
  - material = po.get('material') or po.get('material_name') or ''
  - spec = po.get('spec', '') or ''
  - planStart = po.get('plan_start', '') or ''
  - planEnd = po.get('plan_end', '') or o.get('delivery_date', '') or ''
  - assignedTo = operator_map.get(order_no, '') or po.get('assigned_to', '')
  - flowType = o.get('flow_type', '') or po.get('flow_type', '')

注: production_orders / steel_belt.orders 都没有 material/spec 字段
    → 字段会保持空, 由前端 fallback 到 product_name
    → 数据建模缺陷, 需后续 migration

【Bug #7+#8】质检 record 字段
────────────────────────────────────────────────
修改前: 字段 id/orderName 缺失, inspectionItems 3 种格式
修改后:
  - id = r['id']  (已有)
  - orderName = r.get('order_no', '')  (新加, = order_no)
  - inspectionItems = _normalize_inspection_items(r.get('inspection_items'))
    (归一化: None/空 → []; 'a,b,c' → ['a','b','c']; "['a','b']" → ['a','b'])

【Bug #11】老板 KPI
────────────────────────────────────────────────
修改前: pending/processing/completed 算 process_records (7 条) → 全接近 0
修改后: 算 production_orders (5 条 status='生产中')
  - 新加 storage.get_all_production_orders() 方法
  - pending = '待生产'; processing = '生产中'; completed = '已完成'

【Bug #14+#13】dashboard 字段去重
────────────────────────────────────────────────
修改前: orderId + order_no 重复; material = name = product_name
修改后: 
  - expectedOrders 只保留 orderId (删 order_no/orderNo)
  - material = po.get('material') or po.get('material_name') or product_name
  - spec = spec (已修 #14 不再降级)
  - name = product_name
```

---

## 2. 数据流图

```
报工 (app.py 5008)
  ↓ POST /api/process_sub_step
  ├─ 字段名兼容（#12）
  ├─ 调 storage.save_process_sub_step_with_pkg_update (P0 已修)
  └─ 返回 {"code":0,"message":"报工已提交 (P01 +1.0)"}

扫码 (app.py 5008)
  ↓ POST /api/scan-info
  ├─ 解析 code 字段（GET ?code= 或 POST body）
  └─ 返回扫码结果

Dashboard (5008)
  ↓ GET /api/dashboard
  ├─ 调 get_all_process_records() + get_sub_steps() (P0 已修 #4)
  ├─ 调 get_all_production_orders() (P2 #11 新加)
  ├─ 计算 KPI
  └─ 返回 expectedOrders（去重 + spec 字段修正）

质检 (5003)
  ↓ GET /api/dispatch-center/quality/records
  ├─ 查 container_center.quality_records
  ├─ 归一化 inspectionItems
  └─ 补 orderName = order_no

生产订单 (5008)
  ↓ GET /api/production-orders
  ├─ 调 get_all_process_records() → records
  ├─ 批量查 production_orders → po_map
  └─ 拼装 result（补 material/spec/planStart/...）
```

---

## 3. 接口契约（不变更）

| API | 路径 | 方法 | 不变更 |
|-----|------|------|--------|
| 报工 | /api/process_sub_step | POST | ✅ |
| Dashboard | /api/dashboard | GET | ✅ |
| 扫码 | /api/scan-info | GET, POST | ✅（加 POST）|
| 生产订单 | /api/production-orders | GET | ✅ |
| 质检 | /api/dispatch-center/quality/records | GET | ✅ |

---

## 4. 异常处理

| 异常 | 策略 |
|------|------|
| #6 字段空 | 数据源无字段, 接受空值, 前端 fallback |
| #11 查询失败 | try/except, 回退到 process_records |
| #12 字段名 | 兼容 3 种命名, 优先级 step_name > process_name > process_code |

---

## 5. 不变更部分

- 5003/5008 服务架构
- 报工原子事务边界
- 现有所有 P0 修复代码
- 数据源表结构（material/spec 列缺失是数据建模问题, 不在本次修复范围）
