# 修复日志爆炸 Bug - 对齐文档

> **任务名**: 修复日志爆炸 bug
> **对齐阶段**: 6A 阶段 1 - Align
> **生成时间**: 2026-06-24 00:42
> **执行人**: AI 助手

---

## 一、根因分析（100% 锁定）

### 1.1 现象描述

- 13 分钟内 `logs/cloud_relay/` 目录产生 453 个 .log 文件（每 5 秒 1 个）
- 历史上 `logs/wechat_server/` 17,139 个、`logs/inventory_api/` 1,629 个、`logs/cloud_relay/` 20,276 个 .log
- 文件名格式：`2026-06-24 00-11-15.log`（带秒级时间戳），不是预期 `2026-06-24.log`（按天）

### 1.2 根因定位

**根因**：[core/_config_ui.py:176](file:///d:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/core/_config_ui.py#L176) 默认值错误

```python
# 当前代码（有 bug）
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')  # ← 带秒级时间戳

# 应该是
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d')           # ← 按天
```

### 1.3 触发链路

```
1. 5003 调度中心启动 → core.config 加载 → LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
2. 5003 调度中心导入 logging_setup.py → setup_daily_logger('cloud_poller')
3. logging_setup.py:44  _get_today_str() = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
4. logging_setup.py:50-67 _ensure_today_file() 检查 _today_str 是否变化
5. 每次 emit() 调用时 _today_str 都不同（秒数变化）→ 触发 RolloverFileHandler 创建新文件
6. 产生 N 个 .log 文件（N = 写日志的次数）
```

### 1.4 影响范围

| 服务 | 实际 log 目录 | 触发函数 | 影响 |
|------|--------------|---------|------|
| 5003 调度中心 | `logs/cloud_relay/` | `cloud_poller.py:685` | 13 分钟 453 个 .log |
| 5008 移动端 | `logs/wechat_server/` | `wechat_server.py:168` | 历史 17,139 个 .log |
| 5001 desktop_web | `logs/wechat_cloud/` | `wechat_cloud.py:52` | 历史 105 个 .log |
| 5010 库存 | `logs/inventory_api/` | `inventory_api_server.py:35` | 历史 1,629 个 .log |
| 5002 容器 | `logs/container_api/` | `container_api_server.py:676` | 历史 13 个 .log |
| cloud_relay 服务 | `logs/cloud_relay/` | `cloud_relay.py:25` | 历史 20,276 个 .log（实际上 cloud_relay 服务无法启动） |

---

## 二、修复方案

### 方案 A：最小修复（推荐，1 个文件 1 行改动）

**只修改 `core/_config_ui.py:176` 默认值**：

```python
# 修改前
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')

# 修改后
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d')
```

- 优点：最小变更
- 缺点：如果未来有人设置错误的 `LOG_DATE_FORMAT` env，会再次爆炸

### 方案 B：根因修复（推荐，2 个文件 3 行改动）

**修改 1**：`core/_config_ui.py:176` 默认值改对
**修改 2**：`logging_setup.py:42-44` 强制按天（防御性）

```python
# logging_setup.py 修改
def _get_today_str(self):
    """获取今日日期字符串（强制按天）"""
    # 强制按天，防止 LOG_DATE_FORMAT 配置错误导致每条日志一个新文件
    # v3.6.4 治理发现的历史 bug（曾产生 75k+ 个 .log）
    return datetime.now().strftime('%Y-%m-%d')
```

- 优点：双保险，彻底防止此类问题再发
- 缺点：轻微扩大变更范围

### 方案 C：完整修复（推荐生产环境，3 个文件 5 行改动）

**修改 1**：`core/_config_ui.py:176` 默认值改对 + 注释
**修改 2**：`logging_setup.py:42-44` 强制按天
**修改 3**：`mobile_api_ai/.env` 显式设置 `LOG_DATE_FORMAT=%Y-%m-%d`（双保险）

```python
# core/_config_ui.py:175-178 修改
# ⚠️ v3.6.4 治理：LOG_DATE_FORMAT 必须是 '%Y-%m-%d'（按天）
# 错误配置 '%Y-%m-%d %H:%M:%S' 会导致每秒生成一个新 .log（历史曾产生 75k+ 个 .log）
LOG_DATE_FORMAT = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d')
```

```env
# mobile_api_ai/.env 末尾追加
LOG_DATE_FORMAT=%Y-%m-%d
```

---

## 三、推荐方案

**方案 C（完整修复）**：双保险 + 防御性代码 + 注释说明

### 3.1 实施步骤

1. **Step 1**: 修改 `core/_config_ui.py:176`（默认值 + 注释）
2. **Step 2**: 修改 `logging_setup.py:42-44`（强制按天）
3. **Step 3**: 在 `mobile_api_ai/.env` 末尾追加 `LOG_DATE_FORMAT=%Y-%m-%d`
4. **Step 4**: 重启 6 个服务（5003/5008/5001/5002/5010/8008）
5. **Step 5**: 清理现有的 453+ 个 cloud_relay/ 残留 .log
6. **Step 6**: 持续观察 1 小时，验证修复效果

### 3.2 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 服务重启导致业务中断 | 中 | 6 个服务按序重启（先 5003 → 5008 → 5001 → 5002 → 5010 → 8008），每步间隔 5 秒 |
| 业务人员依赖旧日志路径 | 低 | 日志路径不变（仍是 `logs/<service>/YYYY-MM-DD.log`） |
| 修复后日志丢失 | 低 | 只影响**新写入**的日志命名，历史日志已存在不受影响 |
| 跨服务配置不同步 | 低 | 所有 6 个服务共用同一份 `core/config.py`，改一次全部生效 |

### 3.3 验证标准

- [ ] **数量验证**：1 小时内 `logs/cloud_relay/` 只产生 1 个 .log（不是 720 个）
- [ ] **大小验证**：单个 .log 不超过 10MB（触发 `RotatingFileHandler` 轮转）
- [ ] **路径验证**：日志仍在 `D:/yuan/不锈钢网带跟单3.0/logs/<service>/` 路径下
- [ ] **格式验证**：文件名为 `YYYY-MM-DD.log`（按天），不是 `YYYY-MM-DD HH-MM-SS.log`（按秒）
- [ ] **业务验证**：6 个服务正常运行，5001/5003/5008 端口能正常响应

---

## 四、任务边界

### 4.1 在范围内
- ✅ 修改 `core/_config_ui.py:176`
- ✅ 修改 `logging_setup.py:42-44`
- ✅ 修改 `mobile_api_ai/.env`
- ✅ 重启 6 个服务
- ✅ 清理现有 cloud_relay/ 残留 .log
- ✅ 1 小时观察验证

### 4.2 不在范围内（明确划界）
- ❌ 重构整个 logging_setup.py（仅修改 _get_today_str 函数）
- ❌ 修改其他服务的日志逻辑
- ❌ 修改 `RotatingFileHandler` 的参数（maxBytes/backupCount）
- ❌ 引入第三方日志框架（如 loguru）
- ❌ 重写 cloud_poller 模块

---

## 五、修复时间线

| 阶段 | 时间 | 工作量 |
|------|------|--------|
| Align（本文档） | 2026-06-24 00:42 | 完成 |
| Architect（设计） | 5 分钟 | 1 个文件 |
| Atomize（任务拆分） | 3 分钟 | 5 个原子任务 |
| Approve（用户审批） | — | 等待用户 |
| Automate（执行） | 30 分钟 | 5 步实施 + 重启 |
| Assess（评估） | 60 分钟 | 1 小时观察 |

---

**等待用户确认方案 C 后进入 Architect 阶段。**
