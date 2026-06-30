# 监控配置说明

## 文件清单
- `prometheus/dispatch_center.json` - Grafana 看板（8 图表）
- `prometheus/alerts.yml` - Prometheus 告警规则（6 条）

## 部署步骤

### 1. Prometheus 接入
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'dispatch_center'
    metrics_path: '/metrics'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:5003']
```

### 2. Grafana 导入看板
1. 登录 Grafana
2. 左侧菜单 → Dashboards → Import
3. 上传 `grafana/dispatch_center.json`
4. 选择 Prometheus 数据源

### 3. 告警规则部署
```bash
# 复制到 Prometheus 规则目录
cp prometheus/alerts.yml /etc/prometheus/rules/

# 重新加载 Prometheus
curl -X POST http://prometheus:9090/-/reload
```

## 看板内容（8 图）

| 编号 | 图表 | 监控指标 |
|:----:|------|----------|
| 1 | QPS (请求/秒) | dispatch_center_request_total |
| 2 | P95/P99 响应延迟 | dispatch_center_request_latency_seconds |
| 3 | 错误率 (%) | 5xx 状态码占比 |
| 4 | DLQ 队列大小 | dispatch_center_dlq_queue_size |
| 5 | DLQ 重试结果 | dispatch_center_dlq_retries_total |
| 6 | 业务事件 | dispatch_center_business_events_total |
| 7 | DB 连接池 | dispatch_center_db_pool_size |
| 8 | 缓存命中率 | dispatch_center_cache_total |

## 告警规则（6 条）

| 告警 | 条件 | 严重度 |
|------|------|:------:|
| HighErrorRate | 错误率 > 5% 持续 5min | 🔴 critical |
| HighLatency | P95 > 2s 持续 5min | 🟡 warning |
| DLQQueueGrowing | 队列 > 100 持续 10min | 🟡 warning |
| DLQPoisonedMessages | 1h 内 poison > 10 | 🔴 critical |
| DBPoolExhausted | DB 连接池使用 > 90% | 🟡 warning |
| LowCacheHitRate | 缓存命中率 < 50% 持续 15min | 🔵 info |

## 通知渠道
需在 Grafana/AlertManager 中配置企业微信/钉钉/邮件
