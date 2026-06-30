# 静默蓝图影响矩阵 - v3.7.0

> **创建日期**: 2026-06-28
> **关联版本**: v3.7.0 架构重构 Week 0 紧急任务
> **性质**: P0 文档，Week 0 第1-2天必须完成
> **审计来源**: 4专家审计（小曦PM）→ C-2

---

## 一、现状诊断

### 1.1 代码位置

[app.py:132-137](file:///d:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/app.py#L132-L137)

```python
for mod_name, bp_attr in [
    ('mobile_api_ai.api.ai',     'bp'),
    ('mobile_api_ai.api.cost',  'bp'),
    ('mobile_api_ai.api.reports','bp'),
]:
    try:
        mod = __import__(mod_name, fromlist=[bp_attr])
        app.register_blueprint(getattr(mod, bp_attr))
    except (ImportError, AttributeError) as e:
        logger.warning(f"[App] 蓝图 {mod_name}.{bp_attr} 注册跳过（未实现）: {e}")
```

### 1.2 静默机制

| 失败类型 | 行为 | 日志输出 |
|---------|------|---------|
| `ImportError`（依赖不存在） | 蓝图跳过，日志warning | `[App] 蓝图 xxx 注册跳过（未实现）: ImportError` |
| `AttributeError`（属性不存在） | 蓝图跳过，日志warning | `[App] 蓝图 xxx 注册跳过（未实现）: AttributeError` |
| 任何其他异常 | 全量上报 | 启动失败（不在try范围内） |

### 1.3 Week 0 诊断动作

**启动 app.py，观察日志中是否有以下3行 warning**：

```
grep "[App] 蓝图 mobile_api_ai.api.ai.bp 注册跳过" app.log
grep "[App] 蓝图 mobile_api_ai.api.cost.bp 注册跳过" app.log
grep "[App] 蓝图 mobile_api_ai.api.reports.bp 注册跳过" app.log
```

- **全部无warning** → 3个蓝图全部正常加载 → 跳到"二、2 蓝图表态确认"
- **有warning** → 对应蓝图静默 → 进入"三、影响评估"

---

## 二、三个蓝图的功能清单

### 2.1 ai.bp（AI模块）

**文件**: `mobile_api_ai/api/ai.py`
**功能数**: 6个
**依赖**: 无外部依赖（纯mock数据）
**注册条件**: 任意时刻可加载，无ImportError

| # | 路由 | 函数 | 功能描述 | 工厂角色影响 |
|---|------|------|---------|------------|
| 1 | POST /api/ai/voice-report | `parse_voice_report` | 解析语音报工文本 | 🔴 工人（语音报工功能） |
| 2 | POST /api/ai/image-analysis | `analyze_image_mock` | 图像分析（mock） | 🟡 质检（图片质检） |
| 3 | POST /api/ai/speech-to-report | `speech_to_report` | 语音转报工记录 | 🔴 工人（语音→数据） |
| 4 | POST /api/ai/image-analysis/chat | `image_analysis` | 图像分析对话 | 🟡 质检 |
| 5 | POST /api/ai/chat | `ai_chat` | AI智能对话 | 🟢 辅助 |
| 6 | GET /api/ai/chat/history | `chat_history` | 对话历史 | 🟢 辅助 |

**注**: ai.py 内置了 mock 数据（ORDERS、PROCESS_RECORDS），说明这个模块本身是半成品，语音功能可能是摆设。

---

### 2.2 cost.bp（成本模块）

**文件**: `mobile_api_ai/api/cost.py`
**功能数**: 13个
**依赖**: `services.factory.get_cost_service()` ← **如果此服务不存在，ImportError**
**注册条件**: 依赖 `services.factory` 模块存在

| # | 路由 | 函数 | 功能描述 | 工厂角色影响 |
|---|------|------|---------|------------|
| 1 | GET /api/cost/orders | `list_orders` | 订单成本列表 | 🟡 财务/老板 |
| 2 | GET /api/cost/orders/{order_no} | `get_order_cost` | 订单成本详情 | 🟡 财务 |
| 3 | POST /api/cost/calculate | `calculate` | 计算订单成本 | 🔴 财务（核心功能） |
| 4 | POST /api/cost/orders/{order_no}/revenue | `set_revenue` | 设置订单营收 | 🟠 财务 |
| 5 | GET /api/cost/orders/{order_no}/details | `get_details` | 成本明细 | 🟡 财务 |
| 6 | POST /api/cost/details | `add_detail` | 添加成本明细 | 🔴 财务（核心功能） |
| 7 | DELETE /api/cost/details/{id} | `delete_detail` | 删除成本明细 | 🟡 财务 |
| 8 | GET /api/cost/summary | `summary` | 成本汇总报表 | 🔴 老板（核心功能） |
| 9 | GET /api/cost/material-prices | `list_material_prices` | 物料价格表 | 🔴 财务 |
| 10 | POST /api/cost/material-prices | `save_material_price` | 保存物料价格 | 🔴 财务 |
| 11 | GET /api/cost/labor-prices | `list_labor_prices` | 人工单价表 | 🔴 财务 |
| 12 | POST /api/cost/labor-prices | `save_labor_price` | 保存人工单价 | 🔴 财务 |

**注**: 核心成本计算功能，如果静默 → 财务无法计算订单成本 → 影响老板决策

---

### 2.3 reports.bp（报表模块）

**文件**: `mobile_api_ai/api/reports.py`
**功能数**: 22个
**依赖**: `services.factory.get_stats_service()` + `get_scheduler_service()`
**注册条件**: 依赖 `services.factory` 模块存在

| # | 路由 | 函数 | 功能描述 | 工厂角色影响 |
|---|------|------|---------|------------|
| 1 | GET /api/reports/page | `page` | 报表中心页面 | 🔴 老板/生产主管（核心） |
| 2 | GET /api/reports/definitions | `list_definitions` | 报表定义列表 | 🔴 老板 |
| 3 | GET /api/reports/definitions/{id} | `get_definition` | 报表详情 | 🟡 老板 |
| 4 | POST /api/reports/definitions | `create_definition` | 新建报表定义 | 🟠 老板 |
| 5 | PUT /api/reports/definitions/{id} | `update_definition` | 更新报表定义 | 🟠 老板 |
| 6 | DELETE /api/reports/definitions/{id} | `delete_definition` | 删除报表定义 | 🟠 老板 |
| 7 | POST /api/reports/definitions/{id}/execute | `execute_definition` | 执行报表 | 🔴 老板（核心） |
| 8 | GET /api/reports/profiles | `list_profiles` | 报表配置列表 | 🟡 老板 |
| 9 | GET /api/reports/profiles/{id} | `get_profile` | 报表配置详情 | 🟡 老板 |
| 10 | POST /api/reports/profiles | `create_profile` | 新建报表配置 | 🟠 老板 |
| 11 | PUT /api/reports/profiles/{id} | `update_profile` | 更新报表配置 | 🟠 老板 |
| 12 | DELETE /api/reports/profiles/{id} | `delete_profile` | 删除报表配置 | 🟠 老板 |
| 13 | GET /api/reports/schedules | `list_schedules` | 定时任务列表 | 🔴 老板/生产主管 |
| 14 | GET /api/reports/schedules/{id} | `get_schedule` | 定时任务详情 | 🟡 老板 |
| 15 | POST /api/reports/schedules | `create_schedule` | 创建定时任务 | 🔴 老板（核心） |
| 16 | PUT /api/reports/schedules/{id} | `update_schedule` | 更新定时任务 | 🟠 老板 |
| 17 | DELETE /api/reports/schedules/{id} | `delete_schedule` | 删除定时任务 | 🟠 老板 |
| 18 | GET /api/reports/outputs | `list_outputs` | 报表输出列表 | 🔴 老板 |
| 19 | GET /api/reports/scheduler/status | `scheduler_status` | 调度器状态 | 🔴 运维 |
| 20 | POST /api/reports/scheduler/start | `start_scheduler_api` | 启动调度器 | 🔴 运维（核心） |
| 21 | POST /api/reports/scheduler/stop | `stop_scheduler_api` | 停止调度器 | 🔴 运维（核心） |

**注**: reports.bp 依赖 `services.factory`，如果服务不存在 → 整个报表系统静默下线

---

## 三、影响矩阵

### 3.1 按工厂角色影响

| 角色 | 影响的蓝图 | 影响功能 | 影响程度 | 降级方案 |
|------|---------|---------|:-------:|---------|
| **工人** | ai.bp | 语音报工/语音转文字 | 🔴高 | 降级为手动输入文字报工 |
| **质检员** | ai.bp | 图片质检分析 | 🟡中 | 降级为人工肉眼质检 |
| **财务** | cost.bp | 成本计算/物料人工单价管理 | 🔴高 | 降级为Excel手工计算（短期可接受） |
| **老板** | cost.bp + reports.bp | 成本汇总报表/报表中心/定时报表 | 🔴极高 | 降级为微信/电话汇报 |
| **生产主管** | reports.bp | 定时任务触发报表 | 🔴高 | 降级为手动触发 |
| **运维** | reports.bp | 调度器启动/停止 | 🟠中 | 临时：手动命令行启动 |

### 3.2 按依赖链影响

```
cost.bp 静默
  └─ services.factory.get_cost_service() 不存在
       └─ services/factory.py 不存在 或 get_cost_service 未定义
           └─ 依赖链断裂，13个路由全部下线

reports.bp 静默
  └─ services.factory.get_stats_service() 不存在
  └─ services.factory.get_scheduler_service() 不存在
       └─ 22个路由全部下线（含老板核心报表）

ai.bp 静默
  └─ 无外部依赖，纯mock数据
       └─ 6个路由全部下线（语音功能可能本来就是mock）
```

### 3.3 风险评级

| 蓝图 | 静默概率 | 功能完整性 | 工厂影响 | 综合风险 |
|------|:-------:|:---------:|:-------:|:-------:|
| **cost.bp** | 高（依赖外部服务） | 完整（13个路由） | 🔴极高 | 🔴 P0 |
| **reports.bp** | 高（依赖外部服务） | 完整（22个路由） | 🔴极高 | 🔴 P0 |
| **ai.bp** | 低（无外部依赖） | 存疑（mock数据） | 🟡中 | 🟠 P1 |

---

## 四、Week 0 诊断与决策树

```
启动 app.py，检查日志
    ↓
├─ 无 warning → 3个蓝图全部加载 → 人工验证功能是否真实可用
│       ↓
│   ├─ ai.bp 验证：POST /api/ai/voice-report（是否真实调用外部AI？）
│   ├─ cost.bp 验证：GET /api/cost/summary（是否返回真实数据？）
│   └─ reports.bp 验证：GET /api/reports/definitions（是否返回真实报表？）
│       ↓
│   ├─ 真实数据 → 标记为"已上线功能"，纳入回归测试范围
│   └─ mock/空数据 → 标记为"待上线功能"，纳入 v3.7.1 开发计划
│
└─ 有 warning → 蓝图静默 → 进入"静默处理决策"
        ↓
    ├─ cost.bp 静默 → 🔴 P0 → PM决策：
    │       ├─ "紧急上线" → 补 services.factory 模块
    │       └─ "暂缓" → 加警告banner通知用户
    ├─ reports.bp 静默 → 🔴 P0 → PM决策：
    │       ├─ "紧急上线" → 补 services.factory 模块
    │       └─ "暂缓" → 加警告banner通知用户
    └─ ai.bp 静默 → 🟠 P1 → PM决策：
            ├─ "紧急上线" → 修复导入问题
            └─ "暂缓" → 标记为待开发功能
```

---

## 五、处理决策（Week 0 必须签字）

| 蓝图 | 决策选项 | 签字人 | 时间限制 |
|------|---------|--------|---------|
| **cost.bp** | [ ] 补依赖，Week 4前上线 | PM+财务 | Week 0 第2天 |
| **reports.bp** | [ ] 补依赖，Week 4前上线 | PM+老板 | Week 0 第2天 |
| **ai.bp** | [ ] 确认是否真实使用，Week 8前决定 | PM | Week 0 第2天 |

---

## 六、降级方案模板

### 6.1 静默时强制启动失败（推荐修改）

将静默跳过改为启动失败，避免用户不知情：

```python
# 修改 app.py:132-137
for mod_name, bp_attr in [...]:
    try:
        mod = __import__(mod_name, fromlist=[bp_attr])
        app.register_blueprint(getattr(mod, bp_attr))
    except (ImportError, AttributeError) as e:
        logger.critical(f"[App] 蓝图 {mod_name}.{bp_attr} 注册失败: {e}")
        raise RuntimeError(f"核心蓝图 {mod_name} 加载失败，请检查 services.factory 是否就绪") from e
```

### 6.2 降级Banner提示

在移动端H5页面顶部添加提示：

```html
<!-- 静默蓝图降级Banner -->
<div class="warning-banner" id="costUnavail" style="display:none">
  成本计算功能暂时不可用，请联系管理员 | 临时方案：联系财务微信
</div>
<div class="warning-banner" id="reportsUnavail" style="display:none">
  报表中心暂时不可用，请联系管理员 | 临时方案：老板查看微信日报
</div>
```

---

**维护人**: PM小曦
**签字**: PM ☐ / 老板 ☐ / 财务 ☐
**决策截止**: Week 0 第2天
**最后更新**: 2026-06-28
