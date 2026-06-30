# 技术债务看板

> 通过 GitHub Issues 标签体系跟踪技术债务。创建 Issue 时添加对应标签。

## 标签体系

### 严重度
| 标签 | 颜色 | 说明 |
|------|------|------|
| `debt-p0` | 🔴 #E24B4A | 阻断性问题：安全问题、数据丢失风险、系统不可用 |
| `debt-p1` | 🟡 #EF9F27 | 高优先级：性能退化、架构违规、核心功能受影响 |
| `debt-p2` | 🟢 #639922 | 中优先级：代码异味、冗余、可维护性问题 |
| `debt-p3` | ⚪ #888780 | 低优先级：优化建议、文档补充、风格统一 |

### 类别
| 标签 | 说明 |
|------|------|
| `area-test` | 缺少测试覆盖 |
| `area-arch` | 架构违规（绕过 service、直接调 models） |
| `area-perf` | 性能问题 |
| `area-security` | 安全问题 |
| `area-docs` | 文档缺失 |
| `area-code` | 代码质量（大函数、重复代码、魔法数字） |
| `area-ops` | 运维相关（部署、监控、日志） |

## 使用

```bash
# 创建债务 Issue
gh issue create --title "process_view.py: 10处 raw SQL 提取为 ProcessService" \
  --label "debt-p1,area-arch" \
  --body "位置: desktop/views/process_view.py
影响: 绕过 service 层直接操作数据库
修复: 迁移到 services/process_service.py"
```

## 当前已知债务

| # | 问题 | 标签 | 位置 |
|---|------|------|------|
| 1 | process_view.py 10 处 raw SQL | debt-p1, area-arch | desktop/views/process_view.py |
| 2 | InventoryNotifier 300s 阻塞轮询 | debt-p1, area-perf | services/inventory_notifier.py |
| 3 | 嵌入式库存 + 独立 WMS 双数据库 | debt-p2, area-arch | models/inventory.py + scripts/archive/ |
| 4 | RedisEventBus 已创建但未接入 | debt-p2, area-arch | core/redis_event_bus.py |
| 5 | 测试覆盖率仅 11% | debt-p1, area-test | tests/ |
| 6 | views 深层重构（god method 拆分） | debt-p2, area-code | desktop/views/process_view.py |
| 7 | config.py 713行 混合路径/DB/UI配置 | debt-p2, area-code | core/config.py |
