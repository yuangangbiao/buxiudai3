---
name: "msg-template-manager"
description: "消息模板管理器。触发词：更新模板、修改模板、模板变更、所有模板。功能：(1) 指定模板ID更新单个模板；(2) 批量更新所有模板；(3) 查询模板列表；(4) 根据ID查询模板内容。"
---

# 消息模板管理器

消息模板存储在 MySQL `message_templates` 表，MySQL 优先 + 内置兜底。

## 模板结构

```sql
SELECT id, name, category, channels, content, is_active FROM message_templates;
```

## Category 中文对照

| Category | 中文 |
|----------|------|
| alert | 告警 |
| cost | 成本 |
| material | 物料 |
| other | 其他 |
| process | 流程 |
| schedule | 排产 |
| task | 报工 |
| quality | 质检 |

## Channels 中文对照

| Channels | 中文 |
|----------|------|
| wechat_group | 群聊 |
| wechat_app | 个人 |
| wechat_group, wechat_app | 群聊+个人 |

## 查询模板列表

**SQL**:
```sql
SELECT id, name, category, channels, is_active FROM message_templates ORDER BY category, name;
```

**中文显示格式**:
```
【告警】
  tmpl_alert_timeout | 任务超时告警 | 群聊
```

## 根据ID查询模板内容

当用户说"查看 tmpl_schedule_confirmed 的内容"或"查询 tmpl_workorder_created"时：

**SQL**:
```sql
SELECT id, name, category, channels, content FROM message_templates WHERE id='tmpl_schedule_confirmed';
```

**中文显示格式**:
```
ID: tmpl_schedule_confirmed
名称: 排产已确认通知
分类: 排产
渠道: 群聊
内容:
━━━━━━━━━━━━━━━━━━━━
🎉 **排产已确认**
━━━━━━━━━━━━━━━━━━━━
工单: {订单号}
客户: {客户}
产品: {产品}
数量: {数量} {单位}
━━━━━━━━━━━━━━━━━━━━
```

## 更新模板

### 方式1：指定模板更新

当用户说"更新 tmpl_schedule_confirmed 模板"时：

```sql
-- 查看当前内容
SELECT id, name, content FROM message_templates WHERE id='tmpl_schedule_confirmed';

-- 更新内容
UPDATE message_templates SET content='新内容 {变量}' WHERE id='tmpl_schedule_confirmed';
```

### 方式2：全部模板更新

当用户说"更新所有模板"或"批量修改模板"时：

```sql
-- 查看所有模板
SELECT id, name, content FROM message_templates;
```

## 注意事项

1. **保留占位符**: `{变量名}` 格式不可更改
2. **重启服务**: 模板变更立即生效（MySQL 查询）
3. **验证**: 修改后重新查询确认
4. **MySQL 优先**: 所有模板优先从 MySQL 读取，内置模板仅作兜底
