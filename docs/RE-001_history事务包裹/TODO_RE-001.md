# TODO — RE-001 history 事务包裹（待办事项）

> 阶段 6: Assess · 任务后待办清单
> 日期: 2026-06-09
> 用途: 明确哪些待办、缺少的配置、需用户决策的事宜

---

## 一、RE-001 任务范围内（已全部完成）

✅ **无** — RE-001 范围（11 处事务包裹）已 100% 完成，无需待办。

---

## 二、项目级技术债（不属于 RE-001，建议处理）

### 🔴 P0-001: `utils.password_hasher` 模块缺失

| 项 | 详情 |
|:---|:-----|
| **影响** | test_cost_module.py 全部 18 个测试 ModuleNotFoundError |
| **触发** | `from utils.password_hasher import ...` 找不到 |
| **修复方式** | (1) 创建 `utils/password_hasher.py` 模块<br>(2) 或在测试中标记 skip |
| **优先级** | 🔴 P0（影响 122 个测试） |
| **负责人** | 待分配 |
| **预估** | 30 min |

**操作指引**：
```bash
# 1. 检查模块是否存在
ls d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\utils\password_hasher*

# 2. 如果不存在,搜索 git 历史
cd d:\yuan\不锈钢网带跟单3.0
git log --all --oneline -- mobile_api_ai/utils/password_hasher.py

# 3. 或在测试 conftest.py 中加 skip
@pytest.mark.skipif(not importlib.util.find_spec("utils.password_hasher"), reason="模块缺失")
```

### 🔴 P0-002: `api.health has no attribute 'core'`

| 项 | 详情 |
|:---|:-----|
| **影响** | test_health.py 3 个测试失败 |
| **触发** | `api.health` 模块缺少 `core` 导入 |
| **修复方式** | 检查 `api/health.py` 顶部 import，补 `from api import core` |
| **优先级** | 🔴 P0 |
| **预估** | 10 min |

### 🟡 P0-003: `utils.auto_schema has no attribute 'sqlite3'`

| 项 | 详情 |
|:---|:-----|
| **影响** | test_auto_schema.py 2 个测试失败 |
| **触发** | `utils.auto_schema` 暴露 `sqlite3` 属性失败（Python 3.14 兼容） |
| **修复方式** | 检查 `utils/auto_schema.py` 第 1 段 import |
| **优先级** | 🟡 P0 |
| **预估** | 15 min |

### 🟡 P0-004: pyproject.toml addopts 冲突

| 项 | 详情 |
|:---|:-----|
| **影响** | pytest `--no-cov` 与 addopts 冲突 |
| **触发** | `addopts = "--cov=... --no-cov"` 不允许 |
| **修复方式** | 拆分 addopts 为"默认"和"CI 严格"两组 |
| **优先级** | 🟡 P0 |
| **预估** | 10 min |

**示例修复**：
```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = ""  # 默认空,避免冲突
testpaths = ["tests"]

# CI 配置 (.github/workflows/test.yml)
# 单独覆盖 addopts:
# pytest tests/ -o "addopts=--cov=api --cov-fail-under=60"
```

### 🟡 P0-005: `pyjwt` 缺包

| 项 | 详情 |
|:---|:-----|
| **影响** | `from api.auth import ...` import 失败 |
| **触发** | 缺 `pyjwt` 包 |
| **修复方式** | 加到 `requirements.txt` |
| **优先级** | 🟡 P0 |
| **预估** | 5 min |

**操作指引**：
```bash
echo "pyjwt>=2.0" >> d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\requirements.txt
pip install pyjwt
```

---

## 三、RE-001 任务后续（建议）

### 3.1 立即（1 天内）

- [ ] **移动 7 份文档** 从 `d:\yuan\构想文件\RE-001_history事务包裹\` → `d:\yuan\现实文件\RE-001_history事务包裹\`
- [ ] **删除** 构想文件目录
- [ ] **更新 README** 标记 RE-001 已完成

### 3.2 短期（1-2 周内）

- [ ] **进入 RE-002** (乐观锁) 或 **RE-005** (WAL)
- [ ] **修复 P0-001 ~ P0-005** 5 个项目级技术债
- [ ] **建立监控**: 事务失败率告警

### 3.3 中期（1 个月内）

- [ ] **推广事务样板** 到代码审查 checklist
- [ ] **培训团队**: 解释事务边界 + 失败回滚重要性
- [ ] **写 Wiki 文档**: 事务使用规范

### 3.4 长期（3 个月内）

- [ ] **拆分大事务**: 找出 p99 > 100ms 的接口
- [ ] **建立 SLA**: 事务失败率 < 0.01%
- [ ] **接入 APM**: 监控事务耗时 + 锁竞争

---

## 四、需用户决策的事宜

### 4.1 下一 P0 任务选择

| 选项 | 范围 | 投入 | 推荐度 |
|:-----|:-----|:-----|:------:|
| **RE-002 乐观锁** | 8 处代码加 version 字段 | 2-3 天 | ⭐⭐⭐ |
| **RE-005 WAL 预写日志** | SQLite WAL + 应用层 crash recovery | 3-4 天 | ⭐⭐ |
| **跳过 P0,修复 P0-001~005** | 项目级技术债 | 1 小时 | ⭐⭐⭐⭐ |

**建议**: 先修复 P0-001~005（1 小时），再做 RE-002。

### 4.2 文档归档方式

| 选项 | 操作 | 风险 |
|:-----|:-----|:-----|
| A. 移动 + 清理 | 移动到 `现实文件/`,删除 `构想文件/` | 中（不可逆） |
| B. 仅复制 | 复制到 `现实文件/`,保留 `构想文件/` | 低（保留历史） |
| C. 暂不归档 | 保留现状 | 0（无操作） |

**建议**: A（按 jgs6 规范）。

### 4.3 RE-001 代码是否立即部署？

| 选项 | 操作 | 风险 |
|:-----|:-----|:-----|
| A. 立即部署到云端 | wechat_server.py 同步改动 | 中（云端需回归） |
| B. 仅本地验证 | 不部署,等下次例行 | 低 |
| C. 灰度部署 | 10% 流量先跑 1 周 | 低（推荐） |

**建议**: C（按 5% → 25% → 100% 灰度）。

---

## 五、缺失配置

| 配置 | 状态 | 备注 |
|:-----|:----:|:-----|
| MySQL 连接池监控 | ❌ 缺 | 建议接入 Prometheus |
| 事务失败告警 | ❌ 缺 | 建议接企业微信 |
| 死锁日志收集 | ❌ 缺 | MySQL `innodb_print_all_deadlocks=ON` |
| 慢查询日志 | ❌ 缺 | `slow_query_log=ON, long_query_time=0.05` |

**操作指引**：在 MySQL 配置文件中添加：
```ini
[mysqld]
innodb_print_all_deadlocks = ON
slow_query_log = ON
long_query_time = 0.05
log_slow_extra = ON
```

---

## 六、跟进表（已确认事项）

| 跟进项 | 负责人 | 截止日 | 状态 |
|:-------|:------|:------|:----:|
| 文档移动到 `现实文件/` | 待分配 | 2026-06-10 | ⏳ |
| P0-001 password_hasher 修复 | 待分配 | 2026-06-10 | ⏳ |
| P0-002 api.health 修复 | 待分配 | 2026-06-10 | ⏳ |
| P0-003 auto_schema 修复 | 待分配 | 2026-06-10 | ⏳ |
| P0-004 addopts 拆分 | 待分配 | 2026-06-10 | ⏳ |
| P0-005 pyjwt 加入 requirements | 待分配 | 2026-06-09 | ⏳ |
| 灰度部署上线 | 待分配 | 2026-06-15 | ⏳ |
| 下一 P0 任务立项 | 用户决策 | 待确认 | ⏳ |

---

**TODO 清单完毕。** ✅

**用户需要决策**：
1. 下一 P0 任务选择（4.1）
2. 文档归档方式（4.2）
3. 部署方式（4.3）

请直接回复决策，我会立即执行。
