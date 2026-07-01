# TODO — 全面优化方案待办清单

## 🟡 中优先级（建议近期处理）

### R1: 慢查询索引优化（数据库层）
- **位置**: MySQL 数据库
- **描述**: 慢查询分析报告识别了 Top 5 候选慢查询，需要在数据库层执行以下操作：
  - Q1: 生产工单主列表 JOIN 查询 → 加 `(status, created_at)` 复合索引
  - Q2: 流程记录列表分页查询 → 游标分页替代 OFFSET
  - Q3: 物料需求表全表扫描 → 加 `(order_no, material_code)` 索引
  - Q4: 数据流日志聚合查询 → 日志归档策略+分区表
  - Q5: 工序子步骤汇总查询 → 加 `(process_id, batch_no)` 索引
- **依赖**: 需要数据库管理员权限
- **参考**: `docs/全面优化方案/慢查询分析报告.md`

### R4: pytest 需要 MySQL 服务
- **描述**: pytest 套件需要 MySQL 服务才能运行（部分测试依赖真实数据库连接）
- **解决方式**: 执行前需要：
  1. 配置 `.env` 中的 `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DB`
  2. 确保 MySQL 服务正常运行
  3. 运行：`cd mobile_api_ai && pytest`
- **当前状态**: 环境不支持 MySQL 服务，暂无法运行测试套件

---

## 🟢 低优先级（上线前或上线后安排）

### R2: 熔断器监控面板
- **描述**: 当前熔断器的开关状态通过日志输出，缺少可视化面板
- **建议**: 在健康检查端点 `/api/health` 增加熔断器状态字段，或集成到现有监控系统
- **参考**: `circuit_breaker_integration.py` 的 `CircuitBreakerRegistry.get_all_states()`

### R3: 限流阈值调优
- **描述**: 当前限流策略使用保守的默认值（60 per minute 等）
- **建议**: 根据生产环境流量进行调整
- **修改位置**: `api/auth.py` / `api/scan.py` / `api/process.py` 中的 `@limiter.limit()` 参数
- **当前值**:
  - 登录接口: 10 per minute
  - 验证/信息接口: 30 per minute
  - 扫码/工单/任务接口: 60 per minute
  - 流程接口: 60 per minute

---

## 🔵 无需处理（信息性记录）

### v4 标签状态
- `git tag v4` 已创建，标记阶段四完成
- 注意：当前工作区仍有未提交的修改（Phase 4 代码变更），建议在下次提交前确认是否需要重新打 tag

### 构想文件位置
- 全部文档已从 `d:\yuan\构想文件\全面优化方案\` 移动到 `d:\yuan\现实文件\全面优化方案\`
- 确认移动后已清理原构想文件目录

---

## 常用命令参考

```bash
# 运行测试（需要 MySQL 服务）
cd d:\yuan\不锈钢网带跟单3.0\mobile_api_ai
pytest

# 带覆盖率运行
pytest --cov=. --cov-report=term-missing

# 代码风格检查
flake8 .
isort --check-only .
black --check .

# 类型注解覆盖率检查
python utils/check_annotation_coverage.py

# 启动服务
python app.py --port 5002
python dispatch_center.py --port 5003
```
