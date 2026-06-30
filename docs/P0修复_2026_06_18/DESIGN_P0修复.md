# DESIGN - P0 修复设计

> 创建时间: 2026-06-18

---

## 1. 整体改动图

```
┌─────────────────────────────────────────────────────────────┐
│                    修改前 / 修改后对比                       │
└─────────────────────────────────────────────────────────────┘

【Bug #1+#2】save_process_sub_step_with_pkg_update
────────────────────────────────────────────────────
修改前：
  ① 去重检查 → ② 命中合并 OR 未命中插入 → ③ 累加 data_packages.completed_qty
  （去重命中时仍累加 → 重复报工会导致 completed_qty 暴增）

修改后：
  ① 去重检查 → ② 命中合并 OR 未命中插入 → ③ 仅当未命中时累加 data_packages
  （去重命中时只合并 operator，不重复累加）

【Bug #4】cc.get_sub_steps
────────────────────────────
修改前：
  SELECT * FROM process_sub_steps WHERE order_no = %s
  （processName 字段不存在 → 前端显示空）

修改后：
  SELECT s.*, pr.process_name AS process_name
  FROM process_sub_steps s
  LEFT JOIN process_records pr ON pr.process_name = s.step_name
                              AND pr.order_no = s.order_no
                              AND pr.is_deleted = 0
  WHERE s.order_no = %s
  （多表 JOIN 补 process_name 字段）

【Bug #5】GET /api/dispatch-center/material/requirements
────────────────────────────────────────────────────────
修改前：查 data_packages 引用 title/content/data_type（不存在字段）→ 500
修改后：查 order_materials 表（有 spec/unit 字段，16 条数据）

【Bug #14】spec 字段降级
──────────────────────────────
修改前：spec: spec or product_name  （spec 空时降级 → 三个字段值相同）
修改后：spec: spec  （spec 空时留空字符串，与 name 区分开）
```

---

## 2. 接口契约（不变更）

| API | 路径 | 方法 | 不变更 |
|-----|------|------|--------|
| 报工 | /api/process_sub_step | POST | ✅ |
| Dashboard | /api/dashboard | GET | ✅ |
| 物料缺料 | /api/dispatch-center/material/requirements | GET | ✅ |

---

## 3. 数据流图

```
操作工扫码报工
  ↓
POST /api/process_sub_step {order_no, step_name, quantity, operator, [batch_no]}
  ↓
mysql_storage.save_process_sub_step_with_pkg_update()
  ├─ ① 3 键去重检查 (order_no, step_name, process_code)
  ├─ ② 命中 → UPDATE operator（【FIX】不再累加 completed_qty）
  ├─ ② 未命中 → INSERT new row
  └─ ③ 【FIX】仅未命中时 UPDATE data_packages.completed_qty
  ↓
1 次 commit（原子事务）
  ↓
sync 桌面端
```

---

## 4. 异常处理

| 异常 | 策略 |
|------|------|
| 数据库连接失败 | 返回 500，记录异常 |
| 去重检查 SQL 失败 | 回滚事务，返回 500 |
| JOIN 失败（Bug #4 修复）| 返 NULL process_name，前端 fallback 到 step_name |
| data_packages 不存在 (Bug #1+#2 修复) | UPDATE 0 行不影响 INSERT 成功 |

---

## 5. 不变更部分

- 5003 调度中心架构
- 5008 移动端架构
- 报工入口路径 /api/process_sub_step
- process_sub_steps 主表结构
- 现有所有路由
- 报工幂等的 batch_no 检查（app.py:298）
