# TODO — RE-002 消息触发链路修复 · 待办与配置

> 用户确认交付时关注

## 一、上线待办（用户执行）

- [ ] **重启 dispatch_center 服务**
  ```bash
  cd d:\yuan\不锈钢网带跟单3.0
  python mobile_api_ai/dispatch_center.py --port 5003
  ```
  目的：触发 `schedule_records` DDL 建表 + 蓝图重载新消息调用

- [ ] **验证群消息可达性**（`.env` 中 `WECHAT_WORK_BOT_URL` 已在前序步骤配置）
  ```bash
  curl -X POST http://127.0.0.1:5003/api/sync/report \
    -H "Content-Type: application/json" \
    -d '{"order_no":"RE002-VERIFY","process":"焊接","quantity":1,"operator":"verifier"}'
  ```
  期望：HTTP 200 + 企业微信群出现"报工提交"消息

- [ ] **失败容错验证**（可选）
  关闭外网或篡改 `WECHAT_WORK_BOT_URL`，再调一次 `/report`，确认：
  - HTTP 仍返 200
  - 日志出现 `报工消息发送失败` warning

## 二、暂时无需处理

- 云端 `wechat_server.py`：本任务不涉及云端修改
- 排产接口回归：MySQLStorage 补方法后原有 500 已自动恢复

## 三、可选优化（不在本任务范围）

- 排产消息触发：`/api/schedule/submit` 和 `/api/schedule/confirm` 修好 500 后，可参考本任务的 `tmpl_schedule_submitted/confirmed/rejected` 模板补群消息调用
- 消息发送链路监控：可在 CloudPoller 中加成功率埋点
- 模板可视化编辑：当前 `template_engine.py` 仍是字典结构，可考虑迁移到 DB

## 四、文档归档

任务全部完成，需要执行 P9 归档（移动构想文件 → 现实文件）：
- 源：`d:\yuan\构想文件\RE-002_消息触发链路修复\`
- 目标：`d:\yuan\现实文件\RE-002_消息触发链路修复\`
