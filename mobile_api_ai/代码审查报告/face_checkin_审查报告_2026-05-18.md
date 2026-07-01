# 代码审查报告：face_checkin 模块

**审查日期**: 2026-05-18
**审查范围**: `d:\yuan\不锈钢网带跟单3.0\mobile_api_ai\face_checkin/` 目录下全部文件及相关联文件
**涉及文件**:
- `face_checkin/__init__.py` (823行)
- `face_checkin/admin_html.py` (887行)
- `data/config.json`
- `app.py` (相关注册代码行 44-68)
- `blueprint_registry.py`

---

## 1. 数据库表结构分析

### 1.1 enrollments 表（`__init__.py` 行 162-168）

```sql
CREATE TABLE IF NOT EXISTS enrollments (
    name TEXT PRIMARY KEY,
    descriptor TEXT NOT NULL,
    created_at REAL NOT NULL
)
```

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| 主键为 name（无唯一ID） | MEDIUM | `__init__.py:163` | 以姓名作为主键，无法支持同名不同人。建议使用自增ID或UUID做主键，name作为普通字段 |
| 缺少微信用户ID字段 | MEDIUM | `__init__.py:162-168` | `_notify_checkin_success()` 行 480-488 需要从 `operators.json` 中查找微信UserID，应该直接存储在 enrollment 记录中 |
| 无 created_at 索引 | LOW | `__init__.py:162-168` | 如果人员量大会有排序查询性能问题 |

### 1.2 checkins 表（`__init__.py` 行 169-178）

```sql
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    similarity REAL,
    photo TEXT,
    photo_path TEXT,
    created_at REAL NOT NULL
)
```

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| **photo 字段存储完整 base64 数据** | **CRITICAL** | `__init__.py:174` | 每条签到记录包含完整 base64 照片(可能 100KB-500KB)，数据库文件会急剧膨胀。行 573 `INSERT INTO checkins ... photo` 接收前端传来的 base64 数据直接入库。签到量累积后数据库大小失控 |
| 缺少外键约束 | MEDIUM | `__init__.py:169-178` | checkins.name 不引用 enrollments.name，签到可以不经过注册直接写入 |
| 缺少照片文件清理跟踪 | MEDIUM | `__init__.py:175` | photo_path 记录的文件路径，当删除 enrollment 或 checkin 记录时，对应照片文件不会被清理 |
| 无 admin_users 表 | **CRITICAL** | 整体设计 | 管理员账号存储在 `config.json` 而非数据库中，存在并发写丢失、无审计日志、无法多实例共享的问题 |

### 1.3 migration 设计问题

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| migrate_db() 每次初始化都执行 | LOW | `__init__.py:183-188` | 每次 init_db() 后都执行 `PRAGMA table_info` 检查，虽然开销不大，但可考虑只执行一次并标记版本 |

---

## 2. 数据库连接管理

### 2.1 连接管理总评：良好但有隐患

`get_db()` 使用了 `@contextmanager` 模式（行 144-157），正确地管理了连接的获取、提交/回滚和关闭。

```python
@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| **模块级 init_db() 调用** | **HIGH** | `__init__.py:190` | `init_db()` 在模块加载时执行（行 190），如果数据库目录不可写或权限问题，整个 blueprint 注册会失败，导致 Flask 应用启动异常 |
| 无连接池 | MEDIUM | `__init__.py:144-157` | 每个请求都创建新 SQLite 连接，高频签到场景下有性能开销。SQLite 虽轻量但大量并发连接会竞争 WAL 锁 |
| busy_timeout 5秒可能不足 | MEDIUM | `__init__.py:149` | 在高并发写（如频繁签到 + 导出同时进行）时，5秒超时可能不够 |

---

## 3. 文件上传存储逻辑

### 3.1 路径遍历漏洞（CRITICAL）

**文件**: `__init__.py` 行 609-615

```python
@bp.route('/api/photos/<path:filename>')
def api_photo(filename):
    storage_dir = get_storage_dir()
    file_path = storage_dir / filename
    if not file_path.exists() or not file_path.is_file():
        return jsonify({'code': 404, 'message': '照片不存在'}), 404
    return Response(file_path.read_bytes(), mimetype='image/jpeg')
```

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| **路径遍历漏洞** | **CRITICAL** | `__init__.py:609-615` | `<path:filename>` 可以是 `../../etc/passwd`。`storage_dir / "../../etc/passwd"` 在 pathlib 中会被解析为存储目录之外的路径。虽然需要知道 token（前台页面有管理后台），但仍存在未经授权的路径遍历风险 |
| **整文件读入内存** | MEDIUM | `__init__.py:615` | `file_path.read_bytes()` 将完整文件读入内存，大图片时消耗内存。应使用 `send_file()` 或流式响应 |

### 3.2 照片上传逻辑

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| **返回路径不一致风险** | MEDIUM | `__init__.py:416-417` | 上传后返回的路径使用 `cfg.get("storage_path", "attendance")` 拼接，但实际存储路径已经由 `get_storage_dir()` 确定。如果刚上传后配置被修改，返回的 URL 路径与实际存储位置不一致 |
| 无文件类型校验 | MEDIUM | `__init__.py:396-417` | 没有校验解码后的数据是否为有效 JPEG/PNG 图片，可能被用来上传任意二进制文件 |
| **相对路径默认值安全隐患** | MEDIUM | `__init__.py:127` | 默认存储路径为 `attendance`（相对路径），如果配置被意外清空，照片会存到项目根目录下的 `attendance/` 目录而非预期的 `data/attendance/` |

### 3.3 文件存储路径管理

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| **绝对路径与相对路径混用** | MEDIUM | `__init__.py:124-137` | `get_storage_dir()` 中 `BASE_DIR / path`，如果 `config.json` 中 storage_path 为 `D:/photos`（绝对路径），Path 拼接行为取决于 Python 版本，可能导致存储位置异常 |
| 路径硬编码默认值 | LOW | `__init__.py:127,135` | `storage_path` 和 `export_path` 默认值硬编码为字符串，与规范要求不符 |

---

## 4. 静态文件服务

### 4.1 路由重复注册（CRITICAL）

**文件**: `__init__.py` 行 816-822 和 `app.py` 行 51-57

**face_checkin/__init__.py**:
```python
@bp.route('/models/<path:filename>')     # 实际路径: /face/models/<path>
def static_models(filename):
    return send_from_directory(STATIC_DIR / 'models', filename)

@bp.route('/wasm/<path:filename>')       # 实际路径: /face/wasm/<path>
def static_wasm(filename):
    return send_from_directory(STATIC_DIR / 'wasm', filename)
```

**app.py**:
```python
@app.route('/models/<path:filename>')    # 路径: /models/<path>
def face_models(filename):
    return send_from_directory(...)

@app.route('/wasm/<path:filename>')      # 路径: /wasm/<path>
def face_wasm(filename):
    return send_from_directory(...)
```

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| **功能重复、代码冗余** | HIGH | `__init__.py:816-822` + `app.py:51-57` | Blueprint 和 app 级别分别注册了模型的静态文件路由。Blueprint 下是 `/face/models/...`，app 下是 `/models/...`。前端实际引用路径不明确，容易导致 404。应当统一管理 |
| 前端页面路径依赖不清晰 | MEDIUM | `__init__.py:794-808` | SPA 页面在 `/face/app/` 下，但静态资源引用若使用绝对路径 `/models/...` 则走 app 路由，使用相对路径 `models/...` 则走 blueprint 路由。两种路由都可能工作，增加了调试复杂度 |

### 4.2 WASM 文件命名不一致

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| WASM 文件有两个版本 | LOW | `face_checkin_static/wasm/` | 存在 `tfjs-backend-wasm.wasm` 和 `tfjs-backend-wasm-threaded-simd.wasm`，但 models.json 中可能只引用其中一个，未被引用的文件浪费存储空间 |

---

## 5. 配置文件 config.json 结构和读取方式

### 5.1 文件内容（data/config.json）

```json
{
  "admin_password_hash": "aaffebecec560fec66e75f24062224ffa4e07696d2ae9a1fee3707c3f8fd9373",
  "admin_users": [
    {
      "username": "admin",
      "password_hash": "aaffebecec560fec66e75f24062224ffa4e07696d2ae9a1fee3707c3f8fd9373"
    }
  ]
}
```

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| **SHA256 无盐哈希密码** | **CRITICAL** | `config.json:2` + `__init__.py:42` | 使用 `hashlib.sha256(password.encode()).hexdigest()` 无盐哈希，易受彩虹表攻击。应使用 `hashlib.scrypt()` 或 `bcrypt` |
| **管理员凭证存储在明文 JSON** | **CRITICAL** | `config.json:2-8` | 密码哈希存储在 JSON 配置文件中，无加密。任何能读取 config.json 的进程都能获取密码哈希用于离线破解 |
| 配置无 schema 校验 | MEDIUM | `__init__.py:69-77` | `load_config()` 返回裸 dict，没有验证字段类型和格式。`export_schedule_day` 应为 1-31 的整数，`export_schedule_time` 应为合法时间格式 |
| 多线程写冲突风险 | MEDIUM | `__init__.py:69-83` | `_config_lock` 虽保护了并发写，但 `load_config()` + 修改 + `save_config()` 不是原子操作（见 `_get_admin_users()` 行 45-58），存在丢失写入的风险 |
| 文件锁范围过大 | LOW | `__init__.py:70,81` | 读操作也加全局互斥锁，高并发下成为瓶颈。可考虑使用读写锁 |

### 5.2 配置加载设计问题

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| admin_users 高频读写 JSON 文件 | **HIGH** | `__init__.py:55-58` | 每次增删管理员都写 JSON 文件。高频写操作导致文件 I/O 并发问题。建议使用 SQLite 存储用户数据 |
| 配置项无默认值收敛 | MEDIUM | `__init__.py:69-83, 124-137` | 多个地方分别读取 `cfg.get('storage_path', 'attendance')`，默认值分散在代码各处。应集中管理默认配置 |

---

## 6. 数据一致性问题

### 6.1 requests 库缺失导入（CRITICAL - 运行时会崩溃）

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| **缺少 import requests** | **CRITICAL** | `__init__.py:497,530` | `_notify_checkin_success()` 函数中使用了 `requests.post()`（行 497 和行 530），但文件顶部（行 1-19）没有 `import requests`。运行时触发考勤通知功能会引起 **NameError: name 'requests' is not defined**，导致考勤推送功能完全不可用 |

### 6.2 照片数据冗余与膨胀

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| **checkins.photo 存储完整 base64** | **CRITICAL** | `__init__.py:174, 572-575` | 每次签到将 base64 照片存入数据库字段，签到千人后数据库可达数百 MB。`photo_path` 已经保存了文件路径，`photo` 字段多余 |
| 照片文件不随记录删除 | MEDIUM | `__init__.py:443-444, 458` | 删除 enrollment 或 checkin 记录时，不删除对应的照片文件，造成磁盘空间泄漏 |

### 6.3 业务逻辑一致性问题

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| 签到无注册校验 | MEDIUM | `__init__.py:550-577` | `api_checkin()` 不验证 name 是否在 enrollments 中存在，任何名称都可签到 |
| 签到频率限制基于内存状态 | LOW | `__init__.py:565-569` | 1小时内重复签到限制依赖数据库查询，如果系统时间被修改会有异常行为 |
| **密码修改时旧密码允许为空** | MEDIUM | `__init__.py:270-271` | `if not old or not new` - 旧密码为空也能通过校验（行 277 才真正校验），这种"先检查为空再检查旧密码"的逻辑可能绕过错传非空校验 |
| 导出功能不含图片 | LOW | `__init__.py:638-666` | CSV 导出只包含文本数据，不含照片。但管理后台展示照片，存在数据导出不完整的问题 |

### 6.4 编码与兼容性问题

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| 编码声明缺失 | LOW | `__init__.py:1` | `admin_html.py` 有 `# -*- coding: utf-8 -*-`，但 `__init__.py` 没有。虽然 Python 3 默认 UTF-8，但一致性不佳 |

---

## 7. 其他发现

### 7.1 安全相关问题

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| admin_token 存储在 sessionStorage | MEDIUM | `admin_html.py:328` | 管理后台 token 存储在浏览器 sessionStorage，退出登录后不清除可能导致残留。但整体风险可控 |
| token 生成使用 secrets 模块 | GOOD | `__init__.py:94` | 使用了 `secrets.token_hex(32)`，密码学安全的 token 生成 |
| 登录失败未限制尝试次数 | MEDIUM | `__init__.py:228-251` | 无登录失败次数限制，可暴力破解管理员密码 |
| 无 CORS 保护 | MEDIUM | 全局 | 未配置 CORS，如果在浏览器环境跨域调用 API 可能存在问题 |

### 7.2 编码规范问题

| 问题 | 严重程度 | 位置 | 说明 |
|------|---------|------|------|
| `except Exception` 缺少类型细化 | LOW | 多处 | 多处通用异常捕获（如行 369, 392, 412 等）未区分异常类型 |
| 未使用 isort 排序导入 | LOW | `__init__.py:1-19` | import 顺序可优化 |

---

## 修复优先级清单

### P0 - 必须立即修复（生产隐患）

| # | 问题 | 文件 | 行号 |
|---|------|------|------|
| 1 | **缺少 import requests** - `_notify_checkin_success()` 运行时崩溃 | `__init__.py` | 行 4（需加 import） |
| 2 | **路径遍历漏洞** - `/api/photos/<path:filename>` 可访问任意文件 | `__init__.py` | 行 609-615 |
| 3 | **checkins.photo 大字段** - base64 照片直接入库导致数据库膨胀 | `__init__.py` | 行 174, 572-575 |

### P1 - 高优先级

| # | 问题 | 文件 | 行号 |
|---|------|------|------|
| 4 | **SHA256 无盐密码哈希** - 应升级为 scrypt 或 bcrypt | `__init__.py` | 行 42 |
| 5 | **admin_users 存在 config.json 中** - 应迁移到 SQLite | `__init__.py` | 行 45-58 |
| 6 | **静态文件路由重复** - Blueprint 和 App 两层注册 | `__init__.py:816-822` + `app.py:51-57` | 两处 |
| 7 | **模块级 init_db() 调用** - 启动时可能阻塞 | `__init__.py` | 行 190 |

### P2 - 中等优先级

| # | 问题 | 文件 | 行号 |
|---|------|------|------|
| 8 | 照片上传无文件类型校验 | `__init__.py` | 行 396-417 |
| 9 | 删除记录不清理照片文件 | `__init__.py` | 行 443-444, 458 |
| 10 | 登录无失败次数限制 | `__init__.py` | 行 228-251 |
| 11 | 返回路径依赖配置不一致 | `__init__.py` | 行 416-417 |
| 12 | 配置无 schema 校验 | `__init__.py` | 行 69-77 |

### P3 - 建议改进

| # | 问题 | 文件 | 行号 |
|---|------|------|------|
| 13 | 整文件读入内存应用 `send_file()` | `__init__.py` | 行 615 |
| 14 | 默认配置值分散多处，应集中管理 | `__init__.py` | 多处 |
| 15 | enrollment 应加微信 userid 字段 | `__init__.py` | 行 162-168 |

---

## 问题文件清单

| 文件 | 问题数 | P0 | P1 | P2 | P3 |
|------|--------|----|----|----|----|
| `face_checkin/__init__.py` | 25 | 3 | 4 | 5 | 3 |
| `data/config.json` | 6 | 2 | 1 | 1 | 0 |
| `app.py` (行 44-68) | 1 | 0 | 1 | 0 | 0 |
| `admin_html.py` | 1 | 0 | 0 | 1 | 0 |
| **合计** | **33** | **5** | **6** | **7** | **3** |

---

**审查结论**:
模块整体架构合理，`get_db()` 连接管理方式正确，CRUD API 设计规范。但存在 3 个 CRITICAL 级问题：**requests 库缺失导入会导致考勤推送功能运行时崩溃**、**照片 API 的路径遍历漏洞**、**base64 照片直接入库导致数据库空间暴涨**。建议优先修复 P0 问题后上线。另外管理员凭证存储在 JSON 文件中且使用无盐 SHA256 的问题虽然短期内风险可控，但建议中期规划迁移到 SQLite 统一管理。
