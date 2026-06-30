# TASK 3.1：移除直引用 + 清理冗余代码

## 基本信息

| 字段 | 内容 |
|------|------|
| 任务ID | T3.1 |
| 任务名称 | 移除直引用函数 + 删除冗余代码 |
| 所属阶段 | 第三阶段（清理） |
| 预估工时 | 0.5天 |
| 优先级 | P1 |

---

## 输入契约（Input Contract）

### 前置依赖
- [ ] T1.4 调度中心 P0 引用替换已完成
- [ ] T2.3 调度中心 P1 引用替换已完成
- [ ] 全部直引用已通过 SDK 客户端替换完毕

### 输入数据
- `dispatch_center.py` 当前全部代码
- DESIGN 文档第 10 节中列出的需删除/改造的文件清单
- `integration/timeout_reminder.py` 全部代码

### 环境依赖
- `dispatch_center.py` 工程文件
- `integration/timeout_reminder.py` 工程文件

---

## 输出契约（Output Contract）

### 交付物

| 操作 | 文件 | 说明 |
|------|------|------|
| 删除 | `_get_container_center()` 函数 | 不再需要直引用 |
| 删除 | `_send_wechat_via_cloud()` 函数 | 全部替换为 client.send_message() |
| 删除 | 定时器中告警相关的调用 | 告警引擎已迁移到容器中心 |
| 删除 | `start_background_scheduler` 中的告警任务 | 同上 |
| 删除 | `integration/timeout_reminder.py` | 功能已合并到告警引擎 |
| 清理 | 不再使用的 import | `from container_center_v5 import ...` 等 |
| 保留 | `dispatch_center.py` 中的流程引擎 | 不受影响 |
| 保留 | `dispatch_center.py` 中的消息模板 | 本地功能，不受影响 |

### 验收标准

1. **代码清理验收**：
   - [ ] `_get_container_center()` 已从 `dispatch_center.py` 中删除
   - [ ] `_send_wechat_via_cloud()` 已删除
   - [ ] `integration/timeout_reminder.py` 已删除
   - [ ] 调度中心不再导入 `container_center_v5` 模块
   - [ ] 不再使用的 import 已全部清理

2. **功能完整性验收**：
   - [ ] 调度中心启动后不再产生 `container_center_v5` 相关警告
   - [ ] 调度中心核心流程（任务列表/派单/转派/消息发送）完全正常
   - [ ] 告警功能由容器中心独立运行，调度中心不参与告警检查

3. **测试验收**：
   - [ ] 调度中心单元测试全部通过
   - [ ] 调度中心冒烟测试通过
   - [ ] 容器中心告警引擎独立测试通过

---

## 实现约束

### 技术栈
- 纯文件编辑+删除操作
- 使用 Python 静态分析工具确认删除后无残留引用

### 接口规范
- 不改变调度中心和容器中心之间的通信接口
- 清理后不引入新的 import

### 质量要求
- 删除前确认该函数/文件没有任何地方再被调用
- 删除后运行全量测试确保不会出现 ImportError
- 禁止大段注释遗留，应该彻底删除而非注释掉

---

## 依赖关系

### 前置任务
- **T1.4** 调度中心 P0 引用替换（必须完成才能清理 P0 相关代码）
- **T2.3** 调度中心 P1 引用替换（必须完成才能清理 P1 相关代码）

### 后置任务
- **T3.2** 统一部署模式（清理后才方便统一部署）

### 并行任务
- **T3.3** 前端告警规则配置页面（无代码依赖）

---

## 实施要点

1. **先确认再删除**：在删除 `_get_container_center()` 前，确认 `dispatch_center.py` 中所有 `cc.xxx()` 调用已替换为 `client.xxx()`
2. **import 清理**：使用 IDE 或工具自动检测未使用的 import
3. **safe delete timeout_reminder.py**：删除前确认该文件无其他导入引用
