# 部署前快照索引

部署时间：2026-06-02
部署范围：8 个 TASK（TASK-003/005/006/008/011/014/017/018）

## 备份清单

| 文件 | 类型 | 状态 |
|------|------|------|
| `inventory_api_server.py` | 旧 v1 入口 | 备份 |
| `inventory_web/__init__.py` | 蓝图入口 | 备份 |
| `inventory_web/routes.py` | 路由聚合 | 备份 |
| `inventory_web/routes_api.py` | API 路由 | 备份 |

## 部署前关键发现

1. **`inventory_api_server.py` 是 v1 单文件实现**（行 1-219），不是 v2.3 蓝图架构
   - 硬编码 `user='root'`, `database='inventory_db'`, `secret_key='inventory_web_secret_2026'`, `ADMIN_PASSWORD='admin123'`
   - 登录页是内联 HTML（`return '''<!DOCTYPE html>...'''`）
   - 响应头未配置（无 X-Frame-Options / X-Content-Type-Options）
   - 已有 5 个 API 端点（health/query/inbound/outbound/alert）

2. **`inventory_web/` 蓝图目录不完整**：
   - 已有：`__init__.py`、`routes.py`、`routes_api.py`
   - 缺失：`db_utils.py`、`routes_core.py`、`routes_data.py`、`routes_system.py`

3. **`inventory_api_server.py` 第 203 行已注册 `web_bp` 蓝图**，但蓝图目录本身不完整，会导致 `ImportError`

4. **方案 T3-R 提到的 `PROJECT_ROOT` 不存在**于 `inventory_api_server.py`，需在 `routes_system.py` 定义

5. **`save_settings` 函数（routes_api.py:30-42）正在写 `password` 字段**到 `inventory_config.json` —— 必须按 TASK-018 拒绝

## 部署策略

| 策略 | 决策 |
|------|------|
| 重写 vs 增量改造 | **重写**（4 个新文件） |
| 备份位置 | `inventory_web/._backup_pre_v2.3/` |
| 入口 `inventory_api_server.py` | **完全重写**为 v2.3 |
| 数据库 schema | 不变更（使用现有 inventory_db） |
| 部署后端选择 | 内存（默认）+ Redis（可选） |

## 部署顺序

1. TASK-005（凭证/请求头）— 入口文件先行
2. TASK-003（路径/备份）— 系统路由
3. TASK-006（输入校验）— 数据路由
4. TASK-008（FOR UPDATE/死锁）— 核心业务
5. TASK-011（admin_required）— 装饰器
6. TASK-014（MAX_STOCK）— 业务规则
7. TASK-017（限流）— 入口
8. TASK-018（文件权限）— 系统路由
