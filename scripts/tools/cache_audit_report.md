# 缓存覆盖审计报告

- 生成时间: 2026-06-21 13:50
- 总接口数: **500**
- 已用缓存: **4** (0%)
- 可缓存但未缓存: **100**

## 高优先级: 可缓存但未缓存的接口

| 文件 | 行号 | 方法 | 路径 |
|------|------|------|------|
| mobile_api_ai/api/cost.py | 16 | GET | `/orders'` |
| mobile_api_ai/api/cost.py | 33 | GET | `/orders/<order_no>'` |
| mobile_api_ai/api/cost.py | 66 | GET | `/detail/<order_no>'` |
| mobile_api_ai/api/cost.py | 100 | GET | `/summary'` |
| mobile_api_ai/api/cost.py | 107 | GET | `/material-prices'` |
| mobile_api_ai/api/health.py | 10 | GET | `/health'` |
| mobile_api_ai/api/message.py | 15 | GET | `/list'` |
| mobile_api_ai/api/metrics_api.py | 26 | GET | `/health'` |
| mobile_api_ai/api/quality.py | 22 | GET | `/list'` |
| mobile_api_ai/api/quality_inspection.py | 108 | GET | `/tasks'` |
| mobile_api_ai/api/quality_inspection.py | 149 | GET | `/tasks/<order_no>'` |
| mobile_api_ai/api/reports.py | 234 | GET | `/scheduler/status'` |
| mobile_api_ai/api/stats.py | 56 | GET | `/order-stats'` |
| mobile_api_ai/api/swagger.py | 421 | GET | `/summary` |
| mobile_api_ai/app.py | 193 | GET | `/api/orders/full-status/<order_no>'` |
| mobile_api_ai/app.py | 253 | GET | `/api/orders/full-status-list'` |
| mobile_api_ai/app.py | 302 | GET | `/api/all-process-tasks'` |
| mobile_api_ai/app.py | 515 | GET | `/api/process-tasks/by-order/<order_no>'` |
| mobile_api_ai/app.py | 761 | GET | `/api/process_sub_step/history'` |
| mobile_api_ai/app.py | 774 | GET | `/api/report_record/list'` |
| mobile_api_ai/app.py | 1012 | GET | `/api/quality_record/list'` |
| mobile_api_ai/app.py | 1256 | GET | `/api/material_record/list'` |
| mobile_api_ai/app.py | 1439 | GET | `/api/material_record/history_full'` |
| mobile_api_ai/app.py | 1466 | GET | `/api/outsource_record/list'` |
| mobile_api_ai/app.py | 1587 | GET | `/api/repair_record/list'` |
| mobile_api_ai/app.py | 1712 | GET | `/api/schedule_record/list'` |
| mobile_api_ai/app.py | 1862 | GET | `/health` |
| mobile_api_ai/app.py | 1961 | GET | `/api/tasks'` |
| mobile_api_ai/app.py | 2084 | GET | `/api/material/requirements'` |
| mobile_api_ai/app.py | 2134 | GET | `/api/material/<pkg_id>'` |
| mobile_api_ai/app.py | 2382 | GET | `/api/sync-queue/list'` |
| mobile_api_ai/cloud_relay.py | 194 | GET | `/api/queue/status'` |
| mobile_api_ai/cloud_relay.py | 314 | GET | `/api/health` |
| mobile_api_ai/cloud_router_service.py | 271 | GET | `/api/health'` |
| mobile_api_ai/container_api_server.py | 93 | GET | `/health` |
| mobile_api_ai/container_api_server.py | 97 | GET | `/api/health` |
| mobile_api_ai/container_api_server.py | 107 | GET | `/api/status` |
| mobile_api_ai/container_api_server.py | 175 | GET | `/api/tasks'` |
| mobile_api_ai/container_api_server.py | 236 | GET | `/api/tasks/<task_id>'` |
| mobile_api_ai/container_api_server.py | 369 | GET | `/api/pool/status'` |
| mobile_api_ai/container_api_server.py | 381 | GET | `/api/operators'` |
| mobile_api_ai/container_center_api.py | 953 | GET | `/api/process_sub_steps/<order_no>/<process_code>'` |
| mobile_api_ai/container_center_api.py | 1155 | GET | `/health` |
| mobile_api_ai/container_center_api.py | 1229 | GET | `/api/health` |
| mobile_api_ai/container_center_api.py | 1240 | GET | `/api/status` |
| mobile_api_ai/container_center_api.py | 1254 | GET | `/api/operators'` |
| mobile_api_ai/container_center_api.py | 1322 | GET | `/api/v4/operators'` |
| mobile_api_ai/container_center_api.py | 1381 | GET | `/api/process_names'` |
| mobile_api_ai/container_center_api.py | 1399 | GET | `/api/process_departments'` |
| mobile_api_ai/container_center_api.py | 2132 | GET | `/api/pool/status'` |
| mobile_api_ai/container_center_api.py | 2138 | GET | `/api/processes'` |
| mobile_api_ai/container_center_api.py | 2150 | GET | `/api/processes/<record_id>'` |
| mobile_api_ai/container_center_api.py | 2280 | GET | `/api/processes/by-order/<order_no>'` |
| mobile_api_ai/container_center_api.py | 2297 | GET | `/api/orders/full-status/<order_no>'` |
| mobile_api_ai/container_center_api.py | 2473 | GET | `/api/orders/full-status-list'` |
| mobile_api_ai/container_center_api.py | 2732 | GET | `/api/tasks'` |
| mobile_api_ai/container_center_api.py | 2789 | GET | `/api/tasks/<task_id>'` |
| mobile_api_ai/container_center_api.py | 2810 | GET | `/api/tasks/unacknowledged'` |
| mobile_api_ai/container_center_api.py | 3054 | GET | `/api/internal/config/versions/<config_name>'` |
| mobile_api_ai/container_center_api.py | 3296 | GET | `/api/outsource/config'` |
| mobile_api_ai/container_center_api.py | 3515 | GET | `/api/process_sub_steps/<order_no>'` |
| mobile_api_ai/container_center_api.py | 3527 | GET | `/api/process_sub_step_summary/<order_no>'` |
| mobile_api_ai/container_center_api.py | 3731 | GET | `/api/process_sub_step/summary_by_order/<order_no>'` |
| mobile_api_ai/container_center_api.py | 4068 | GET | `/api/material/list'` |
| mobile_api_ai/container_center_api.py | 4186 | GET | `/api/material/<pkg_id>'` |
| mobile_api_ai/deploy_output/wechat_cloud.py | 469 | GET | `/api/queue/status'` |
| mobile_api_ai/deploy_output/wechat_cloud.py | 717 | GET | `/api/backup/status'` |
| mobile_api_ai/deploy_output/wechat_cloud.py | 1049 | GET | `/health'` |
| mobile_api_ai/face_checkin/__init__.py | 216 | GET,PUT | `/api/config'` |
| mobile_api_ai/inventory_api_server.py | 379 | GET | `/api/health'` |
| mobile_api_ai/inventory_web/routes_api.py | 131 | GET | `/inventory/api/notification/list'` |
| mobile_api_ai/inventory_web/routes_api.py | 191 | GET | `/inventory/api/import/template'` |
| mobile_api_ai/inventory_web/routes_core.py | 184 | GET | `/inventory/api/stock/list'` |
| mobile_api_ai/inventory_web/routes_core.py | 1011 | GET | `/inventory/api/stocktake/list'` |
| mobile_api_ai/inventory_web/routes_core.py | 1087 | GET | `/inventory/api/transfer/list'` |
| mobile_api_ai/inventory_web/routes_data.py | 133 | GET | `/inventory/api/product/list'` |
| mobile_api_ai/inventory_web/routes_data.py | 466 | GET | `/inventory/api/recycle-bin/list'` |
| mobile_api_ai/scripts/cloud/cloud_group_bot_service.py | 115 | GET | `/api/health'` |
| mobile_api_ai/standalone_dispatch_server.py | 208 | GET | `/api/sync-queue/list'` |
| mobile_api_ai/standalone_dispatch_server.py | 313 | GET | `/health` |
| mobile_api_ai/standalone_dispatch_server.py | 340 | GET | `/api/report_record/list'` |
| mobile_api_ai/standalone_dispatch_server.py | 579 | GET | `/api/outsource_record/list'` |
| mobile_api_ai/standalone_dispatch_server.py | 731 | GET | `/api/quality_record/list'` |
| mobile_api_ai/standalone_dispatch_server.py | 772 | GET | `/api/material_record/list'` |
| mobile_api_ai/standalone_dispatch_server.py | 851 | GET | `/status'` |
| mobile_api_ai/sync_bridge_server.py | 81 | GET | `/health` |
| mobile_api_ai/sync_bridge_server.py | 99 | GET | `/api/health` |
| mobile_api_ai/wechat_cloud.py | 469 | GET | `/api/queue/status'` |
| mobile_api_ai/wechat_cloud.py | 717 | GET | `/api/backup/status'` |
| mobile_api_ai/wechat_cloud.py | 1049 | GET | `/health'` |
| mobile_api_ai/wechat_server.py | 1055 | GET | `/api/sync/status'` |
| mobile_api_ai/wechat_server.py | 1066 | GET | `/api/sync/health/detailed'` |
| mobile_api_ai/wechat_server.py | 1261 | GET | `/api/sync/circuit/status'` |
| mobile_api_ai/wechat_server.py | 1321 | GET | `/api/sync/queue/status'` |
| mobile_api_ai/wechat_server.py | 1385 | GET | `/api/sync/tasks'` |
| mobile_api_ai/wechat_server.py | 1421 | GET | `/api/sync/tasks/<task_id>'` |
| mobile_api_ai/wechat_server.py | 1438 | GET | `/api/sync/task/<order_no>/status'` |
| mobile_api_ai/wechat_server.py | 2348 | GET | `/health` |
| mobile_api_ai/wechat_server.py | 2376 | GET | `/api/cloud/status` |
| mobile_api_ai/wechat_server.py | 2578 | GET | `/api/wechat/status` |

## 所有接口详情

| 文件 | 行号 | 方法 | 路径 | 已用缓存 |
|------|------|------|------|---------|
| mobile_api_ai/api/ai.py | 112 | POST | `/speech-to-report'` | - |
| mobile_api_ai/api/ai.py | 150 | POST | `/image-analysis'` | - |
| mobile_api_ai/api/ai.py | 167 | POST | `/chat'` | - |
| mobile_api_ai/api/ai.py | 240 | GET | `/chat/history'` | - |
| mobile_api_ai/api/approval.py | 15 | GET | `/pending'` | - |
| mobile_api_ai/api/approval.py | 24 | POST | `/<int:approval_id>/approve'` | - |
| mobile_api_ai/api/approval.py | 33 | POST | `/<int:approval_id>/reject'` | - |
| mobile_api_ai/api/approval.py | 48 | GET | `/history'` | - |
| mobile_api_ai/api/auth.py | 99 | POST | `/login'` | - |
| mobile_api_ai/api/auth.py | 142 | GET | `/verify'` | - |
| mobile_api_ai/api/auth.py | 158 | GET | `/info'` | - |
| mobile_api_ai/api/cost.py | 16 | GET | `/orders'` | - |
| mobile_api_ai/api/cost.py | 33 | GET | `/orders/<order_no>'` | - |
| mobile_api_ai/api/cost.py | 42 | POST | `/orders/<order_no>/calculate'` | - |
| mobile_api_ai/api/cost.py | 56 | PUT | `/orders/<order_no>/revenue'` | - |
| mobile_api_ai/api/cost.py | 66 | GET | `/detail/<order_no>'` | - |
| mobile_api_ai/api/cost.py | 73 | POST | `/detail'` | - |
| mobile_api_ai/api/cost.py | 92 | DELETE | `/detail/<int:detail_id>'` | - |
| mobile_api_ai/api/cost.py | 100 | GET | `/summary'` | - |
| mobile_api_ai/api/cost.py | 107 | GET | `/material-prices'` | - |
| mobile_api_ai/api/cost.py | 114 | POST | `/material-prices'` | - |
| mobile_api_ai/api/cost.py | 136 | GET | `/labor-prices'` | - |
| mobile_api_ai/api/cost.py | 143 | POST | `/labor-prices'` | - |
| mobile_api_ai/api/decorators.py | 33 | POST | `/submit'` | - |
| mobile_api_ai/api/decorators.py | 70 | POST | `/update'` | - |
| mobile_api_ai/api/decorators.py | 96 | GET | `/protected'` | - |
| mobile_api_ai/api/decorators.py | 128 | POST | `/send'` | - |
| mobile_api_ai/api/health.py | 10 | GET | `/health'` | - |
| mobile_api_ai/api/legacy_routes.py | 119 | GET | `/api/dashboard'` | - |
| mobile_api_ai/api/legacy_routes.py | 261 | GET,POST | `/api/scan-info'` | - |
| mobile_api_ai/api/legacy_routes.py | 552 | POST | `/api/quality'` | - |
| mobile_api_ai/api/legacy_routes.py | 586 | GET | `/api/quality'` | - |
| mobile_api_ai/api/legacy_routes.py | 649 | GET | `/api/sub_step_records'` | - |
| mobile_api_ai/api/legacy_routes.py | 713 | GET | `/api/production-orders'` | - |
| mobile_api_ai/api/legacy_routes.py | 803 | GET | `/api/workers'` | - |
| mobile_api_ai/api/legacy_routes.py | 840 | GET | `/api/attendance/<username>'` | - |
| mobile_api_ai/api/legacy_routes.py | 863 | GET | `/api/attendance'` | - |
| mobile_api_ai/api/legacy_routes.py | 883 | POST | `/api/attendance'` | - |
| mobile_api_ai/api/legacy_routes.py | 920 | POST | `/api/login'` | - |
| mobile_api_ai/api/message.py | 15 | GET | `/list'` | - |
| mobile_api_ai/api/message.py | 29 | GET | `/unread-count'` | - |
| mobile_api_ai/api/message.py | 35 | POST | `/<int:msg_id>/read'` | - |
| mobile_api_ai/api/metrics_api.py | 12 | GET | `/stats'` | - |
| mobile_api_ai/api/metrics_api.py | 19 | POST | `/reset'` | - |
| mobile_api_ai/api/metrics_api.py | 26 | GET | `/health'` | - |
| mobile_api_ai/api/process.py | 22 | GET | `/my-tasks'` | - |
| mobile_api_ai/api/quality.py | 22 | GET | `/list'` | - |
| mobile_api_ai/api/quality.py | 41 | POST | `/<int:order_id>/create'` | - |
| mobile_api_ai/api/quality.py | 101 | GET | `/types'` | - |
| mobile_api_ai/api/quality_inspection.py | 108 | GET | `/tasks'` | - |
| mobile_api_ai/api/quality_inspection.py | 149 | GET | `/tasks/<order_no>'` | - |
| mobile_api_ai/api/quality_inspection.py | 246 | POST | `/evaluate'` | - |
| mobile_api_ai/api/quality_inspection.py | 259 | POST | `/submit'` | - |
| mobile_api_ai/api/quality_inspection.py | 335 | POST | `/review'` | - |
| mobile_api_ai/api/quality_inspection.py | 403 | POST | `/rework'` | - |
| mobile_api_ai/api/quality_inspection.py | 447 | GET | `/versions/<order_no>'` | - |
| mobile_api_ai/api/quality_inspection.py | 473 | POST | `/photos/upload'` | - |
| mobile_api_ai/api/quality_inspection.py | 505 | GET | `/history'` | - |
| mobile_api_ai/api/quality_inspection.py | 542 | GET | `/types'` | - |
| mobile_api_ai/api/reports.py | 13 | GET | `/page` | - |
| mobile_api_ai/api/reports.py | 25 | GET | `/definitions'` | - |
| mobile_api_ai/api/reports.py | 34 | GET | `/definitions/<report_id>'` | - |
| mobile_api_ai/api/reports.py | 44 | POST | `/definitions'` | - |
| mobile_api_ai/api/reports.py | 57 | PUT | `/definitions/<report_id>'` | - |
| mobile_api_ai/api/reports.py | 74 | DELETE | `/definitions/<report_id>'` | - |
| mobile_api_ai/api/reports.py | 84 | GET,POST | `/definitions/<report_id>/execute'` | - |
| mobile_api_ai/api/reports.py | 101 | GET | `/profiles'` | - |
| mobile_api_ai/api/reports.py | 109 | GET | `/profiles/<profile_id>'` | - |
| mobile_api_ai/api/reports.py | 119 | POST | `/profiles'` | - |
| mobile_api_ai/api/reports.py | 132 | PUT | `/profiles/<profile_id>'` | - |
| mobile_api_ai/api/reports.py | 149 | DELETE | `/profiles/<profile_id>'` | - |
| mobile_api_ai/api/reports.py | 161 | GET | `/schedules'` | - |
| mobile_api_ai/api/reports.py | 170 | GET | `/schedules/<schedule_id>'` | - |
| mobile_api_ai/api/reports.py | 180 | POST | `/schedules'` | - |
| mobile_api_ai/api/reports.py | 193 | PUT | `/schedules/<schedule_id>'` | - |
| mobile_api_ai/api/reports.py | 210 | DELETE | `/schedules/<schedule_id>'` | - |
| mobile_api_ai/api/reports.py | 222 | GET | `/outputs'` | - |
| mobile_api_ai/api/reports.py | 234 | GET | `/scheduler/status'` | - |
| mobile_api_ai/api/reports.py | 243 | POST | `/scheduler/start'` | - |
| mobile_api_ai/api/reports.py | 252 | POST | `/scheduler/stop'` | - |
| mobile_api_ai/api/scan.py | 147 | GET | `/workorder/<order_no>'` | - |
| mobile_api_ai/api/scan.py | 172 | POST | `/task'` | - |
| mobile_api_ai/api/scan.py | 219 | GET | `/worker/<worker_id>'` | - |
| mobile_api_ai/api/scan.py | 245 | POST | `/test/create-sample'` | - |
| mobile_api_ai/api/stats.py | 16 | GET | `/dashboard'` | - |
| mobile_api_ai/api/stats.py | 24 | GET | `/production'` | - |
| mobile_api_ai/api/stats.py | 32 | GET | `/cost'` | - |
| mobile_api_ai/api/stats.py | 40 | GET | `/worker'` | - |
| mobile_api_ai/api/stats.py | 48 | GET | `/worker-stats'` | - |
| mobile_api_ai/api/stats.py | 56 | GET | `/order-stats'` | - |
| mobile_api_ai/api/stats.py | 78 | GET | `/report/<report_id>'` | - |
| mobile_api_ai/api/stats.py | 89 | GET | `/report/<report_id>/export'` | - |
| mobile_api_ai/api/swagger.py | 409 | GET | `/` | - |
| mobile_api_ai/api/swagger.py | 415 | GET | `/openapi.json` | - |
| mobile_api_ai/api/swagger.py | 421 | GET | `/summary` | - |
| mobile_api_ai/api_validators.py | 14 | POST | `/api/order/create'` | import cache |
| mobile_api_ai/app.py | 104 | GET | `/favicon.ico` | - |
| mobile_api_ai/app.py | 109 | GET | `/mobile_login.html` | - |
| mobile_api_ai/app.py | 113 | POST | `/api/login'` | - |
| mobile_api_ai/app.py | 193 | GET | `/api/orders/full-status/<order_no>'` | - |
| mobile_api_ai/app.py | 253 | GET | `/api/orders/full-status-list'` | - |
| mobile_api_ai/app.py | 302 | GET | `/api/all-process-tasks'` | - |
| mobile_api_ai/app.py | 515 | GET | `/api/process-tasks/by-order/<order_no>'` | - |
| mobile_api_ai/app.py | 545 | POST | `/api/process_sub_step'` | - |
| mobile_api_ai/app.py | 698 | POST | `/api/process_sub_step/withdraw'` | - |
| mobile_api_ai/app.py | 761 | GET | `/api/process_sub_step/history'` | - |
| mobile_api_ai/app.py | 774 | GET | `/api/report_record/list'` | - |
| mobile_api_ai/app.py | 817 | POST | `/api/report_record/update'` | - |
| mobile_api_ai/app.py | 918 | POST | `/api/report_record/withdraw'` | - |
| mobile_api_ai/app.py | 985 | GET | `/api/report_record/history_full'` | - |
| mobile_api_ai/app.py | 1012 | GET | `/api/quality_record/list'` | - |
| mobile_api_ai/app.py | 1063 | POST | `/api/quality_record/update'` | - |
| mobile_api_ai/app.py | 1149 | POST | `/api/quality_record/withdraw'` | - |
| mobile_api_ai/app.py | 1228 | GET | `/api/quality_record/history_full'` | - |
| mobile_api_ai/app.py | 1256 | GET | `/api/material_record/list'` | - |
| mobile_api_ai/app.py | 1306 | POST | `/api/material_record/update'` | - |
| mobile_api_ai/app.py | 1389 | POST | `/api/material_record/withdraw'` | - |
| mobile_api_ai/app.py | 1439 | GET | `/api/material_record/history_full'` | - |
| mobile_api_ai/app.py | 1466 | GET | `/api/outsource_record/list'` | - |
| mobile_api_ai/app.py | 1506 | POST | `/api/outsource_record/update'` | - |
| mobile_api_ai/app.py | 1547 | POST | `/api/outsource_record/withdraw'` | - |
| mobile_api_ai/app.py | 1565 | GET | `/api/outsource_record/history_full'` | - |
| mobile_api_ai/app.py | 1587 | GET | `/api/repair_record/list'` | - |
| mobile_api_ai/app.py | 1625 | POST | `/api/repair_record/create'` | - |
| mobile_api_ai/app.py | 1655 | POST | `/api/repair_record/update'` | - |
| mobile_api_ai/app.py | 1693 | POST | `/api/repair_record/withdraw'` | - |
| mobile_api_ai/app.py | 1712 | GET | `/api/schedule_record/list'` | - |
| mobile_api_ai/app.py | 1752 | POST | `/api/schedule_record/update'` | - |
| mobile_api_ai/app.py | 1792 | POST | `/api/schedule_record/withdraw'` | - |
| mobile_api_ai/app.py | 1810 | GET | `/api/schedule_record/history_full'` | - |
| mobile_api_ai/app.py | 1862 | GET | `/health` | - |
| mobile_api_ai/app.py | 1961 | GET | `/api/tasks'` | - |
| mobile_api_ai/app.py | 2010 | POST | `/api/material/confirm'` | - |
| mobile_api_ai/app.py | 2050 | POST | `/api/material/arrived'` | - |
| mobile_api_ai/app.py | 2067 | POST | `/api/material/delivered'` | - |
| mobile_api_ai/app.py | 2084 | GET | `/api/material/requirements'` | - |
| mobile_api_ai/app.py | 2134 | GET | `/api/material/<pkg_id>'` | - |
| mobile_api_ai/app.py | 2161 | POST | `/api/material/return'` | - |
| mobile_api_ai/app.py | 2198 | POST | `/api/material/replenish'` | - |
| mobile_api_ai/app.py | 2238 | GET | `/api/warehousing/pending'` | - |
| mobile_api_ai/app.py | 2250 | POST | `/api/warehousing/confirm'` | - |
| mobile_api_ai/app.py | 2270 | GET | `/` | - |
| mobile_api_ai/app.py | 2275 | GET | `/scanner` | - |
| mobile_api_ai/app.py | 2280 | POST | `/api/wechat/pool/report'` | - |
| mobile_api_ai/app.py | 2382 | GET | `/api/sync-queue/list'` | - |
| mobile_api_ai/app.py | 2417 | POST | `/api/sync-queue/retry'` | - |
| mobile_api_ai/cloud_relay.py | 111 | GET | `/api/wechat/hook'` | - |
| mobile_api_ai/cloud_relay.py | 136 | POST | `/api/wechat/hook'` | - |
| mobile_api_ai/cloud_relay.py | 157 | GET | `/api/queue/poll'` | - |
| mobile_api_ai/cloud_relay.py | 174 | POST | `/api/queue/ack'` | - |
| mobile_api_ai/cloud_relay.py | 194 | GET | `/api/queue/status'` | - |
| mobile_api_ai/cloud_relay.py | 205 | POST | `/api/wechat/send'` | - |
| mobile_api_ai/cloud_relay.py | 240 | POST | `/api/stats/push'` | - |
| mobile_api_ai/cloud_relay.py | 314 | GET | `/api/health` | - |
| mobile_api_ai/cloud_router_service.py | 216 | POST | `/api/wechat/send'` | - |
| mobile_api_ai/cloud_router_service.py | 239 | POST | `/api/send'` | - |
| mobile_api_ai/cloud_router_service.py | 271 | GET | `/api/health'` | - |
| mobile_api_ai/container_api_server.py | 93 | GET | `/health` | - |
| mobile_api_ai/container_api_server.py | 97 | GET | `/api/health` | - |
| mobile_api_ai/container_api_server.py | 107 | GET | `/api/status` | - |
| mobile_api_ai/container_api_server.py | 120 | GET | `/api/version` | - |
| mobile_api_ai/container_api_server.py | 130 | GET | `/` | - |
| mobile_api_ai/container_api_server.py | 138 | POST | `/api/auth/login'` | - |
| mobile_api_ai/container_api_server.py | 168 | GET | `/api/auth/verify'` | - |
| mobile_api_ai/container_api_server.py | 175 | GET | `/api/tasks'` | - |
| mobile_api_ai/container_api_server.py | 219 | POST | `/api/tasks/dispatch'` | - |
| mobile_api_ai/container_api_server.py | 236 | GET | `/api/tasks/<task_id>'` | - |
| mobile_api_ai/container_api_server.py | 246 | POST | `/api/tasks/<task_id>/start'` | - |
| mobile_api_ai/container_api_server.py | 258 | POST | `/api/tasks/<task_id>/complete'` | - |
| mobile_api_ai/container_api_server.py | 270 | POST | `/api/ai/speech-to-report'` | - |
| mobile_api_ai/container_api_server.py | 327 | POST | `/api/ai/chat'` | - |
| mobile_api_ai/container_api_server.py | 369 | GET | `/api/pool/status'` | - |
| mobile_api_ai/container_api_server.py | 381 | GET | `/api/operators'` | - |
| mobile_api_ai/container_api_server.py | 388 | POST | `/api/dispatch'` | - |
| mobile_api_ai/container_api_server.py | 434 | POST | `/api/internal/publish'` | - |
| mobile_api_ai/container_api_server.py | 474 | POST | `/publish-tasks'` | - |
| mobile_api_ai/container_api_server.py | 500 | POST | `/api/schedule/publish'` | - |
| mobile_api_ai/container_center_api.py | 776 | POST | `/api/enterprise/structure'` | - |
| mobile_api_ai/container_center_api.py | 818 | GET | `/api/enterprise/structure'` | - |
| mobile_api_ai/container_center_api.py | 953 | GET | `/api/process_sub_steps/<order_no>/<process_code>'` | - |
| mobile_api_ai/container_center_api.py | 1155 | GET | `/health` | - |
| mobile_api_ai/container_center_api.py | 1178 | GET | `/` | - |
| mobile_api_ai/container_center_api.py | 1182 | GET | `/api/dashboard` | - |
| mobile_api_ai/container_center_api.py | 1189 | POST | `/api/callback'` | - |
| mobile_api_ai/container_center_api.py | 1229 | GET | `/api/health` | - |
| mobile_api_ai/container_center_api.py | 1240 | GET | `/api/status` | - |
| mobile_api_ai/container_center_api.py | 1254 | GET | `/api/operators'` | - |
| mobile_api_ai/container_center_api.py | 1322 | GET | `/api/v4/operators'` | - |
| mobile_api_ai/container_center_api.py | 1327 | GET | `/api/v4/work_order'` | - |
| mobile_api_ai/container_center_api.py | 1377 | GET | `/favicon.ico` | - |
| mobile_api_ai/container_center_api.py | 1381 | GET | `/api/process_names'` | - |
| mobile_api_ai/container_center_api.py | 1399 | GET | `/api/process_departments'` | - |
| mobile_api_ai/container_center_api.py | 1408 | PUT,POST | `/api/process_departments/<process_code>'` | - |
| mobile_api_ai/container_center_api.py | 1419 | DELETE | `/api/process_departments/<process_code>'` | - |
| mobile_api_ai/container_center_api.py | 1429 | DELETE | `/api/process_names/<process_name>'` | - |
| mobile_api_ai/container_center_api.py | 1473 | POST | `/api/dispatch'` | - |
| mobile_api_ai/container_center_api.py | 1474 | POST | `/api/wechat/dispatch'` | - |
| mobile_api_ai/container_center_api.py | 1776 | POST | `/api/schedule/publish'` | - |
| mobile_api_ai/container_center_api.py | 2095 | POST | `/api/auth/login'` | - |
| mobile_api_ai/container_center_api.py | 2125 | GET | `/api/auth/verify'` | - |
| mobile_api_ai/container_center_api.py | 2132 | GET | `/api/pool/status'` | - |
| mobile_api_ai/container_center_api.py | 2138 | GET | `/api/processes'` | - |
| mobile_api_ai/container_center_api.py | 2150 | GET | `/api/processes/<record_id>'` | - |
| mobile_api_ai/container_center_api.py | 2158 | POST | `/api/processes'` | - |
| mobile_api_ai/container_center_api.py | 2191 | PUT | `/api/processes/<record_id>'` | - |
| mobile_api_ai/container_center_api.py | 2208 | PUT | `/api/processes/<record_id>/status'` | - |
| mobile_api_ai/container_center_api.py | 2226 | PUT | `/api/processes/<record_id>/template'` | - |
| mobile_api_ai/container_center_api.py | 2243 | PUT | `/api/processes/<record_id>/step'` | - |
| mobile_api_ai/container_center_api.py | 2257 | PUT | `/api/processes/<record_id>/tasks'` | - |
| mobile_api_ai/container_center_api.py | 2271 | DELETE | `/api/processes/<record_id>'` | - |
| mobile_api_ai/container_center_api.py | 2280 | GET | `/api/processes/by-order/<order_no>'` | - |
| mobile_api_ai/container_center_api.py | 2297 | GET | `/api/orders/full-status/<order_no>'` | - |
| mobile_api_ai/container_center_api.py | 2473 | GET | `/api/orders/full-status-list'` | - |
| mobile_api_ai/container_center_api.py | 2565 | GET | `/api/orders/<order_no>'` | _mirror_auth_warn_cache |
| mobile_api_ai/container_center_api.py | 2650 | POST | `/api/process_sub_steps/mirror'` | Redis cache<br>_mirror_auth_warn_cache |
| mobile_api_ai/container_center_api.py | 2732 | GET | `/api/tasks'` | - |
| mobile_api_ai/container_center_api.py | 2789 | GET | `/api/tasks/<task_id>'` | - |
| mobile_api_ai/container_center_api.py | 2797 | POST | `/api/tasks/<task_id>/acknowledge'` | - |
| mobile_api_ai/container_center_api.py | 2810 | GET | `/api/tasks/unacknowledged'` | - |
| mobile_api_ai/container_center_api.py | 2823 | POST | `/api/tasks/<task_id>/complete'` | - |
| mobile_api_ai/container_center_api.py | 2886 | POST | `/api/internal/publish'` | - |
| mobile_api_ai/container_center_api.py | 3011 | POST | `/api/internal/config/deploy'` | - |
| mobile_api_ai/container_center_api.py | 3054 | GET | `/api/internal/config/versions/<config_name>'` | - |
| mobile_api_ai/container_center_api.py | 3072 | POST | `/api/internal/config/rollback'` | - |
| mobile_api_ai/container_center_api.py | 3138 | GET | `/api/outsource/records'` | - |
| mobile_api_ai/container_center_api.py | 3151 | GET | `/api/outsource/records/<record_id>'` | - |
| mobile_api_ai/container_center_api.py | 3164 | POST | `/api/internal/outsource/publish'` | - |
| mobile_api_ai/container_center_api.py | 3227 | POST | `/api/outsource/records/<record_id>/feedback'` | - |
| mobile_api_ai/container_center_api.py | 3246 | POST | `/api/outsource/records/<record_id>/complete'` | - |
| mobile_api_ai/container_center_api.py | 3271 | POST | `/api/outsource/records/<record_id>/receive'` | - |
| mobile_api_ai/container_center_api.py | 3296 | GET | `/api/outsource/config'` | - |
| mobile_api_ai/container_center_api.py | 3309 | POST | `/api/outsource/config'` | - |
| mobile_api_ai/container_center_api.py | 3318 | GET | `/api/wechat/get_access_token'` | - |
| mobile_api_ai/container_center_api.py | 3376 | POST | `/api/process_sub_step'` | - |
| mobile_api_ai/container_center_api.py | 3515 | GET | `/api/process_sub_steps/<order_no>'` | - |
| mobile_api_ai/container_center_api.py | 3527 | GET | `/api/process_sub_step_summary/<order_no>'` | - |
| mobile_api_ai/container_center_api.py | 3731 | GET | `/api/process_sub_step/summary_by_order/<order_no>'` | - |
| mobile_api_ai/container_center_api.py | 3750 | GET | `/api/scan-info'` | - |
| mobile_api_ai/container_center_api.py | 3881 | GET | `/api/flow-type/<product_type_id>'` | - |
| mobile_api_ai/container_center_api.py | 3887 | POST | `/api/flow-map/sync'` | - |
| mobile_api_ai/container_center_api.py | 3897 | POST | `/api/sub-step/rollback'` | - |
| mobile_api_ai/container_center_api.py | 3946 | GET | `/api/sub-step/audit/<order_no>'` | - |
| mobile_api_ai/container_center_api.py | 3955 | POST | `/api/sub-step/repair-mysql'` | - |
| mobile_api_ai/container_center_api.py | 4035 | POST | `/api/material/create'` | - |
| mobile_api_ai/container_center_api.py | 4068 | GET | `/api/material/list'` | - |
| mobile_api_ai/container_center_api.py | 4083 | POST | `/api/material/confirm'` | - |
| mobile_api_ai/container_center_api.py | 4139 | POST | `/api/material/arrived'` | - |
| mobile_api_ai/container_center_api.py | 4162 | POST | `/api/material/delivered'` | - |
| mobile_api_ai/container_center_api.py | 4186 | GET | `/api/material/<pkg_id>'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 121 | GET,POST | `/api/wechat/hook'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 211 | POST | `/api/wechat/callback'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 256 | POST | `/api/forward'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 320 | POST | `/api/queue/forward'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 344 | GET | `/api/queue/poll'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 358 | GET | `/api/poll'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 363 | POST | `/api/queue/ack'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 372 | POST | `/api/poll/ack'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 378 | POST | `/api/response'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 421 | POST | `/api/response/callback'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 454 | GET | `/api/dead'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 469 | GET | `/api/queue/status'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 487 | GET | `/api/messages/outgoing'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 510 | GET | `/api/messages/<msg_id>'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 528 | POST | `/api/messages/retry'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 573 | GET | `/api/messages/stats'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 590 | POST | `/api/wechat/send'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 627 | POST | `/api/wechat/send_text'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 635 | POST | `/api/wechat/proxy_send'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 695 | GET | `/logs'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 717 | GET | `/api/backup/status'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 832 | GET,POST | `/cloud/org/enterprise_structure'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 890 | GET | `/api/wechat/users'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 891 | GET | `/api/wechat/contacts'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 977 | GET | `/api/wechat/user/<user_id>'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 1008 | GET | `/api/wechat/user/<user_id>/name'` | - |
| mobile_api_ai/deploy_output/wechat_cloud.py | 1049 | GET | `/health'` | - |
| mobile_api_ai/face_checkin/__init__.py | 211 | GET | `/api/ip` | - |
| mobile_api_ai/face_checkin/__init__.py | 216 | GET,PUT | `/api/config'` | - |
| mobile_api_ai/face_checkin/__init__.py | 235 | POST | `/api/admin/login'` | - |
| mobile_api_ai/face_checkin/__init__.py | 261 | GET | `/api/admin/check'` | - |
| mobile_api_ai/face_checkin/__init__.py | 268 | PUT | `/api/admin/password'` | - |
| mobile_api_ai/face_checkin/__init__.py | 295 | GET | `/api/admin/users'` | - |
| mobile_api_ai/face_checkin/__init__.py | 304 | POST | `/api/admin/users'` | - |
| mobile_api_ai/face_checkin/__init__.py | 325 | DELETE | `/api/admin/users'` | - |
| mobile_api_ai/face_checkin/__init__.py | 349 | GET | `/api/drives` | - |
| mobile_api_ai/face_checkin/__init__.py | 360 | POST | `/api/list-dirs'` | - |
| mobile_api_ai/face_checkin/__init__.py | 380 | POST | `/api/create-dir'` | - |
| mobile_api_ai/face_checkin/__init__.py | 403 | POST | `/api/upload-photo'` | - |
| mobile_api_ai/face_checkin/__init__.py | 429 | POST | `/api/enroll'` | - |
| mobile_api_ai/face_checkin/__init__.py | 444 | GET,DELETE | `/api/enrollments'` | - |
| mobile_api_ai/face_checkin/__init__.py | 464 | DELETE | `/api/enrollments/<name>'` | - |
| mobile_api_ai/face_checkin/__init__.py | 472 | GET | `/api/enrollments/photo` | - |
| mobile_api_ai/face_checkin/__init__.py | 660 | POST | `/api/checkin'` | - |
| mobile_api_ai/face_checkin/__init__.py | 695 | GET | `/api/checkins'` | - |
| mobile_api_ai/face_checkin/__init__.py | 724 | GET | `/api/photos/<path:filename>` | - |
| mobile_api_ai/face_checkin/__init__.py | 747 | POST | `/api/export-checkins'` | - |
| mobile_api_ai/face_checkin/__init__.py | 853 | GET,POST | `/api/scheduler'` | - |
| mobile_api_ai/face_checkin/__init__.py | 889 | POST | `/api/send-attendance-to-cloud'` | - |
| mobile_api_ai/face_checkin/__init__.py | 952 | GET | `/` | - |
| mobile_api_ai/face_checkin/__init__.py | 957 | GET | `/admin/` | - |
| mobile_api_ai/face_checkin/__init__.py | 961 | GET | `/admin/<path:filename>` | - |
| mobile_api_ai/face_checkin/__init__.py | 973 | GET | `/app/` | - |
| mobile_api_ai/face_checkin/__init__.py | 978 | GET | `/app/<path:rest>` | - |
| mobile_api_ai/face_checkin/__init__.py | 983 | GET | `/assets/<path:filename>` | - |
| mobile_api_ai/face_checkin/__init__.py | 988 | GET | `/models/<path:filename>` | - |
| mobile_api_ai/face_checkin/__init__.py | 993 | GET | `/wasm/<path:filename>` | - |
| mobile_api_ai/face_server.py | 32 | GET | `/` | - |
| mobile_api_ai/face_server.py | 36 | GET | `/models/<path:filename>` | - |
| mobile_api_ai/face_server.py | 40 | GET | `/wasm/<path:filename>` | - |
| mobile_api_ai/inventory_api_server.py | 301 | GET,POST | `/login'` | - |
| mobile_api_ai/inventory_api_server.py | 343 | GET | `/logout` | - |
| mobile_api_ai/inventory_api_server.py | 349 | GET | `/` | - |
| mobile_api_ai/inventory_api_server.py | 360 | GET | `/api/csrf-token'` | - |
| mobile_api_ai/inventory_api_server.py | 379 | GET | `/api/health'` | - |
| mobile_api_ai/inventory_web/admin_auth.py | 34 | POST | `/inventory/api/product/add'` | - |
| mobile_api_ai/inventory_web/admin_auth.py | 94 | POST | `/inventory/api/settings'` | - |
| mobile_api_ai/inventory_web/feature_flags.py | 120 | POST | `/inventory/api/stocktake/create'` | - |
| mobile_api_ai/inventory_web/feature_flags.py | 155 | GET | `...` | - |
| mobile_api_ai/inventory_web/routes_api.py | 35 | PATCH,DELETE | `/inventory/api/<entity>/<int:eid>'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 43 | POST | `/inventory/api/alert/<int:aid>/resolve'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 51 | POST | `/inventory/api/stock/adjust'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 59 | POST | `/inventory/api/settings'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 70 | POST | `/inventory/api/cleanup'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 81 | GET | `/inventory/reports'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 87 | GET | `/inventory/api/report/stock-trend'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 96 | GET | `/inventory/api/report/io-flow'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 105 | GET | `/inventory/api/report/top-low-stock'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 114 | GET | `/inventory/api/report/category-distribution'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 125 | GET | `/inventory/notifications'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 131 | GET | `/inventory/api/notification/list'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 144 | GET | `/inventory/api/notification/unread-count'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 154 | POST | `/inventory/api/notification/<int:nid>/read'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 162 | POST | `/inventory/api/notification/read-all'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 170 | POST | `/inventory/api/notification/check-low-stock'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 182 | GET | `/inventory/scanner'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 191 | GET | `/inventory/api/import/template'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 230 | POST | `/inventory/api/import/dry-run'` | - |
| mobile_api_ai/inventory_web/routes_api.py | 307 | POST | `/inventory/api/import/commit'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 46 | GET | `/inventory/dashboard'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 154 | GET | `/inventory/stock'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 184 | GET | `/inventory/api/stock/list'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 205 | GET | `/inventory/inbound'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 241 | POST | `/inventory/api/inbound/do'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 338 | GET | `/inventory/outbound'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 373 | POST | `/inventory/api/outbound/do'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 443 | GET | `/inventory/alerts'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 493 | POST | `/inventory/api/alert/<int:alert_id>/resolve'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 505 | GET | `/inventory/warehouses'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 525 | POST | `/inventory/warehouses/add', endpoint='wh_add_view` | - |
| mobile_api_ai/inventory_web/routes_core.py | 544 | POST | `/inventory/warehouses/edit/<int:wid>'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 556 | POST | `/inventory/warehouses/toggle/<int:wid>'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 569 | POST | `/inventory/warehouses/delete/<int:wid>', endpoint='warehouse_delete_page` | - |
| mobile_api_ai/inventory_web/routes_core.py | 587 | GET | `/inventory/categories'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 618 | POST | `/inventory/categories/add', endpoint='category_add_view` | - |
| mobile_api_ai/inventory_web/routes_core.py | 634 | POST | `/inventory/products/add', endpoint='product_add_simple` | - |
| mobile_api_ai/inventory_web/routes_core.py | 660 | GET | `/inventory/export'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 665 | GET | `/inventory/print/preview'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 699 | GET | `/inventory/base'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 744 | POST | `/inventory/base/<kind>/add', endpoint='base_add_page` | - |
| mobile_api_ai/inventory_web/routes_core.py | 774 | GET | `/inventory/settings'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 785 | POST | `/inventory/api/settings'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 810 | GET | `/inventory/batch'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 830 | POST | `/inventory/api/batch/do'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 939 | GET | `/inventory/api/inventory/alert'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 960 | GET | `/inventory/stocktake'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 966 | POST | `/inventory/api/stocktake/create'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 982 | POST | `/inventory/api/stocktake/<int:sid>/submit'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 996 | POST | `/inventory/api/stocktake/<int:sid>/adjust'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 1011 | GET | `/inventory/api/stocktake/list'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 1026 | GET | `/inventory/api/stocktake/<int:sid>/items'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 1040 | GET | `/inventory/transfer'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 1046 | POST | `/inventory/api/transfer/create'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 1065 | POST | `/inventory/api/transfer/<int:tid>/complete'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 1075 | POST | `/inventory/api/transfer/<int:tid>/cancel'` | - |
| mobile_api_ai/inventory_web/routes_core.py | 1087 | GET | `/inventory/api/transfer/list'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 129 | GET | `/inventory/products'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 133 | GET | `/inventory/api/product/list'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 145 | POST | `/inventory/api/product/add'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 190 | DELETE | `/inventory/api/product/<int:pid>/delete'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 200 | PATCH | `/inventory/api/product/<int:pid>/update'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 237 | GET | `/inventory/suppliers'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 241 | POST | `/inventory/api/supplier/add'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 273 | POST | `/inventory/api/category/add'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 302 | POST | `/inventory/api/base/add'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 411 | DELETE | `/inventory/api/supplier/<int:eid>/delete'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 417 | DELETE | `/inventory/api/category/<int:eid>/delete'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 423 | DELETE | `/inventory/api/base/<int:eid>/delete'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 429 | DELETE | `/inventory/api/warehouse/<int:eid>/delete'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 438 | POST | `/inventory/api/warehouse/add'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 466 | GET | `/inventory/api/recycle-bin/list'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 487 | POST | `/inventory/api/recycle-bin/<entity>/<int:eid>/restore'` | - |
| mobile_api_ai/inventory_web/routes_data.py | 496 | GET | `/inventory/recycle-bin'` | - |
| mobile_api_ai/inventory_web/routes_external.py | 25 | GET | `/dashboard'` | - |
| mobile_api_ai/inventory_web/routes_external.py | 47 | GET | `/alerts'` | - |
| mobile_api_ai/inventory_web/routes_external.py | 73 | GET | `/search'` | - |
| mobile_api_ai/inventory_web/routes_system.py | 40 | GET | `/inventory/backup'` | - |
| mobile_api_ai/inventory_web/routes_system.py | 65 | POST | `/inventory/api/backup/create'` | - |
| mobile_api_ai/inventory_web/routes_system.py | 125 | GET | `/inventory/api/backup/download/<filename>'` | - |
| mobile_api_ai/inventory_web/routes_system.py | 162 | POST | `/inventory/api/backup/delete'` | - |
| mobile_api_ai/inventory_web/routes_system.py | 194 | POST | `/inventory/api/backup/restore'` | - |
| mobile_api_ai/inventory_web/routes_system.py | 252 | GET | `/inventory/api/settings'` | - |
| mobile_api_ai/inventory_web/routes_system.py | 271 | POST | `/inventory/api/settings'` | - |
| mobile_api_ai/inventory_web/routes_system.py | 313 | POST | `/inventory/api/cleanup'` | - |
| mobile_api_ai/inventory_web/routes_system.py | 354 | GET | `/inventory/api/system/info'` | - |
| mobile_api_ai/scripts/cloud/cloud_group_bot_service.py | 84 | POST | `/api/send'` | - |
| mobile_api_ai/scripts/cloud/cloud_group_bot_service.py | 115 | GET | `/api/health'` | - |
| mobile_api_ai/scripts/cloud/cloud_group_bot_service.py | 155 | POST | `/api/smartsheet/write'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 81 | POST | `/api/login'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 189 | GET | `/favicon.ico` | - |
| mobile_api_ai/standalone_dispatch_server.py | 193 | GET | `/` | - |
| mobile_api_ai/standalone_dispatch_server.py | 199 | GET | `/api/enterprise/structure'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 208 | GET | `/api/sync-queue/list'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 244 | POST | `/api/sync-queue/retry'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 288 | POST | `/api/enterprise/structure'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 313 | GET | `/health` | - |
| mobile_api_ai/standalone_dispatch_server.py | 340 | GET | `/api/report_record/list'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 387 | POST | `/api/report_record/update'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 484 | POST | `/api/report_record/withdraw'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 550 | GET | `/api/report_record/history_full'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 579 | GET | `/api/outsource_record/list'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 627 | POST | `/api/outsource_record/update'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 668 | POST | `/api/outsource_record/withdraw'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 705 | GET | `/api/outsource_record/history_full'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 731 | GET | `/api/quality_record/list'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 772 | GET | `/api/material_record/list'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 816 | GET | `/workorder'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 831 | GET | `/production-orders'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 835 | GET | `/outsource-records'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 851 | GET | `/status'` | - |
| mobile_api_ai/standalone_dispatch_server.py | 1189 | POST | `/api/dispatch-center/report-submitted'` | - |
| mobile_api_ai/sync_bridge_server.py | 81 | GET | `/health` | - |
| mobile_api_ai/sync_bridge_server.py | 99 | GET | `/api/health` | - |
| mobile_api_ai/wechat_cloud.py | 121 | GET,POST | `/api/wechat/hook'` | - |
| mobile_api_ai/wechat_cloud.py | 211 | POST | `/api/wechat/callback'` | - |
| mobile_api_ai/wechat_cloud.py | 256 | POST | `/api/forward'` | - |
| mobile_api_ai/wechat_cloud.py | 320 | POST | `/api/queue/forward'` | - |
| mobile_api_ai/wechat_cloud.py | 344 | GET | `/api/queue/poll'` | - |
| mobile_api_ai/wechat_cloud.py | 358 | GET | `/api/poll'` | - |
| mobile_api_ai/wechat_cloud.py | 363 | POST | `/api/queue/ack'` | - |
| mobile_api_ai/wechat_cloud.py | 372 | POST | `/api/poll/ack'` | - |
| mobile_api_ai/wechat_cloud.py | 378 | POST | `/api/response'` | - |
| mobile_api_ai/wechat_cloud.py | 421 | POST | `/api/response/callback'` | - |
| mobile_api_ai/wechat_cloud.py | 454 | GET | `/api/dead'` | - |
| mobile_api_ai/wechat_cloud.py | 469 | GET | `/api/queue/status'` | - |
| mobile_api_ai/wechat_cloud.py | 487 | GET | `/api/messages/outgoing'` | - |
| mobile_api_ai/wechat_cloud.py | 510 | GET | `/api/messages/<msg_id>'` | - |
| mobile_api_ai/wechat_cloud.py | 528 | POST | `/api/messages/retry'` | - |
| mobile_api_ai/wechat_cloud.py | 573 | GET | `/api/messages/stats'` | - |
| mobile_api_ai/wechat_cloud.py | 590 | POST | `/api/wechat/send'` | - |
| mobile_api_ai/wechat_cloud.py | 627 | POST | `/api/wechat/send_text'` | - |
| mobile_api_ai/wechat_cloud.py | 635 | POST | `/api/wechat/proxy_send'` | - |
| mobile_api_ai/wechat_cloud.py | 695 | GET | `/logs'` | - |
| mobile_api_ai/wechat_cloud.py | 717 | GET | `/api/backup/status'` | - |
| mobile_api_ai/wechat_cloud.py | 832 | GET,POST | `/cloud/org/enterprise_structure'` | - |
| mobile_api_ai/wechat_cloud.py | 890 | GET | `/api/wechat/users'` | - |
| mobile_api_ai/wechat_cloud.py | 891 | GET | `/api/wechat/contacts'` | - |
| mobile_api_ai/wechat_cloud.py | 977 | GET | `/api/wechat/user/<user_id>'` | - |
| mobile_api_ai/wechat_cloud.py | 1008 | GET | `/api/wechat/user/<user_id>/name'` | - |
| mobile_api_ai/wechat_cloud.py | 1049 | GET | `/health'` | - |
| mobile_api_ai/wechat_server.py | 186 | GET | `/favicon.ico` | - |
| mobile_api_ai/wechat_server.py | 192 | GET | `/models/<path:filename>` | - |
| mobile_api_ai/wechat_server.py | 196 | GET | `/wasm/<path:filename>` | - |
| mobile_api_ai/wechat_server.py | 514 | GET | `/` | - |
| mobile_api_ai/wechat_server.py | 521 | GET | `/<path:filename>` | Redis cache<br>Redis cache (alias) |
| mobile_api_ai/wechat_server.py | 631 | POST | `/api/sync/task'` | - |
| mobile_api_ai/wechat_server.py | 785 | POST | `/api/sync/report'` | - |
| mobile_api_ai/wechat_server.py | 981 | POST | `/api/sync/report/actual'` | - |
| mobile_api_ai/wechat_server.py | 1055 | GET | `/api/sync/status'` | - |
| mobile_api_ai/wechat_server.py | 1066 | GET | `/api/sync/health/detailed'` | - |
| mobile_api_ai/wechat_server.py | 1092 | POST | `/api/sync/validate/input'` | - |
| mobile_api_ai/wechat_server.py | 1138 | POST | `/api/sync/delivery-date-change'` | - |
| mobile_api_ai/wechat_server.py | 1194 | POST | `/api/sync/drift/check'` | - |
| mobile_api_ai/wechat_server.py | 1230 | POST | `/api/sync/data/fingerprint'` | - |
| mobile_api_ai/wechat_server.py | 1261 | GET | `/api/sync/circuit/status'` | - |
| mobile_api_ai/wechat_server.py | 1302 | POST | `/api/sync/circuit/reset'` | - |
| mobile_api_ai/wechat_server.py | 1321 | GET | `/api/sync/queue/status'` | - |
| mobile_api_ai/wechat_server.py | 1354 | GET | `/api/sync/queue/stats'` | - |
| mobile_api_ai/wechat_server.py | 1385 | GET | `/api/sync/tasks'` | - |
| mobile_api_ai/wechat_server.py | 1421 | GET | `/api/sync/tasks/<task_id>'` | - |
| mobile_api_ai/wechat_server.py | 1438 | GET | `/api/sync/task/<order_no>/status'` | - |
| mobile_api_ai/wechat_server.py | 1507 | POST | `/api/sync/outsource/publish'` | - |
| mobile_api_ai/wechat_server.py | 1566 | GET,POST | `/api/wechat/hook'` | - |
| mobile_api_ai/wechat_server.py | 2151 | GET | `/api/sync/reports'` | - |
| mobile_api_ai/wechat_server.py | 2202 | GET | `/api/logs/operations'` | - |
| mobile_api_ai/wechat_server.py | 2203 | GET | `/api/sync/logs'` | - |
| mobile_api_ai/wechat_server.py | 2250 | GET | `/api/logs/stats'` | - |
| mobile_api_ai/wechat_server.py | 2269 | GET | `/api/wechat/departments'` | - |
| mobile_api_ai/wechat_server.py | 2286 | GET | `/api/wechat/users'` | - |
| mobile_api_ai/wechat_server.py | 2319 | GET | `/api/wechat/user/<user_id>'` | - |
| mobile_api_ai/wechat_server.py | 2348 | GET | `/health` | - |
| mobile_api_ai/wechat_server.py | 2357 | GET | `/api/poll'` | - |
| mobile_api_ai/wechat_server.py | 2376 | GET | `/api/cloud/status` | - |
| mobile_api_ai/wechat_server.py | 2420 | POST | `/api/cloud/send'` | - |
| mobile_api_ai/wechat_server.py | 2469 | POST | `/api/wechat/proxy_send'` | - |
| mobile_api_ai/wechat_server.py | 2529 | POST | `/api/wechat/send'` | - |
| mobile_api_ai/wechat_server.py | 2578 | GET | `/api/wechat/status` | - |
| mobile_api_ai/wechat_server.py | 2687 | POST | `/api/sync/report/wechat'` | - |
| mobile_api_ai/wechat_server.py | 2898 | POST | `/api/sync/report/confirm'` | - |
| mobile_api_ai/wechat_server.py | 3025 | GET | `/api/sync/report/requests'` | - |
| mobile_api_ai/wecom_auth.py | 19 | POST | `/login'` | - |