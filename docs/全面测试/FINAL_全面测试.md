# FINAL 报告：不锈钢网带跟单系统3.0 全面测试

> 完成时间：2026-06-08
> 状态：**部分完成**（60%）
> 下一步：P0 阻塞项修复后回归

## 一、测试结论

| 维度 | 结果 | 关键证据 |
|------|------|----------|
| 服务可用性 | ✅ 通过 | 5003/15003 端口均可响应 |
| API 端点覆盖 | ✅ 通过 | 32 端点全量 GET/POST 可达 |
| 业务流程冒烟 | ⚠️ 50% | 12 步中 6 步通过，6 步失败 |
| 静态检查 | ✅ 通过 | flake8 0 致命；bandit 0 致命业务漏洞 |
| 安全扫描 | ⚠️ 需关注 | 15 HIGH（仅 scripts/ 部署脚本 + 非密码 hash） |

## 二、关键阻塞（P0 优先级，需云端修复）

### 1. 数据库缺 `direction` 列
- 表：`process_sub_steps`（推测）
- 触发：`/api/sync/task/<order>/status`、`/api/sync/report`
- 错误：`(1072, "Key column 'direction' doesn't exist in table")`
- 建议：在云端 `wechat_server.py` 中定位 `ORDER BY direction` / `WHERE direction=` 用法，新增列或修正 SQL

### 2. 订单号验证正则不匹配
- 端点：`/api/sync/validate/input`
- 当前：`ORD-202605020001` 被判为 `无效的订单号格式`
- 实际：生产订单号格式就是 `ORD-YYYYMMDDXXXX`
- 建议：云端更新 `validate_order_no` 正则为 `^ORD-\d{8,}$`

## 三、非阻塞观察（P1 建议优化）

- 外协发布接口（`/api/sync/outsource/publish`）参数传递异常，疑似 JSON/Form 协议不一致
- `scripts/*.py` 中 10 处 `subprocess shell=True`，可改为列表形式消除风险
- `migrations/run.py` 中 2 处 `exec()` 调用，建议改为 `importlib` 或函数调用

## 四、可立即执行的下一步

1. **云端修复 P0-1、P0-2**（开发者操作）
2. **重跑回归**：`D:\yuan\test_venv\Scripts\python.exe D:\yuan\smoke_business.py` 验证 12 步通过率 ≥ 90%
3. **P1 协议验证**：手工 curl 外协发布确认问题侧
4. **可选清理**：547 个 F401 未使用 import 批量清理（不阻塞）

## 五、产物归档

- 主报告：[ACCEPTANCE_全面测试.md](ACCEPTANCE_全面测试.md)
- 测试脚本：`D:\yuan\smoke_*.py`
- 扫描产物：`D:\yuan\flake8*.txt`、`D:\yuan\bandit.json`
- 日志：`D:\yuan\wechat_15003.log`

---

> 测试负责人：AI 辅助 + 用户确认
> 验收标准：阻塞项修复后业务流程冒烟通过率 ≥ 90%
