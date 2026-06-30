# 监控告警方案 - v3.7.0

> **创建日期**: 2026-06-28
> **关联版本**: v3.7.0 架构重构（18周计划）
> **性质**: P0 文档，Week 0 建立，Week 1 验证，灰度放量前必须完成
> **目的**: 定义所有监控指标、告警阈值、通知渠道，让灰度Gate判断有数据可依

---

## 一、现状监控能力评估

### 1.1 已有监控

| 工具 | 覆盖范围 | 说明 |
|------|---------|------|
| **MySQL `SHOW PROCESSLIST`** | 数据库连接 | 可手动查看，实时 |
| **Flask日志** (`logs/`) | API错误 | 事后分析，无告警 |
| **企微群通知** | 人工推送 | 无自动触发 |
| **健康检查端点** `/api/health` | 服务存活 | 人工轮询 |
| **工人/老板反馈** | 业务异常 | 被动发现 |

### 1.2 缺失的监控能力

| 缺失项 | 影响 |
|--------|------|
| 无API成功率统计 | 无法判断G放量是否正常 |
| 无P99/P95响应时间 | 无法判断性能退化 |
| 无数据库连接池监控 | 无法提前发现连接泄漏 |
| 无并发压测自动化 | Gate4靠人工跑 |
| 无告警触发机制 | 出了事故才被动发现 |
| 无业务层监控 | 工人报工失败不知道 |

---

## 二、核心监控指标体系

### 2.1 四类指标（Dev方向）

> 技术指标：开发负责，数据来源为日志和APM。

| 指标名 | 计算方式 | 正常范围 | 告警阈值 | 数据来源 |
|--------|---------|---------|---------|---------|
| **API成功率** | `(2xx+3xx) / 总请求 × 100%` | ≥ 99.5% | < 99% | Nginx/Flask日志 |
| **API错误率** | `5xx / 总请求 × 100%` | ≤ 0.5% | > 0.5% | Nginx/Flask日志 |
| **P50响应时间** | 所有请求第50百分位 | ≤ 200ms | > 500ms | APM/日志聚合 |
| **P99响应时间** | 所有请求第99百分位 | ≤ 1000ms | > 1500ms | APM/日志聚合 |
| **数据库连接数** | `SHOW PROCESSLIST` 行数 | ≤ max 80% | > max 90% | MySQL |
| **数据库慢查询数** | `SHOW GLOBAL STATUS LIKE 'Slow_queries'` | ≤ 10/小时 | > 50/小时 | MySQL |
| **连接池使用率** | 活跃连接 / pool_size | ≤ 70% | > 85% | 日志/pool监控 |
| **错误日志速率** | 错误日志行数/时间窗口 | ≤ 1条/分钟 | > 10条/分钟 | 日志聚合 |

### 2.2 业务层指标（PM方向）

> 业务指标：PM小曦负责，数据来源为工厂反馈+日志分析。

| 指标名 | 正常表现 | 异常表现 | 监控方式 |
|--------|---------|---------|---------|
| **工人手机报工成功率** | ≥ 99% | 工人反馈"报不了" | 工厂对接人报告 |
| **老板浏览器数据加载** | ≤ 3秒 | 老板反馈"看不到" | 工厂对接人报告 |
| **质检提交成功率** | ≥ 99% | 质检员反馈"提交不了" | 工厂对接人报告 |
| **订单状态同步延迟** | ≤ 30秒 | 桌面端与移动端数据不一致 | 工厂对接人报告 |
| **微信推送送达率** | ≥ 95% | 工人没收到消息 | 企微后台统计 |

---

## 三、告警阈值矩阵

### 3.1 三级告警

| 级别 | 触发条件 | 响应时间 | 通知方式 | 处置人 |
|------|---------|---------|---------|--------|
| **🔴 P0 - 紧急** | API成功率 < 99%；服务完全不可用；任意服务5xx | 5分钟内响应 | 企微P0告警群+电话 | 开发负责人+PM+安全 |
| **🟠 P1 - 重要** | API错误率 > 1%；P99 > 1500ms；DB连接 > 90% | 15分钟内响应 | 企微告警群 | 开发+PM |
| **🟡 P2 - 提示** | P99 > baseline+500ms；错误日志 > 10条/分钟；连接池 > 85% | 1小时内响应 | 企微普通群 | 开发 |

### 3.2 详细阈值表

| 指标 | 🔴 P0 紧急 | 🟠 P1 重要 | 🟡 P2 提示 |
|------|-----------|-----------|-----------|
| API成功率 | < 99% | < 99.5% | < 99.8% |
| API错误率 | > 2% | > 1% | > 0.5% |
| P99响应时间 | > 3000ms | > 1500ms | > baseline+500ms |
| DB连接数 | > 95% | > 90% | > 80% |
| 错误日志速率 | > 50条/分钟 | > 10条/分钟 | > 5条/分钟 |
| 工人报工成功率 | < 98% | < 99% | < 99.5% |
| DB慢查询 | > 100/小时 | > 50/小时 | > 10/小时 |

---

## 四、监控工具选型与落地方案

### 4.1 现状约束

工厂系统未引入 Prometheus/Grafana，短期内不新增基础设施。
**因此采用"日志聚合+企微通知"的轻量方案。**

### 4.2 最小化监控方案（Week 0-1落地）

#### 方案A：Python脚本定时采集（推荐，无需改代码）

```python
# scripts/monitor.py — 每天cron定时执行，结果推企微

import pymysql, requests, json, subprocess
from datetime import datetime

WECHAT_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"

def check_mysql_connections():
    conn = pymysql.connect(host='127.0.0.1', port=3306,
                           user='root', password='xxx')
    cur = conn.cursor()
    cur.execute("SHOW PROCESSLIST")
    count = len(cur.fetchall())
    cur.execute("SHOW VARIABLES LIKE 'max_connections'")
    max_conn = int(cur.fetchone()[1])
    cur.close(); conn.close()
    return count, max_conn, count / max_conn * 100

def check_api_health():
    try:
        r = requests.get('http://localhost:5008/api/health', timeout=3)
        return r.status_code == 200, r.elapsed.total_seconds() * 1000
    except:
        return False, 9999

def check_api_success_rate():
    # 读取nginx/access.log统计（如果有）
    # 或读取Flask日志统计
    try:
        with open('logs/app.log') as f:
            lines = f.readlines()
        recent = [l for l in lines if '2026-06' in l][-1000:]
        errors = [l for l in recent if '500' in l or 'Error' in l]
        return 100 - len(errors) / len(recent) * 100 if recent else 100
    except:
        return 100.0

def send_wechat(message):
    data = {"msgtype": "text", "text": {"content": message}}
    requests.post(WECHAT_WEBHOOK, json=data)

def main():
    results = []
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 1. DB连接数
    cnt, mx, pct = check_mysql_connections()
    results.append(f"DB连接: {cnt}/{mx} ({pct:.1f}%)")
    if pct > 90:
        send_wechat(f"🔴 [P0] DB连接告警 {pct:.1f}% @ {ts}")

    # 2. API健康
    ok, latency = check_api_health()
    results.append(f"API健康: {'✅' if ok else '❌'} ({latency:.0f}ms)")
    if not ok:
        send_wechat(f"🔴 [P0] API不可用 @ {ts}")

    # 3. 错误率
    rate = check_api_success_rate()
    results.append(f"成功率: {rate:.2f}%")
    if rate < 99:
        send_wechat(f"🟠 [P1] 成功率 {rate:.2f}% @ {ts}")

    # 输出
    report = f"【监控报告 {ts}】\n" + "\n".join(results)
    print(report)
    send_wechat(report)

if __name__ == '__main__':
    main()
```

#### 方案B：Flask内置健康检查（增强）

在 `app.py` 增加 `/api/metrics` 端点，暴露关键指标：

```python
@app.route('/api/metrics')
def metrics():
    conn = g.storage.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SHOW PROCESSLIST")
        db_conn_count = len(cur.fetchall())
        cur.execute("SHOW VARIABLES LIKE 'max_connections'")
        max_conn = int(cur.fetchone()[1])
    finally:
        g.storage.release_connection(conn)

    return jsonify({
        'db_connections': db_conn_count,
        'db_max_connections': max_conn,
        'db_connection_pct': round(db_conn_count / max_conn * 100, 1),
        'timestamp': datetime.now().isoformat()
    })
```

### 4.3 监控脚本部署

```bash
# crontab -e
# 每天早上9点跑一次
0 9 * * * cd /path/to/mobile_api_ai && python scripts/monitor.py

# 灰度放量期间，每小时跑一次
0 * * * * cd /path/to/mobile_api_ai && python scripts/monitor.py
```

---

## 五、灰度Gate判断规则

> 每个放量节点（G1-G5），必须先查监控数据，满足阈值才能放量。

| Gate指标 | 允许放量条件 | 禁止放量条件 |
|---------|------------|-------------|
| API成功率 | ≥ 99.5% | < 99.5% |
| P99响应时间 | ≤ baseline+200ms | > baseline+200ms |
| DB连接数 | ≤ max 80% | > max 80% |
| 错误日志 | ≤ 1条/分钟 | > 1条/分钟 |
| 工厂反馈 | 无异常 | 有工人/老板投诉 |

**判断流程**：
```
G放量签字前
    ↓
开发跑 python scripts/monitor.py
    ↓
导出监控报告（截图留存）
    ↓
对比阈值表
    ↓
├─ 全部绿灯 → 4人签字 → 执行放量
└─ 任一红灯 → 禁止放量 → 优先修复 → 再测
```

---

## 六、告警通知模板

### 6.1 P0 紧急告警（企微）

```
🔴 [P0 紧急] {系统名} {告警指标}告警

时间: {YYYY-MM-DD HH:MM}
指标: {API成功率/P99/DB连接}
当前值: {实际值}
阈值: {告警阈值}
影响: {工人报工/老板查看/质检提交}
建议: {立即回滚/紧急修复}
负责人: {开发姓名} {电话}
```

### 6.2 P1 重要告警（企微）

```
🟠 [P1 重要] {系统名} {指标}提示

时间: {YYYY-MM-DD HH:MM}
指标: {P99响应时间}
当前值: {实际值}ms
阈值: {告警阈值}ms
趋势: {持续X分钟}
建议: {观察/准备回滚}
负责人: {开发姓名}
```

---

## 七、实施计划

| 时间 | 任务 | 产出 |
|------|------|------|
| Week 0 | 部署 monitor.py | 脚本可执行 |
| Week 0 | 配置企微告警群Webhook | 通知可达 |
| Week 1 | 建立baseline（正常状态数据） | baseline.json |
| Week 1 | 灰度放量前演练一次 | 报告模板 |
| G1放量前 | 所有Gate数据可查 | 签字材料 |
| G1-G5 | 每次放量前查监控 | 监控报告 |

---

## 八、触发机制（v3.7.1审计补充）

> ⚠️ **审计发现**：原文档写了crontab但未说明"谁来执行"和"结果给谁看"。
> 以下是明确的执行规范。

### 8.1 触发模式（明确三档）

| 场景 | 触发方式 | 执行人 | 结果给谁看 |
|------|---------|--------|---------|
| **平时（稳定运行）** | 每天 09:00 cron | 服务器自动 | 开发团队企微群 |
| **灰度放量期间（G1-G5）** | 每小时 cron | 服务器自动 | 开发+PM企微群 |
| **放量签字前** | 手动执行 `python scripts/monitor.py` | **开发负责人** | 4人签字材料 |
| **告警触发时** | 自动（脚本内判断阈值） | 服务器自动 | 企微P0/P1告警群 |

### 8.2 明确的执行清单

```
【Week 0 第4天，完成以下3项，才能算监控方案"已部署"】

☐ 1. scripts/monitor.py 存在且可执行
   $ cd mobile_api_ai && python scripts/monitor.py
   （输出监控报告，无报错）

☐ 2. 企微Webhook可发消息
   测试：向企微群发一条测试消息
   验证：群里能收到

☐ 3. crontab 已配置
   $ crontab -e
   （确认两条cron任务存在）
   0 9 * * * ... python scripts/monitor.py
   0 * * * * ... python scripts/monitor.py
```

### 8.3 监控报告模板

每次放量签字前，手动执行并截图留存：

```bash
$ python scripts/monitor.py

【监控报告 2026-WW-W 放量签字用】

DB连接: 45/200 (22.5%) ✅
API健康: ✅ (28ms)
成功率: 99.7% ✅
P99响应: 380ms ✅
错误日志: 0条/分钟 ✅
工人报工: 无异常 ✅
DB慢查询: 3/小时 ✅

结论: 全部绿灯 ✅ 可签字放量
执行人: ___  时间: ___
```

---

**维护人**: 开发团队
**最后更新**: 2026-06-28（v3.7.1审计修复：明确触发机制+执行清单）
**下次审查**: Week 0 第4天监控部署完成后
**Week 0 签字条件之一**: 上述3项全部完成
