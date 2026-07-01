# TASK-T8: 导入导出 + 通知 + 扫码 + 前端模板

## 输入契约

**前置依赖**：T1-T7
**输入数据**：DESIGN v2.0 模块 8/9/10
**环境依赖**：openpyxl（Python 库），html5-qrcode（前端 CDN）

## 输出契约

**输出数据**：
- **导入导出**：
  - `inventory_web/services/import_service.py` 实现 dry-run / commit / template
  - `inventory_web/routes_api.py` 新增 3 端点：template / dry-run / commit
  - 升级 `templates/inventory/export.html`
- **通知**：
  - `inventory_web/services/notification_service.py` 实现 create / list / mark_read
  - `inventory_web/routes_api.py` 新增 3 端点
  - `templates/inventory/notifications.html` 新建
  - `templates/inventory/base.html` 升级（铃铛+下拉）
- **扫码**：
  - `templates/inventory/scanner.html` 新建
  - html5-qrcode 本地化：`static/vendor/html5-qrcode.min.js`
- **前端模板升级**（15 个 html）：
  - base_data.html / stock_list.html / batch.html / dashboard.html / export.html / logs.html / settings.html / products.html
  - 新建 warehouses.html / stocktake.html / transfer.html / reports.html / notifications.html / scanner.html / recycle_bin.html

**验收标准**：
- [ ] xlsx 导入 1000 行 < 10s
- [ ] dry-run 不入库，commit 才入库
- [ ] 通知触发：入库后 < safety_stock 自动生成
- [ ] 扫码：无摄像头时降级手动输入
- [ ] 15 模板均支持二次确认（DELETE {count}）
- [ ] html5-qrcode 本地化（不依赖 CDN）

## 实现约束

- **技术栈**：
  - openpyxl（`pip install openpyxl`）
  - html5-qrcode（本地下：`static/vendor/`）
- **接口规范**：
  ```
  GET /inventory/api/import/template?entity=product → 下载 xlsx
  POST /inventory/api/import/dry-run (multipart file) → 返回错误列表
  POST /inventory/api/import/commit?token=xxx → 入库
  GET /inventory/api/notification/list?is_read=0
  POST /inventory/api/notification/<id>/read
  POST /inventory/api/notification/read-all
  ```
- **质量要求**：
  - dry-run 必须用事务，commit 失败要回滚
  - xlsx 限制文件大小（< 5MB）+ 行数（< 10000）
  - 通知已读状态独立字段
  - 扫码组件支持 PWA 摄像头权限失败降级

## 依赖关系

**后置任务**：无
**并行任务**：无（最后一批）
