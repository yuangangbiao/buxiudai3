# TODO - P0 修复

## 立即清理

- [x] 已删除临时探查脚本：_check_*.py / _tmp_*.py / _diag_*.py（保留 4 个验证/重启脚本）
- [ ] 清理 `_verify_final.py` / `_verify_p0_v2.py` / `_diag_storage.py` / `_restart_services.py` 临时验证脚本
- [ ] 清理 `logs/restart_5003.log` 和 `logs/restart_5008.log` 临时日志

## 数据清理（已完成 - 不需要清理）

- [x] **脏数据检查**: data_packages 86 条数据已完成审计（2026-06-18）
  - 3 条 > 1000：2 条是真实业务数据（编制左/右旋 29528, sub_steps 一致），1 条是 config 类型测试数据（ORD-F6-ATOMIC-001, data_type='config'）
  - 0 条真实脏数据需要清理
  - Bug #1+#2 修复后，新报工不会再导致 completed_qty 暴增

## 测试用例补充

- [ ] **Bug #14 验证**: 当前 expectedOrders=0 条无法证明修复，需等有 pending 订单时再跑一次 `_verify_final.py`
- [ ] **Bug #9 验证（待定）**: 重启 5008 用 nohup 捕获 stdout 日志，确认云端 ACK 是否真的重复拉取

## 后续轮次

- [ ] 第 2 轮 Bug 狩猎：并发 + 网络异常 + 跨日班次
- [ ] 第 3 轮 Bug 狩猎：数据一致性
- [ ] 第 4 轮 Bug 狩猎：UI/UX 适老化
- [ ] 修复 9 个 P1 + 4 个 P2 Bug

## 文档归档

- [ ] 把 `docs/P0修复_2026_06_18/` 下的 4 个文档（ALIGNMENT/DESIGN/TASK/ACCEPTANCE/BUSINESS_IMPACT）链接到 README.md
- [ ] 把 R1 报告（V1.1）和审计报告归档到 `docs/bug_hunt_2026_06_18/`
