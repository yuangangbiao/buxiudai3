# SLO 监控指标

## 定义
| 指标 | 目标 | 测量方式 |
|------|------|---------|
| 订单创建延迟 | P99 < 2s | Prometheus histogram |
| 报工回调延迟 | P99 < 5s | Prometheus histogram |
| 大屏加载 | < 3s | 浏览器 Navigation Timing |
| 健康检查成功率 | > 99.9% | Prometheus counter |

## Grafana 仪表盘
- 订单量趋势（24h）
- 工序完成率（按天）
- 异常率（按小时）
- SLO 达标率（月度）
- 数据库连接池使用率

## 告警规则
- 订单积压 > 50 → 企微通知
- 数据库连接池 < 5 → 紧急通知
- 容器中心健康检查失败连续3次 → 告警
