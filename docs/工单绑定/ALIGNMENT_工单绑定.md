# ALIGNMENT - 工单信息绑定至容器中心规则配置

## 一、原始需求

> **主软件订单排产任务发布后，在容器中心规则配置上增加工单信息，当物料需求发布后把数据绑定在该工单下面，工序任务和质检任务也归类到该订单下**

## 二、需求理解

### 2.1 核心目标

在容器中心（wechat_server 侧的 container_center_v5）的规则配置体系中，建立**工单（Work Order）** 作为一级管理单元，使得：

1. **工单注册**：主软件发布排产任务后，工单信息自动注册到容器中心的规则配置中
2. **物料绑定**：物料需求发布时，数据自动关联到对应的工单
3. **工序绑定**：工序任务发布时，归类到对应工单下
4. **质检绑定**：质检任务发布时，归类到对应工单下

### 2.2 当前系统分析

| 组件 | 说明 |
|------|------|
| **主软件 (app.py:5000)** | 不锈钢自动跟单系统3.0版，通过 schedule_flow.py 发布排产任务 |
| **容器中心 (wechat_server:5003)** | 使用 container_center_v5.py，含 DataPackage/DataCollector 数据模型 |
| **容器配置 (container_config.py)** | 管理操作员、工序、数据类型、报修种类等配置 |
| **容器池API (container_api_server.py:5002)** | 独立的任务池系统，与容器中心分属不同体系 |

### 2.3 现有数据模型分析

**DataPackage（container_center_v5.py）** 已有字段：
- `related_order: Optional[str]` - 关联订单号
- `related_process: Optional[str]` - 关联工序名
- `target_operator: Optional[str]` - 目标操作员
- `tags: List[str]` - 标签

**ContainerConfig（container_config.py）** 已有配置：
- `operators` - 操作员管理
- `processes` - 工序配置
- `data_types` - 数据类型
- `repair_categories` - 报修种类
- `notification` - 通知配置

**缺少**：工单（WorkOrder）配置管理单元

### 2.4 数据流分析

```
主软件排产发布 (schedule_flow.py /api/schedule/publish)
    ↓
创建排产记录 (storage.save_schedule_record)
    ↓
发送微信通知
    ↓
[当前] 容器中心没有记录该工单信息
[目标] 自动注册工单到容器中心规则配置
    ↓
后续物料/工序/质检发布时需要关联到此工单
```

## 三、边界确认

### 3.1 包含范围
- ✅ 在 container_config.py 中增加工单（WorkOrder）配置管理
- ✅ 排产发布时自动注册工单到容器中心规则配置
- ✅ 物料需求发布时通过 related_order 绑定到工单
- ✅ 工序任务发布时归类到对应工单
- ✅ 质检任务发布时归类到对应工单
- ✅ 在 container_config.html 增加工单管理标签页

### 3.2 不包含范围
- ❌ 不修改 container_api_server.py（port 5002 的独立容器池系统）
- ❌ 不涉及主软件数据库结构变更
- ❌ 不涉及 WeChat 通知逻辑修改
- ❌ 不涉及排产流程（schedule_flow.py）的业务逻辑变更

## 四、技术方案概要

### 4.1 方案思路

在容器中心规则配置中新增 **工单规则（WorkOrderRule）** 配置类，作为工单信息的统一管理入口：

1. **WorkOrderRule 配置类**：记录工单号、客户名、产品、状态、关联任务列表等
2. **自动注册**：在主软件排产发布时，通过 API 通知容器中心注册工单
3. **任务绑定**：物料/工序/质检任务发布时，通过容器中心 API 自动绑定到工单
4. **可视化**：在 container_config.html 增加工单管理标签页

### 4.2 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 工单数据存储 | container_config.py 内存 + JSON 文件持久化 | 与现有配置体系一致 |
| 工单注册方式 | schedule_flow.py 发布时调用容器中心 API | 松耦合，不直接依赖 |
| 任务绑定机制 | 通过 DataPackage.related_order 字段 | 现有字段已支持，无需扩展 |

## 五、疑问澄清

| 问题 | 回答 |
|------|------|
| Q: 物料/工序/质检任务通过哪个接口发布到容器中心？ | A: 通过 wechat_server 已有接口 `/api/sync/task` 或新增 `/api/sync/material` 等 |
| Q: 工序任务是主软件发布还是容器中心自行创建？ | A: 主软件排产提交时（阶段3）会提交工序计划，需要绑定到工单 |
| Q: 容器中心规则配置中的工单信息需要持久化吗？ | A: 需要持久化，使用 JSON 文件存储（与操作员配置一致） |
| Q: 工单状态需要跟踪吗？ | A: 需要，至少跟踪已发布、执行中、已完成等状态 |

## 六、项目特性规范对齐

### 6.1 代码规范
- 无硬编码：所有配置项通过环境变量或配置文件读取
- 无裸露 except：所有异常处理必须记录日志
- 统一路径管理：使用 config.py 的 BASE_DIR

### 6.2 文档规范
- 所有函数添加函数级注释（功能描述、参数说明、返回值）
- 设计文档存储在 docs/工单绑定/ 目录

### 6.3 安全规范
- 不硬编码密码和 API 密钥
- 敏感配置从环境变量读取
