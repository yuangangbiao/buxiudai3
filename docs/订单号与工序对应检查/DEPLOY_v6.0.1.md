# DEPLOY v6.0.1 - 部署指南

> **版本**: v6.0.1
> **部署日期**: 2026-06-16
> **审计基线**: 100/100
> **回滚方案**: 见 §5

---

## 1. 部署前检查清单

- [ ] MySQL 5.7+ / 8.0+ 可连接
- [ ] Python 3.10+ 可用（推荐 3.14.3）
- [ ] `.env` 文件已配置 `MYSQL_PASSWORD`
- [ ] 备份当前生产代码（v6 备份已存在 `.v6bak`）
- [ ] 桌面端已关闭（避免文件占用）

---

## 2. 部署步骤

### 2.1 拉取代码（跳过，本地为单分支开发）

无 git 操作，本地直接复制 v6.0.1 文件覆盖。

### 2.2 DB 迁移（必须）

```bash
# 1. status_change_logs_current 表加 remark 列
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" d:\yuan\不锈钢网带跟单3.0\scripts\migrations\add_status_log_remark.py
# 预期: 已添加 remark 列 (首次) / remark 列已存在，跳过 (二次)
```

```bash
# 2. 验证迁移成功
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" d:\yuan\不锈钢网带跟单3.0\scripts\verify_status_log_remark.py
# 预期: 6 参调用 OK + 写入结果非 None
```

### 2.3 替换代码（5 个核心文件 + 1 个测试文件）

| 文件 | 来源 |
|------|------|
| `constants.py` | v6.0.1 |
| `models/shipment.py` | v6.0.1 |
| `models/process.py` | v6.0.1 |
| `models/production.py` | v6.0.1 |
| `models/database/utils_db.py` | v6.0.1（log_status_change 6 参）|
| `models/database/_database_legacy.py` | v6.0.1（删除 log_status_change）|
| `models/database/__init__.py` | v6.0.1（re-export）|
| `data/工序规则模板*.json` | v6.0.1（公式带 `{}`）|
| `ORDER_NO_DECLARATION.py` | v6.0.1（文档修正）|
| `scripts/sync_process_rules.py` | v6.0.1（API 修正）|

### 2.4 跑全量回归

```bash
& "C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest "d:\yuan\不锈钢网带跟单3.0\tests\unit\models\test_warehouse_link.py" "d:\yuan\不锈钢网带跟单3.0\tests\unit\models\test_log_status_change.py" -v
# 预期: 34 passed
```

### 2.5 启动服务

| 服务 | 启动命令 |
|------|---------|
| 桌面端 | 双击 `启动报工系统.bat` 或 `python main.py` |
| 5003 调度中心 | `python standalone_dispatch_server.py` |
| 5008 同步桥 | `python sync_bridge_server.py` |
| 5006 云端 | （云端服务，不在本次部署范围）|

### 2.6 端到端验证（建议）

在桌面端执行：
1. 选择一个订单 → 工序追踪 → 重新计算 → 应正常完成
2. 包装入库报工 +5 → 检查 finished_goods 仓库数量 +5
3. 报工 +15（QC 合格 = 10）→ 应硬拒绝弹错误
4. 部分发货 3 → 仓库自动 -3

---

## 3. 监控点

| 监控 | 关注指标 |
|------|---------|
| 数据库 | `status_change_logs_current.remark` 不为空的行数（业务异常记录）|
| 日志 | `5008 同步失败` 关键字（包装入库报工后）|
| 业务流 | 订单状态 `包装入库` 出现频率（应同步 finished_goods）|
| 错误率 | `TypeError: log_status_change` 应为 0 |

---

## 4. 已知问题处理

| 问题 | 触发条件 | 处理 |
|------|---------|------|
| 报工回退不校验 | delta<0 包装入库 | 业务可接受，记录 status_change.remark |
| 工序"穿曲轴" 模板/预设不一致 | 排产"穿曲轴"工序 | 决策"暂不动"，后续统一 |

---

## 5. 回滚方案

### 5.1 快速回滚（保留 v6 备份）

```bash
# 还原 4 个核心 v6 文件
copy d:\yuan\不锈钢网带跟单3.0\constants.py.v6bak d:\yuan\不锈钢网带跟单3.0\constants.py
copy d:\yuan\不锈钢网带跟单3.0\models\shipment.py.v6bak d:\yuan\不锈钢网带跟单3.0\models\shipment.py
copy d:\yuan\不锈钢网带跟单3.0\models\process.py.v6bak d:\yuan\不锈钢网带跟单3.0\models\process.py
copy d:\yuan\不锈钢网带跟单3.0\models\production.py.v6bak d:\yuan\不锈钢网带跟单3.0\models\production.py
```

### 5.2 DB 回滚（移除 remark 列）

```sql
ALTER TABLE status_change_logs_current DROP COLUMN remark;
```

### 5.3 严重故障紧急降级

1. 停止桌面端 + 所有服务
2. 还原代码（5.1）
3. 回滚 DB（5.2）
4. 重启服务
5. 通知相关人员

---

## 6. 联系人

- **开发**: AI 助手
- **审计**: v6.0.1 100/100 通过
- **紧急**: 桌面端"系统设置 → 紧急回滚"（如有此功能）

---

**部署负责人**: _______________
**部署时间**: _______________
**回滚触发条件**: 监控点异常 OR 测试不通过
