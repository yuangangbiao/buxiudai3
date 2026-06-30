# MySQL 迁移兼容性 — 彻底解决方案

> 2026-05-30 | 不锈钢网带跟单系统 3.0

---

## 一、问题全景

```
MySQL 迁移遗留
├── 双文件并存 → 改错文件，修复不生效
├── 全局吞错 → 真实错误不可见
├── 单连接无心跳 → 超时即死 InterfaceError
├── SQLite/MySQL 占位符不兼容 (? vs %s)
├── datetime/str 混排 → sort 崩溃
├── 死信不可见 → 失败任务积压无人知
└── 缺集成测试 → 回归靠运气
```

---

## 二、根因链（以 /api/wechat/dispatch 为例）

```
MySQL wait_timeout=8h → 连接静默断开
  → mysql_storage.py: _ensure_conn 只检查 is None，不检查存活
    → fetch_one() 用死连接执行 → pymysql.err.InterfaceError(0, '')
      → Flask @errorhandler(Exception) 吞掉 → jsonify({'message': '服务器内部错误'})
        → WeChatReportService._send_task() 收到 code≠0 → 3次重试 → dead_letter
          → 用户看到: "任务179转入死信队列，请人工处理"
          → 实际错误: InterfaceError — 重连即可解决
```

**关键发现**: 项目有两个 MySQL 存储文件:
- `storage/mysql_storage.py` — 服务实际运行（330行，原来无防护）
- `storage_mysql.py` — 曾被误认为运行文件（539行，改了白改）

---

## 三、全部修复清单（11个文件）

### 3.1 存储层

| 文件 | 修复 | 说明 |
|------|------|------|
| `storage/mysql_storage.py` | 三层连接防护 | ping心跳 + InterfaceError恢复 + 巡检 |
| `storage_mysql.py` | → 15行别名 | 单向指向权威文件，消除双轨维护 |

**连接恢复代码**:
```python
# _ensure_conn — 每次使用前检查连接存活
def _ensure_conn(self):
    if self._pool is None:
        self.connect()
        return
    try:
        self._pool.ping(reconnect=True)
    except Exception:
        self.connect()

# fetch_one/fetch_all/execute — 操作中异常自动恢复
def fetch_one(self, sql, params=None):
    self._ensure_conn()
    try:
        with self._pool.cursor() as c:
            c.execute(sql, params)
            return c.fetchone()
    except (pymysql.err.InterfaceError, pymysql.err.OperationalError):
        self._reconnect_and_retry()
        with self._pool.cursor() as c:
            c.execute(sql, params)
            return c.fetchone()

def _reconnect_and_retry(self):
    """快速重连 — 断开旧连接，建立新连接"""
    self.disconnect()
    self.connect()
    if self._pool is None:
        raise pymysql.err.InterfaceError("MySQL 重连失败")
```

### 3.2 API 层

| 文件 | 修复 |
|------|------|
| `container_center_api.py` | 全局异常 → `str(e)`; `storage.update()` → `storage.execute()` |
| `dispatch_center.py` | 4处排序: `datetime`/`str` 混排 → `str()` 统一 |
| `standalone_dispatch_server.py` | 全局异常 → `str(e)` |
| `core/app.py` | 全局异常 → `str(e)` |

### 3.3 业务层

| 文件 | 修复 |
|------|------|
| `services/schedule_dispatch_service.py` | `get_dead_letters()` + `retry_dead_letter()` + 死信≥10告警 |
| `services/wechat_report_service.py` | `get_dead_tasks()` + `retry_dead_task()` + 死信≥10告警 |
| `models/inventory.py` | `search_by_material()` 兼容旧 API |

### 3.4 UI 层

| 文件 | 修复 |
|------|------|
| `desktop/views/production_view.py` | 🔄 重发死信按钮 + 列表弹窗 |
| `desktop/views/process_view.py` | 🔄 重发死信按钮 + 列表弹窗 |
| `desktop/views/material_prep_view.py` | 🔄 重发死信按钮 + 列表弹窗 |
| `desktop/views/material_rules_view.py` | MaterialRuleDialog 参数顺序修复 |

---

## 四、防护体系（4层）

| 层 | 位置 | 作用 |
|:--:|------|------|
| 1 | `_ensure_conn` | ping 心跳 — 每次调用前检查 |
| 2 | `fetch_one/fetch_all/execute` | InterfaceError 捕获 — 操作中断恢复 |
| 3 | `ConnectionMonitor` | 60秒定时巡检 — 主动发现断开 |
| 4 | `server_launcher.py` | MD5 变更检测 — 启动时提示需重启的文件 |

---

## 五、部署检查清单

每次修改代码后执行:

- [ ] **终止所有旧进程**: `taskkill /F /IM python.exe`
- [ ] 确认修改的是 `storage/mysql_storage.py`（不是根目录的 `storage_mysql.py`）
- [ ] 确认 `.pyc` 缓存已清除（`PYTHONDONTWRITEBYTECODE=1` 则跳过）
- [ ] 重启顺序: 容器中心 → 调度中心 → 桌面端
- [ ] 验证: `curl http://localhost:5002/health` 返回 `"status":"ok"`
- [ ] 验证: 发布测试任务 → 确认容器中心收到（无 `InterfaceError` 日志）
- [ ] 检查日志: `grep "连接已断开"` 应为空

---

## 六、预防规则

### 6.1 代码规则

1. **禁止维护两份独立副本** — 如必须别名，用单向 `from x import *` 且别名文件不超过 20 行
2. **所有 Flask 全局异常必须返回 `str(e)`**，不能吞掉真实错误
3. **所有 `sort(key=lambda x: x.get('date', ''))` 必须加 `str()`**:  
   `sort(key=lambda x: str(x.get('date') or ''))`
4. **新增存储方法先在 `storage/mysql_storage.py` 实现**，别名自动同步
5. **直接操作数据库用 `execute/update/insert`**，不要用 `_conn.cursor()` 绕过适配层

### 6.2 运维规则

- MySQL `wait_timeout` 建议 ≥ 28800（8小时）
- 每次 git pull 后运行 `server_launcher.py` 自动检测文件变更
- 死信 ≥ 10 条时日志会 WARNING，需及时处理

---

## 七、回滚方案

> ⚠️ 回滚会丢失本文档描述的全部修复。仅在容器中心/桌面端出现新故障且无法定位时使用。

```bash
# 全部回滚（假设文件在 git 中）
cd D:\yuan\不锈钢网带跟单3.0
git stash  # 先备份当前修改
git checkout -- mobile_api_ai/storage/mysql_storage.py
git checkout -- mobile_api_ai/storage_mysql.py
git checkout -- mobile_api_ai/container_center_api.py
git checkout -- mobile_api_ai/dispatch_center.py
git checkout -- mobile_api_ai/standalone_dispatch_server.py
git checkout -- core/app.py
git checkout -- services/schedule_dispatch_service.py
git checkout -- services/wechat_report_service.py
git checkout -- models/inventory.py
git checkout -- desktop/views/production_view.py
git checkout -- desktop/views/process_view.py
git checkout -- desktop/views/material_prep_view.py
git checkout -- desktop/views/material_rules_view.py
git checkout -- server_launcher.py

# 终止并重启
taskkill /F /IM python.exe
python server_launcher.py
```

**恢复本次修复**: `git stash pop`（会重新应用本文档的全部修改）

---

## 八、已知局限与风险

| 项 | 说明 | 等级 |
|---|------|:--:|
| ConnectionMonitor | 2026-05-30 新增，尚未经过长期运行验证 | ⚠️ 低 |
| `storage_layer.py` 排序 | ~20处 `sort(key=lambda x: x.get('created_at', ''))` — 该文件为 SQLite 专用，SQLite 返回字符串，**暂安全** | ✅ |
| 集成测试 | `tests/integration/test_schedule_publish.py` 为新文件，需 `pip install pytest` 后运行: `python -m pytest tests/integration/ -v` | ⚠️ 低 |
| 死信告警阈值 | 当前 ≥10 条触发 WARNING，可根据实际调整 | ⚠️ 低 |
| 文件变更检测 | 首次运行生成 `.hash` 文件（每关键文件一个），会残留在工作目录中 | ⚠️ 极低 |
