# 告警接收人 + 升级机制

> **生效日期**: 2026-07-02
> **维护人**: 运维 / 技术主管
> **最后审查**: 2026-07-02

---

## 一、5 项监控指标

| 指标 | 触发条件 | 告警级别 | 默认动作 |
|------|---------|---------|---------|
| **M1** P1 silent_drop 测试失败 | 单元测试失败 > 0 | 🔴 P0 | 立即通知（5 分钟升级） |
| **M2** dispatch_task 409 比例 | 409 响应 / 总响应 > 5% | 🟠 P1 | 30 分钟升级 |
| **M3** 影子表写入尝试 | block_write_deprecated 触发 > 0 | 🔴 P0 | 立即通知 |
| **M4** 业务表 5xx 错误 | 500 错误数 > 1/min | 🔴 P0 | 立即通知 + PagerDuty |
| **M5** JWT 鉴权失败 | 401 错误数 > 10/min | 🟠 P1 | 30 分钟升级 |

---

## 二、告警接收人清单

### P0 告警（5 分钟升级机制）

| 顺序 | 接收人 | 联系方式 | 升级间隔 |
|------|--------|---------|---------|
| 1 | **老板（苑岗彪）** | wechat: yuan_gang_biao | 0 分钟（立即） |
| 2 | **技术主管** | wechat: tech_lead | 5 分钟未响应 |
| 3 | **运维值班** | phone: 13800001111 | 15 分钟未响应 |
| 4 | **总监** | phone: 13800002222 | 30 分钟未响应 |

### P1 告警（30 分钟升级机制）

| 顺序 | 接收人 | 联系方式 | 升级间隔 |
|------|--------|---------|---------|
| 1 | **技术主管** | wechat: tech_lead | 0 分钟（立即） |
| 2 | **老板** | wechat: yuan_gang_biao | 30 分钟未响应 |

### P2 告警（4 小时升级机制）

| 顺序 | 接收人 | 联系方式 | 升级间隔 |
|------|--------|---------|---------|
| 1 | **技术主管** | wechat: tech_lead | 0 分钟 |
| 2 | 群通知 | wechat group | 4 小时未响应 |

---

## 三、升级机制详解

### P0 流程（紧急）

```
00:00  触发告警 → 企业微信推送给老板
00:05  老板未确认 → 推送给技术主管
00:15  技术主管未响应 → 短信给运维值班
00:30  运维未响应 → 电话给总监
00:60  仍无响应 → PagerDuty 升级
```

### P1 流程（警告）

```
00:00  触发告警 → 企业微信推送给技术主管
00:30  未确认 → 推送给老板
```

### P2 流程（提示）

```
00:00  触发告警 → 企业微信群通知
04:00  未确认 → 技术主管个人推送
```

---

## 四、通知模板

### 模板 1：P0 严重告警

```
【P0 严重告警】data_packages_split_v3

时间: 2026-07-02 18:30
指标: M4 业务表 5xx 错误
当前值: 25 错误/min（阈值 1/min）
影响: 用户报工/查单可能失败
责任: 技术主管

立即操作:
1. 查看 Grafana: http://grafana/d/dashboard
2. 查看日志: docker logs mobile_api_5002 --tail=200
3. 回滚: git revert HEAD~5

5 分钟未响应将自动升级到运维值班。
```

### 模板 2：P1 警告

```
【P1 警告】data_packages_split_v3

指标: M2 dispatch_task 409 比例
当前值: 8%（阈值 5%）
原因: 派工并发冲突（不是 bug，是数据竞争）
建议: 监控趋势，无需立即处理
```

### 模板 3：影子表写入

```
【P0 触发】data_packages_deprecated 写入尝试

时间: 2026-07-02 18:30
来源 IP: 192.168.1.100
调用方: container_center_api.py:1557
说明: 有代码仍在写 data_packages，请检查 v3.6 改造遗漏
责任: 技术主管

⚠️ 紧急: DROP data_packages 前必须修复此问题！
```

---

## 五、监控仪表盘

### Grafana 配置

```yaml
# grafana_dashboard.json
dashboard: data_packages_v3
panels:
  - title: P1 silent_drop 测试
    metric: pytest_failed_count
    threshold: 0
  - title: 409 比例
    metric: dispatch_409_ratio
    threshold: 5%
  - title: 5xx 错误数
    metric: http_5xx_count
    threshold: 1/min
  - title: JWT 失败数
    metric: jwt_auth_fail_count
    threshold: 10/min
```

### Prometheus 指标

```yaml
# prometheus_alerts.yml
groups:
  - name: data_packages_v3
    rules:
      - alert: SilentDropTestFailed
        expr: pytest_silent_drop_failed > 0
        for: 1m
        labels:
          severity: critical
      - alert: Dispatch409High
        expr: rate(dispatch_409_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
```

---

## 六、值班表

| 日期 | 早班（08-16） | 晚班（16-24） | 夜班（00-08） |
|------|--------------|--------------|--------------|
| 2026-07-02 | 技术主管 | 老板 | 运维值班 |
| 2026-07-03 | 老板 | 技术主管 | 运维值班 |
| 2026-07-04 | 运维值班 | 老板 | 技术主管 |

---

## 七、误报处理

如收到误报：
1. 5 分钟内回复「误报」+ 原因
2. 技术主管 1 小时内调整阈值
3. 记录到误报日志

---

**最后审查**: 2026-07-02 ✅
