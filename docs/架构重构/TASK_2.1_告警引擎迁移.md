# TASK 2.1：告警引擎迁移

## 基本信息

| 字段 | 内容 |
|------|------|
| 任务ID | T2.1 |
| 任务名称 | 告警引擎从调度中心迁移到容器中心 |
| 所属阶段 | 第二阶段（P1） |
| 预估工时 | 1天 |
| 优先级 | P1 |

---

## 输入契约（Input Contract）

### 前置依赖
- [ ] T1.2 容器中心 HTTP API 已完成（告警引擎依赖数据 API 查询文档）
- [ ] T1.1 文档桶存储层已完成（告警引擎依赖 AlertStore / ConfigStore）
- [ ] `dispatch_center.py` 中 `_check_overdue_tasks()` 和 `_check_outsource_reminders()` 的完整代码已阅读

### 输入数据
- `dispatch_center.py` 中 `_check_overdue_tasks()` 全部代码逻辑
- `dispatch_center.py` 中 `_check_outsource_reminders()` 全部代码逻辑
- `dispatch_center.py` 中 `start_background_scheduler` 定时器初始化代码
- 现有告警规则（告警配置阈值、提醒间隔等）的存储方式和数据结构
- T1.1 的 DocumentStore / AlertStore / ConfigStore / IndexStore 接口签名
- 现有 `cloud_poller.py` 中消息发送接口

### 环境依赖
- Python 3.8+
- threading 模块（后台定时线程）
- T1.1 storage 模块（DocumentStore / AlertStore / ConfigStore）

---

## 输出契约（Output Contract）

### 交付物

| 文件 | 职责 | 说明 |
|------|------|------|
| `container_center/services/__init__.py` | 模块初始化 | 导出 AlertEngine |
| `container_center/services/alert_engine.py` | 告警引擎 | AlertEngine 类 |
| `container_center/services/message_service.py` | 消息服务 | 封装消息发送逻辑 |

### 核心接口

```python
class AlertEngine:
    def __init__(self, document_store, alert_store, config_store, message_service): ...

    def check_overdue_tasks(self) -> List[Dict]:
        """检查超时未完成的工单，生成告警记录"""

    def check_outsource_reminders(self) -> List[Dict]:
        """检查外协催单条件，生成告警记录并发送通知"""

    def start(self, interval_seconds=60):
        """启动后台定时线程，周期性执行检查"""

    def stop(self):
        """停止后台定时线程"""
```

### 验收标准

1. **功能验收**：
   - [ ] `check_overdue_tasks()` 逻辑与原始 `_check_overdue_tasks()` 完全一致
   - [ ] `check_outsource_reminders()` 逻辑与原始 `_check_outsource_reminders()` 完全一致
   - [ ] 超时检测：按告警规则配置的超时时间阈值检测工单，生成告警记录到 tbl_alerts
   - [ ] 外协催单：按配置的时间节点检测外协单，发送通知并记录告警
   - [ ] 重复告警抑制：已告警过的工单在间隔时间内不再重复告警

2. **告警记录验收**：
   - [ ] 生成的告警记录写入 tbl_alerts，包含 alert_type / doc_id / title / content / level
   - [ ] 告警区分 WARNING（提醒）和 CRITICAL（超时严重）

3. **后台线程验收**：
   - [ ] `start()` 启动后台线程，按 interval_seconds 间隔执行
   - [ ] `stop()` 优雅停止线程（不阻塞）
   - [ ] 线程异常不影响主进程（异常被捕获并记录日志）

4. **配置读取验收**：
   - [ ] 告警规则从 ConfigStore（tbl_configs）读取
   - [ ] 无配置时使用安全的默认值（不告警）
   - [ ] 配置变更后下次检查周期自动生效

5. **测试验收**：
   - [ ] 单元测试覆盖超时检测逻辑（准备过期/未过期工单数据验证）
   - [ ] 单元测试覆盖外协催单逻辑
   - [ ] 单元测试覆盖重复告警抑制
   - [ ] 使用 MockDocumentStore / MockAlertStore 进行隔离测试

---

## 实现约束

### 技术栈
- Python threading 模块（后台定时器）
- 与现有 `container_center_v5.py` 中 `start_background_scheduler` 相同风格的线程管理
- 复用项目中现有的 logger 配置

### 接口规范
- AlertEngine 对外暴露 `start() / stop()` 生命周期方法
- 告警规则通过 ConfigStore 读写，格式为 JSON
- 告警记录通过 AlertStore 写入

### 质量要求
- 后台线程的异常不能传播到主线程（`threading.Thread` daemon = True + try/except）
- 告警规则配置变更后，下一个检查周期自动生效（不需要重启）
- 禁止在 AlertEngine 中直接操作 SQLite，必须通过 Store 类
- 迁移后的告警引擎不能产生重复告警（需实现去重逻辑）

---

## 依赖关系

### 前置任务
- **T1.1** 文档桶存储层（依赖 DocumentStore / AlertStore / ConfigStore）
- **T1.2** 容器中心 HTTP API（依赖数据 API 获取文档数据）

### 后置任务
- **T2.3** 调度中心 P1 引用替换（告警引擎迁移后，调度中心可移除定时器和告警相关代码）
- **T3.1** 移除直引用 + 清理代码（告警引擎迁移后清理调度中心冗余代码）

### 并行任务
- **T2.2** 告警规则配置 API（与 T2.1 无直接依赖关系）

---

## 实施要点

1. **保持逻辑完全一致**：将 `_check_overdue_tasks()` 和 `_check_outsource_reminders()` 的代码原样迁移，不做功能重构
2. **配置读取改造**：原调度中心从本地配置读取告警阈值，迁移后从 ConfigStore（tbl_configs）读取
3. **消息发送**：告警触发后的消息发送通过 MessageService（内部调 CloudPoller）完成
4. **告警去重**：通过 `tbl_alerts` 查询最近 N 分钟内同一 doc_id + alert_type 的记录，避免重复
