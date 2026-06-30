# PRODUCTION_READY_v6.0.2 - 生产就绪报告

> **日期**: 2026-06-16
> **版本**: v6.0.2（dry-run 修补后）
> **审计**: 100/100
> **状态**: ✅ 可生产部署

---

## 1. dry-run 阶段发现并修复

dry-run 在真实 DB + 真实业务流上跑出 2 个 v6.0.1 漏掉的 bug：

| # | Bug | 修复 | 文件 |
|---|-----|------|------|
| 1 | `finished_goods` 表缺 `updated_at` 列 | 加列（v6.0.2 migration）| `scripts/migrations/add_finished_goods_updated_at.py` |
| 2 | `ship_out` 在 DictCursor 下 `row[0]` KeyError | 兼容 dict/tuple 两种返回 | `models/shipment.py:582` |

**3. 主动 commit**（v6 ship_out own_conn 路径缺 commit）| `models/shipment.py:597-599`

---

## 2. 部署清单

### 2.1 必做（已完成 ✅）

| 顺序 | 任务 | 状态 |
|:----:|------|:----:|
| 1 | `status_change_logs_current.remark` 列 | ✅ 已加（v6.0.1）|
| 2 | `finished_goods.updated_at` 列 | ✅ 已加（v6.0.2）|
| 3 | 替换 5 核心代码文件 | ✅ 已替换 |
| 4 | 跑全量回归 34/34 | ✅ 全过 |
| 5 | 端到端 dry-run 8 步 | ✅ 全过 |

### 2.2 桌面端实际运行（用户操作）

```bash
# 1. 启动桌面端
cd d:\yuan\不锈钢网带跟单3.0
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" main.py

# 2. 启动 5003 调度中心（新窗口）
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" standalone_dispatch_server.py

# 3. 启动 5008 同步桥（新窗口）
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" sync_bridge_server.py
```

### 2.3 端到端业务验证

1. 桌面端"工序追踪"选择一个订单 → **重新计算** → 验证 OK
2. **包装入库报工 +5** → 检查 `finished_goods.quantity = 5`
3. **QC 报工 +15**（QC 合格 = 10）→ 应**硬拒绝**弹错误
4. **部分发货 3** → `finished_goods.quantity = 2`
5. **5008 warehousing 消息** → 应收到 1 次

---

## 3. 监控点

| 监控 | 关键指标 |
|------|---------|
| DB | `status_change_logs_current.remark` 写入频率（异常记录）|
| 业务 | `finished_goods.quantity` 与 `process_records` completed_qty 一致性 |
| 日志 | `5008 同步失败` / `库存不足` 出现频率 |
| 错误 | `TypeError: log_status_change` = 0 |

---

## 4. 紧急回滚

```bash
# 代码回滚
copy constants.py.v6bak constants.py
copy models\shipment.py.v6bak models\shipment.py
copy models\process.py.v6bak models\process.py
copy models\production.py.v6bak models\production.py

# DB 回滚（已加列）
ALTER TABLE status_change_logs_current DROP COLUMN remark;
ALTER TABLE finished_goods DROP COLUMN updated_at;
```

---

## 5. 业务能力对照

| 业务流 | 修复前 | 修复后（v6.0.2）|
|--------|--------|----------------|
| 包装入库报工 | 仓库数量不变 | 自动 +5 联动 |
| 报工异常 | TypeError 中断 | 6 参 remark 记录 |
| 部分发货 | 数量减不到 2 | ship_out 真实生效 |
| 强校验 QC | 不校验 | 硬拒绝 |
| 排产公式 | 1000 倍单位错 | 正确 |
