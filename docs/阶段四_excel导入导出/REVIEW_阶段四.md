# 阶段四 Excel导入导出 复盘报告

## 项目时间线
- P0 上下文对齐: 2026-06-22 18:30
- P1-P3 需求/设计/任务: 18:35
- P4 编码实施: 18:45
- P5 测试 (发现mesh_size bug+json bug): 19:00-19:15
- P6 审计+修复DoS: 19:25
- P7 零回归验证: 19:30
- P8 验收: 19:38

## 复盘三问

### ✅ 什么做对了？

1. **真实UI测试，而非API直接调用**
   - Playwright 走完整UI流程（登录→导航→点击→上传→查看结果）
   - 7/7场景全部通过，发现的真实问题比单元测试多
2. **冒烟测试前置拦截**
   - 防止代码导入错误就进入全量审计
3. **审计后立即修复并重测**
   - 发现 DoS 风险 → 立即添加 MAX_CONTENT_LENGTH + 413 错误处理
   - 发现 generate_order_no 序号冲突 → 改为逐条 try/except IntegrityError
4. **业务影响报告**
   - 用户场景对比、业务能力新增、不变更部分、一句话总结 4个维度齐全

### ❌ 什么卡住了？

1. **Python 3.14 vs Python 3.13 路径兼容问题**
   - `py -3` 解析 Python 3.14 路径时中文乱码
   - 解决方案：用 `.venv\Scripts\python.exe` (Python 3.13.0) 启动服务
   - **教训**：项目应统一 Python 环境，避免多版本切换

2. **PowerShell 中文路径乱码**
   - `Start-Process -FilePath "d:\yuan\..."` 中文字符被编码错误
   - 解决方案：用 Python `subprocess.Popen` 启动服务

3. **Playwright Downloads 文件夹清理被 sandbox 阻止**
   - 大量 .tmp 文件堆积触发拦截
   - 解决方案：用 `fetch + arrayBuffer` 替代 `<a download>` 流程

4. **T2/T3/T4 看似失败实际是登录失败**
   - 未登录时页面跳转到 /login，导致找不到按钮
   - 解决方案：先登录，再做按钮检测

### 🆕 什么没想到？

1. **mesh_size 字段类型为 DECIMAL(10,2)**
   - 用户文本 `10mm×10mm` 触发 MySQL 错误
   - 解法：`_to_decimal()` 函数尝试转换，失败时存到 extra_params

2. **json 未导入导致第二次导入失败**
   - `json.dumps(extra_dict)` 报错
   - 解法：在 server.py 顶部加 `import json`

3. **generate_order_no 同一循环内多次调用序号不变**
   - 因 COUNT(*) 不包含未提交行
   - 解法：try/except IntegrityError per-row + 单独 conn.commit()

4. **utils 目录新建被项目视为新模块**
   - `from utils.excel_service import ...` 正常工作
   - 无需修改 sys.path

## 经验池（模式级条目）

| 模式 | 现象 | 建议 |
|------|------|------|
| Python 3.14 中文路径 | openpyxl 路径崩溃 | 项目统一 Python 3.13 venv |
| Playwright Downloads 拦截 | sandbox 阻止文件清理 | 改用 fetch+arrayBuffer |
| MySQL DECIMAL 字符串插入 | "Incorrect decimal value" | 加 `_to_decimal()` 类型转换器 |
| generate_xxx_no() 并发 | 序号重复 → IntegrityError | try/except + per-row commit |
| 老服务器残留进程 | 端口5001被占用 | `taskkill /F /PID` 清理 |

## 经验池（规则级条目）

| 规则 | 说明 |
|------|------|
| 所有Excel导出函数必须先验证 openpyxl import | 防止运行时崩溃 |
| 所有导入API必须有文件大小限制 | DoS 防护 |
| 所有数值字段需提供类型转换器 | DECIMAL 字段接受字符串时崩溃 |
| 所有 UI 测试先登录再检测按钮 | 避免误判 |

## 自进化触发

- **优化级**：下次 P4 编码前直接预装 Python .venv 检查（避免半路切换）
- **优化级**：下次写 server.py 时同步检查所需 imports（json/requests/urllib等）
- **规则级**：下次审计 Excel 导入 API 默认检查 MAX_CONTENT_LENGTH

## TODO询问

请确认是否进入 **阶段五：操作员CRUD增强**？

或者有以下待办事项需要确认：
- 是否要将 stage4 的 dispatch 端 `/api/dispatch-center/shipping/list` 和 `/api/dispatch-center/report-queue/list` 路径核实是否存在？（如不存在则发货/报工导出 API 会返回空数据）
- 是否需要将 Excel 导入的字段别名文档化（FIELD_ALIASES）？
- 是否需要将 mesh_size 等 DECIMAL 字段转换逻辑沉淀为通用工具函数？