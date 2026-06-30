# TASK 2.2：告警规则配置 API

## 基本信息

| 字段 | 内容 |
|------|------|
| 任务ID | T2.2 |
| 任务名称 | 告警规则配置 API + 告警记录查询 API |
| 所属阶段 | 第二阶段（P1） |
| 预估工时 | 0.5天 |
| 优先级 | P1 |

---

## 输入契约（Input Contract）

### 前置依赖
- [ ] T1.2 容器中心 HTTP API 已实现（在相同蓝图中新增路由）
- [ ] T1.1 ConfigStore / AlertStore 已完成
- [ ] 现有告警规则的字段结构已确定

### 输入数据
- `dispatch_center.py` 中现有告警规则的字段定义和数据结构
- DESIGN 文档 2.2 节子任务中定义的 API 端点
- T1.1 ConfigStore（用于读写告警规则）和 AlertStore（用于查询告警记录）
- T1.2 中 `api/` 模块的蓝图注册方式

### 环境依赖
- Python 3.8+
- Flask（复用 T1.2 的蓝图机制）
- T1.1 ConfigStore / AlertStore

---

## 输出契约（Output Contract）

### 交付物
- `container_center/api/alert_api.py`（可能是改造现有文件，或新增告警路由）
- `container_center/api/config_api.py`（配置读写路由）

### API 端点清单

```
# ──────── 告警规则配置 ────────
GET    /api/container/config/alert_rules              # 获取超时告警规则
PUT    /api/container/config/alert_rules              # 配置超时告警规则
GET    /api/container/config/outsource_rules          # 获取外协催单规则
PUT    /api/container/config/outsource_rules          # 配置外协催单规则

# ──────── 告警记录查询 ────────
GET    /api/container/alert/list?level=&alert_type=   # 获取告警记录列表
POST   /api/container/alert/<id>/dismiss              # 忽略告警

# ──────── 操作员配置（补充） ────────
GET    /api/container/config/operators                # 获取操作员列表
GET    /api/container/config/operators?department=    # 按部门筛选操作员
```

### 告警规则 JSON 格式

```json
{
    "overdue_rules": {
        "enabled": true,
        "timeout_minutes": 60,
        "remind_interval_minutes": 10,
        "max_remind_count": 3
    },
    "outsource_rules": {
        "enabled": true,
        "remind_days": [3, 2, 1],
        "remind_times": ["08:00", "13:30"]
    }
}
```

### 验收标准

1. **配置 API 验收**：
   - [ ] `GET /api/container/config/alert_rules` 返回当前告警规则 JSON
   - [ ] `PUT /api/container/config/alert_rules` 接收 JSON 并更新规则
   - [ ] `GET /api/container/config/outsource_rules` 返回外协催单规则
   - [ ] `PUT /api/container/config/outsource_rules` 更新外协催单规则
   - [ ] 配置持久化到 tbl_configs

2. **告警记录 API 验收**：
   - [ ] `GET /api/container/alert/list` 返回告警记录列表（分页）
   - [ ] `GET /api/container/alert/list?level=CRITICAL` 按级别筛选
   - [ ] `GET /api/container/alert/list?alert_type=overdue` 按类型筛选
   - [ ] `POST /api/container/alert/<id>/dismiss` 将告警标记为已处理

3. **操作员配置验收**：
   - [ ] `GET /api/container/config/operators` 返回全部操作员
   - [ ] `GET /api/container/config/operators?department=XX` 按部门筛选

4. **通用验收**：
   - [ ] 所有端点统一 JSON 格式（成功/错误格式与 T1.2 一致）
   - [ ] X-Auth-Token 鉴权与 T1.2 一致
   - [ ] 参数校验完整

5. **测试验收**：
   - [ ] 测试配置的读写一致性
   - [ ] 测试告警记录的查询和筛选
   - [ ] 测试 dismiss 操作
   - [ ] 测试无效参数的错误响应

---

## 实现约束

### 技术栈
- Flask Blueprint（与 T1.2 注册方式一致）
- ConfigStore 读写 tbl_configs

### 接口规范
- 与 T1.2 共享统一响应格式
- 配置更新使用 PUT 全量替换，不支持局部更新

### 质量要求
- 配置写入时校验 JSON schema 合法性
- 告警规则字段校验（数值范围、enabled 布尔类型等）
- 禁止在 API 层直接操作数据库

---

## 依赖关系

### 前置任务
- **T1.1** 文档桶存储层（依赖 ConfigStore / AlertStore）
- **T1.2** 容器中心 HTTP API（复用蓝图注册方式）

### 后置任务
- **T2.3** 调度中心 P1 引用替换（告警规则配置 API 提供告警配置读写能力）
- **T3.3** 前端告警规则配置页面（前端页面调此 API）

### 并行任务
- **T2.1** 告警引擎迁移（与 T2.2 无直接依赖关系）

---

## 实施要点

1. **优先复用**：检查 T1.2 的 `api/` 目录中是否已有 config 相关路由，优先改造扩展现有蓝图
2. **配置格式**：告警规则配置的 JSON schema 需与 T2.1 AlertEngine 读取的格式一致
3. **默认配置**：首次读取时如果 tbl_configs 中没有配置，返回合理的默认值
