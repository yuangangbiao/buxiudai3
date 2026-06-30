# TODO - 阶段四 Excel导入导出 待办清单

## ✅ 已完成
- [x] Excel导出（替代CSV，含格式美化）
- [x] 批量选中导出（基于ids参数）
- [x] 订单查询页Excel导出
- [x] order_import.html 导入页面
- [x] POST /api/orders/import 批量导入
- [x] GET /api/orders/template 模板下载
- [x] 文件上传大小限制（10MB）
- [x] shared.js 导航集成

## ⚠️ 已知风险/未闭环

| # | 风险项 | 影响 | 处理建议 |
|---|--------|------|----------|
| 1 | dispatch端 `/api/dispatch-center/shipping/list` 路径是否真实存在 | LOW | 在阶段七辅助功能中验证，否则发货导出API可能返回空 |
| 2 | dispatch端 `/api/dispatch-center/report-queue/list` 路径是否真实存在 | LOW | 同上 |
| 3 | 并发批量导入未做事务性保护 | LOW | 当前逐条 try/except，3-5单可接受；1000+需要重构 |
| 4 | parse_order_import 模糊表头匹配可能误识别 | LOW | 字段别名设计避免常见歧义，极端情况需手动调整 |
| 5 | Excel 文件下载到Downloads目录被sandbox拦截 | MEDIUM | 临时绕过：fetch+arrayBuffer，但用户真实下载仍受sandbox限制 |
| 6 | Phase4生成的临时文件 `_tmp_*.{js,py,ps1}` 未清理 | LOW | 需要在Phase9执行 stale-file-detector |

## 🔄 待用户确认

| # | 事项 | 选项 |
|---|------|------|
| 1 | 下一步 | A) 阶段五：操作员CRUD增强  B) 阶段六：BOM+库存  C) 先清理临时文件 |
| 2 | 发货/报工Excel导出API是否需要联调 | A) 需要  B) 不需要 |

## 📋 操作指引

### 启动服务（如果已停止）
```powershell
py -3 d:\yuan\不锈钢网带跟单3.0\_tmp_start_servers.py
```

### 验证Excel导入导出
```powershell
# 浏览器访问
http://localhost:5001/login        # 用户名: 测试
http://localhost:5001/orders       # 订单页：导出全部按钮
http://localhost:5001/order-import # 导入页
```

### 重跑端到端测试
```powershell
py -3 d:\yuan\不锈钢网带跟单3.0\_tmp_kill_all.py
py -3 d:\yuan\不锈钢网带跟单3.0\_tmp_start_servers.py
node d:\yuan\不锈钢网带跟单3.0\_tmp_real_e2e.js
```

### 清理临时文件（Phase9 执行）
```powershell
Remove-Item d:\yuan\不锈钢网带跟单3.0\_tmp_*.* -Force
```

### 查看审计报告
```bash
cat d:/yuan/不锈钢网带跟单3.0/docs/阶段四_excel导入导出/ACCEPTANCE_阶段四.md
cat d:/yuan/不锈钢网带跟单3.0/docs/阶段四_excel导入导出/FINAL_阶段四.md
cat d:/yuan/不锈钢网带跟单3.0/docs/阶段四_excel导入导出/REVIEW_阶段四.md
```