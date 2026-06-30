# TASK 1.4：调度中心 P0 级直引用替换

## 基本信息

| 字段 | 内容 |
|------|------|
| 任务ID | T1.4 |
| 任务名称 | 调度中心 P0 级直引用替换为 SDK 调用 |
| 所属阶段 | 第一阶段（P0） |
| 预估工时 | 0.5天 |
| 优先级 | P0（最高） |

---

## 输入契约（Input Contract）

### 前置依赖
- [ ] T1.3 SDK 客户端已完成并可实例化
- [ ] T1.2 容器中心 HTTP API 已部署并可访问
- [ ] `dispatch_center.py` 全部引用已梳理清晰

### 输入数据
- DESIGN 文档 3.1 节映射表中 P0 级直引用清单
- 现有 `dispatch_center.py` 中所有 `cc.storage.xxx()` 和 `_send_wechat_via_cloud()` 的调用位置
- T1.3 交付的 ContainerCenterClient 类

### 环境依赖
- Python 3.8+
- `dispatch_center.py` 工程文件
- T1.3 SDK client 模块

---

## 输出契约（Output Contract）

### 交付物
- 改造 `dispatch_center.py`

### P0 替换范围

| 原直引用 | 出现次数 | 替换为 |
|---------|:-------:|--------|
| `cc.storage.get_packages(limit=N)` | 6处 | `client.get_packages(doc_type, status, limit)` |
| `cc.storage.get_package(id)` | 3处 | `client.get_package(id)` |
| `cc.storage.save_package(pkg)` | 2处 | `client.save_package(data)` |
| `cc.storage.update_package(id, fields)` | 3处 | `client.update_document(id, fields)` |
| `cc.storage.update_package_status(id, status)` | 2处 | `client.update_document_status(id, status)` |
| `_send_wechat_via_cloud(...)` | 3处直接+~15处间接 | `client.send_message(content, to)` |

### 验收标准

1. **引用替换验收**：
   - [ ] 全部 6 处 `get_packages()` 替换完成，返回值格式无变化
   - [ ] 全部 3 处 `get_package()` 替换完成
   - [ ] 全部 2 处 `save_package()` 替换完成
   - [ ] 全部 3 处 `update_package()` 替换完成
   - [ ] 全部 2 处 `update_package_status()` 替换完成
   - [ ] 全部 ~18 处 `_send_wechat_via_cloud()` 替换为 `send_message()`

2. **兼容性验收**：
   - [ ] 替换后调度中心功能与替换前完全一致
   - [ ] 任务列表显示正常
   - [ ] 任务创建正常
   - [ ] 任务状态更新正常
   - [ ] 消息发送正常

3. **代码质量验收**：
   - [ ] `_get_container_center()` 不再用于 P0 功能
   - [ ] 导入方式改为 `from container_center.client import ContainerCenterClient`
   - [ ] 使用 `CONTAINER_CENTER_URL` 环境变量配置服务地址（禁止硬编码）
   - [ ] 替换后的异常处理不降级

4. **测试验收**：
   - [ ] 调度中心单元测试全部通过
   - [ ] 调度中心冒烟测试通过（任务流程 + 消息发送）

---

## 实现约束

### 技术栈
- 纯文本替换 + 人工校验
- SDK 客户端在 `dispatch_center.py` 启动时初始化

### 接口规范
- 替换后的调用语义与原来一致
- 方法参数保持相同顺序和默认值
- 禁止修改现有业务逻辑，仅替换调用方式

### 质量要求
- 逐行审查替换结果，确保没有漏替换
- 替换后运行调度中心全部测试用例
- 替换后的异常处理不降级（原 try/except 保留）

---

## 依赖关系

### 前置任务
- **T1.3** SDK 客户端（替换的载体工具）

### 后置任务
- **T2.3** 调度中心 P1 引用替换（P1 级替换必须在 P0 之后）
- **T3.1** 移除直引用 + 清理代码（P0/P1 都完成后统一清理）

### 并行任务
- 无（T1.4 依赖 T1.3）

---

## 实施要点

1. **优先复用**：在 `dispatch_center.py` 中搜索 `cc.storage` 的所有出现位置，逐行确认替换
2. **不做功能重构**：本次仅替换调用方式，不改变业务逻辑
3. **灰度验证**：替换一处验证一处，避免大面积替换后排查困难
4. **环境变量**：从 `os.environ['CONTAINER_CENTER_URL']` 读取，禁止硬编码
