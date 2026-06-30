# TODO — 云端去除调度中心功能（待办清单）

> 阶段 6: Assess · 精简明确待办事项 + 缺失配置 + 操作指引
> 时间：2026-06-08
> 状态：项目已交付，剩余环境/云端动作清单

---

## 一、云端 DBA 必做（高优先级）

### 1.1 F1 阻塞：operation_logs.direction 列缺失  ✅ 已闭环（2026-06-08）

**状态**：本地 5003 启动时自动加列（[standalone_dispatch_server.py:L207-251](file:///D:/yuan/%E4%B8%8D%E9%94%90%E9%92%A2%E7%BD%91%E5%B8%A6%E8%B7%9F%E5%8D%953.0/mobile_api_ai/standalone_dispatch_server.py#L207-L251) `_ensure_operation_logs_direction()`）

**方案 A 自检逻辑**：
1. 查 `information_schema.columns` 判 `direction` 列存在性
2. 不存在 → `ALTER TABLE operation_logs ADD COLUMN direction VARCHAR(16) DEFAULT '上游' AFTER id`
3. 并发安全：捕 `Duplicate column name` 错误码 1060 视为成功
4. 失败非致命：logger.error 不阻塞 5003 启动

**验证结果**（2026-06-08 20:38）：
- 列已加：`id int / direction varchar(16) / order_id int / order_no varchar(50) / module varchar(50) / action varchar(50) ...`
- smoke_sync_bp.py 重跑：`GET /api/sync/logs` 500 → **200**，4 读类端点全 PASS

**云端后续**：
- 云端 DBA 仍可独立执行（不冲突），建议同步到云端 wechat_server 启动脚本
- 本地自检 SQL 与云端 DBA 手动 SQL 等价，可由云端 DBA 决定是否保留本地自检

---

## 二、本地验证（重启后跑）

### 2.1 重启服务

```bash
# 8008 同步桥（加载新增 /report-confirm + report_request 表自检）
cd D:\yuan\不锈钢网带跟单3.0\mobile_api_ai
python sync_bridge.py --port 8008

# 5003 调度中心（补注册 3 蓝图）
python standalone_dispatch_server.py --port 5003
```

### 2.2 跑测试

```powershell
$env:PYTHONIOENCODING="utf-8"
D:\yuan\test_venv\Scripts\python.exe D:\yuan\smoke_sync_bp.py
```

**预期**：26 用例 22 PASS / 0 FAIL / 4 WARN

### 2.3 健康检查

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:5003/health -UseBasicParsing
Invoke-WebRequest -Uri http://127.0.0.1:8008/health -UseBasicParsing
```

---

## 三、云端后续动作（中优先级）

### 3.1 删除云端 22 个 `/api/sync/*` 业务端点

**前提**：所有桌面端/小程序已切换到 5003 调用（**当前未切换**）

**操作**：
- 编辑 `mobile_api_ai/wechat_server.py`，注释或删除 22 个 `/api/sync/*` route
- 保留 `/api/wechat/*`、`/api/cloud/*` 微信回调
- 部署到云端

**风险**：
- 桌面端/小程序可能硬编码云端 URL（如 `http://124.223.57.82:15003/api/sync/report`）
- 删除前需 grep 全部客户端代码确认无引用

**建议**：保持现状 1-2 周观察期，确认无引用后再删。

### 3.2 关闭 `wechat_server_cloud_only.md` 例外条款

**时机**：TASK-1~10 全部通过 + 云端 22 端点删除后

**操作**：编辑 `.trae/rules/wechat_server_cloud_only.md`，删除"临时例外"段，恢复"禁止本地修改"硬规则。

---

## 四、可选优化（低优先级）

### 4.1 8008 /report-confirm 加事务包裹

**当前**：单 INSERT 无事务, 5min 幂等是软保证（重复无害）

**优化**：
```python
with conn.cursor() as c:
    c.execute("START TRANSACTION")
    # SELECT 幂等 + INSERT
    c.execute("COMMIT")
```

**收益**：极端并发下杜绝重复（实测 5min 窗口无重复）

### 4.2 _CircuitBreaker 单例改 Redis

**当前**：模块级单例, 多 worker 进程不共享

**优化**：用 Redis Hash 存 failure_count / state

**收益**：8 worker 进程下统一熔断状态

**前置**：项目接入 Redis（目前仅用 MySQL）

### 4.3 sync_bp 业务操作类 404 → 业务错误码

**当前**：容器中心无工单时返 404

**优化**：返 `{code: 4041, message: '工单不存在', f1_required: false}`

**收益**：前端能区分端点缺失 vs 业务缺失

---

## 五、文件状态切换（项目归档）

按 [构想文件管理规范](file:///D:/yuan/.trae/rules/%E6%9E%84%E6%83%B3%E6%96%87%E4%BB%B6%E7%AE%A1%E7%90%86%E8%A7%84%E8%8C%83.md)：

**当前状态**：本项目位于 `D:\yuan\不锈钢网带跟单3.0\docs\云端去除调度中心功能\`，**仍属"构想文件"**。

**待用户确认**：
- 项目代码、测试、文档均已完整实现并通过
- 待用户最终验收后，可将本目录从 `构想文件\` 移动到 `现实文件\`
- 移动完成后清理原 `构想文件\云端去除调度中心功能\` 目录

**操作步骤**：
```bash
# 1. 创建现实文件目录
mkdir D:\yuan\现实文件\云端去除调度中心功能

# 2. 移动文档
move D:\yuan\构想文件\云端去除调度中心功能\* D:\yuan\现实文件\云端去除调度中心功能\

# 3. 确认后清理
rmdir D:\yuan\构想文件\云端去除调度中心功能
```

**询问用户**：是否现在执行状态切换？还是有其他事项先处理？

---

## 六、紧急回滚预案

如本地 5003/8008 出现严重问题：

1. **5003 回滚**（移除 sync_bp 注册）：
   ```python
   # standalone_dispatch_server.py
   # 注释 TASK-8 补注册的 3 段 try-except
   ```

2. **8008 回滚**（移除 /report-confirm）：
   ```python
   # sync_bridge.py
   # 删除 api_sync_report_confirm 函数 + _ensure_report_request_table 调用
   ```

3. **完整回滚**（恢复到 22 端点全在云端）：
   ```bash
   # 1. 还原 sync_bp.py, sync_bridge.py, standalone_dispatch_server.py 到 commit 前
   # 2. 重启 5003 / 8008
   # 3. 桌面端切回云端 15003 URL
   ```

---

**TODO 维护人**：结对编程 Agent
**下次复查**：云端执行 F1 修复 SQL 后
