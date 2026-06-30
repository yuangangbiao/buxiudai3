# TODO：全面测试遗留事项

> 创建时间：2026-06-08

## 阻塞项（必须解决）

### P0-1：数据库缺 `direction` 列
- **位置**：`wechat_server.py` 中触发 `direction` 列的 SQL（云端）
- **影响**：`/api/sync/task/.../status` 和 `/api/sync/report` 返回 500
- **操作指引**：
  ```bash
  # 1. 在 MySQL 中查找使用 direction 的 SQL
  cd D:\yuan\不锈钢网带跟单3.0
  grep -rn "direction" mobile_api_ai/*.py | head -20
  # 2. 确认是 ORDER BY direction 还是 WHERE direction
  # 3. 给 process_sub_steps 加 direction 列（若业务需要）：
  #    ALTER TABLE process_sub_steps ADD COLUMN direction VARCHAR(16) DEFAULT 'forward';
  # 4. 重新部署云端 wechat_server.py
  # 5. 本地重跑：D:\yuan\test_venv\Scripts\python.exe D:\yuan\smoke_business.py
  ```

### P0-2：订单号验证正则不匹配
- **位置**：`wechat_server.py` 中 `validate_order_no`（云端）
- **影响**：`/api/sync/validate/input` 和 `/api/sync/task` 业务断链
- **操作指引**：
  ```bash
  # 1. 在云端代码中查找
  cd D:\yuan\不锈钢网带跟单3.0
  grep -n "validate_order_no\|订单号格式" mobile_api_ai/wechat_server.py | head -10
  # 2. 更新正则从 r'^[A-Z0-9-]{3,}$' 或类似 → r'^ORD-\d{8,}$'
  # 3. 重新部署云端
  # 4. 本地重跑 smoke_business.py 验证 #5、#8 通过
  ```

## 建议项（不阻塞，可后续优化）

### P1-1：外协发布协议不一致
- **症状**：`/api/sync/outsource/publish` 报"订单号、工序名和数量不能为空"
- **验证脚本**：
  ```bash
  # 用 JSON
  curl -X POST http://127.0.0.1:15003/api/sync/outsource/publish \
    -H "Content-Type: application/json" \
    -d '{"order_no":"ORD-202605020001","step_name":"焊接","quantity":10}'
  # 用 form
  curl -X POST http://127.0.0.1:15003/api/sync/outsource/publish \
    -d "order_no=ORD-202605020001&step_name=焊接&quantity=10"
  # 看哪个能成功
  ```

### P1-2：scripts 部署脚本安全加固
- **位置**：`mobile_api_ai/scripts/*.py` 共 10 处 `subprocess.Popen(..., shell=True)`
- **建议**：改为列表参数 + `shell=False`
- **影响**：仅本地工具脚本，无生产风险

### P1-3：F401 未使用 import 清理
- **数量**：547 项
- **建议**：用 `autoflake --in-place --remove-all-unused-imports -r mobile_api_ai` 一键清理
- **前置**：备份或 git 暂存

## 缺失配置

- 无（本轮测试环境 `.env` 完整）

## 文档

- 测试主报告：[ACCEPTANCE_全面测试.md](ACCEPTANCE_全面测试.md)
- 测试总结：[FINAL_全面测试.md](FINAL_全面测试.md)
