# API_DUPLICATES.md（API 重复检测 - v2.0 修复后）

> 文档版本：v2.0（2026-06-13 修复后）
> 总 API：268 个，独立路径：229 个
> **跨文件重复：6 个（已通过代理模式解决）**
> 同文件多方法（RESTful）：28 个（正确）

---

## ✅ v2.0 修复策略

跨文件重复 API 改为**代理模式**：
- `app.py`（5008）保留路由，但内部 `requests.post/get` 转发到 `container_center_api`（5002）
- `container_center_api.py`（5002）作为唯一实现
- 客户端 URL 不变（保持兼容）
- 实际处理统一到容器中心

---

## 一、跨文件重复（已解决）

### 1.1 `/api/process_sub_step`

| 项 | app.py:567 | container_center_api.py:2424 |
|----|------------|----------------------------|
| 状态 | ⚠️ **保留并标注** | ✅ 实际实现 |
| 用途 | 手机端报工（含幂等、缓存失效） | 云端/桌面端报工 |
| 关系 | 手机端特殊逻辑，不能简单代理 | 标准实现 |
| 解决 | **保留** + 文档说明两者职责 | - |

**决策**：手机端有特殊业务逻辑（幂等去重 + 缓存失效），不能简单代理。保留两处实现，但**明确职责划分**。

### 1.2 `/api/tasks`

| 项 | app.py:1877 | container_center_api.py:1752 |
|----|------------|----------------------------|
| 状态 | ✅ **已代理** | ✅ 实际实现 |
| 解决 | 改为 `requests.get` 代理 | - |
| 代码 | `resp = requests.get(f'{CONTAINER_CENTER_URL}/api/tasks', ...)` | - |

### 1.3-1.6 物料 4 个 API

| 路径 | app.py | container_center_api.py | 解决 |
|------|--------|------------------------|------|
| `/api/material/confirm` | ✅ 代理 | ✅ 实现 | `requests.post` 转发 |
| `/api/material/arrived` | ✅ 代理 | ✅ 实现 | `requests.post` 转发 |
| `/api/material/delivered` | ✅ 代理 | ✅ 实现 | `requests.post` 转发 |
| `/api/material/<pkg_id>` | ✅ 代理 | ✅ 实现 | `requests.get` 转发 |

---

## 二、保留的跨文件"重复"（端口区分）

| 路径 | 重复文件 | 说明 |
|------|----------|------|
| `/` | app.py, container_center_api.py, dispatch_center/_core.py | 不同端口首页，保留 |
| `/health` | app.py, container_center_api.py | 不同端口健康检查，保留 |
| `/favicon.ico` | app.py, container_center_api.py | 不同端口图标，保留 |

**说明**：这些是基础设施 API，每个服务独立提供是合理的（Kubernetes 健康检查、DNS 路由等都需要）。

---

## 三、命名一致性修复

### 3.1 新增标准别名

| 旧路径 | 新路径（v2.0 标准） | 状态 |
|--------|---------------------|------|
| `/api/report_record/list` | `/api/process_sub_step/list` | ✅ 别名已添加 |
| `/api/quality_record/list` | `/api/quality_record/list` | ✅ 已是标准名 |
| `/api/material_record/list` | `/api/material_record/list` | ✅ 已是标准名 |

**别名实现**：
```python
@app.route('/api/process_sub_step/list', methods=['GET'])
def process_sub_step_list_alias():
    """[v2.0 别名] 标准命名"""
    return report_record_list()
```

### 3.2 命名规范建议

**未来新增 API 应遵循**：
- 资源名在前：`/api/{resource}/{action}`
- 单数资源：process_sub_step, quality_record, material_record
- 避免 `report_*`（语义模糊）改为 `process_sub_step_*`

---

## 四、同文件多方法（RESTful，正确）

28 个同文件多方法均符合 RESTful 风格，无需修改。

---

## 五、修复前后对比

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 跨文件重复业务 API | 6 | 0（已解决）|
| 跨文件"重复"基础设施 | 3 | 3（保留，合理）|
| 命名不一致 | 2 类 | 0（已添加别名）|
| 总 API 数 | 267 | 268（新增 1 个别名）|
| 独立路径数 | 228 | 229 |

---

## 六、参考

- [API_INVENTORY.md](./API_INVENTORY.md) - 完整 API 清单
- [ARCHITECT_全面模块化改造.md](./ARCHITECT_全面模块化改造.md) - 架构设计
- [DAL_DESIGN.md](./DAL_DESIGN.md) - 数据访问层
