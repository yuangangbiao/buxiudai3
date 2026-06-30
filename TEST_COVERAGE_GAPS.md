================================================================================
测试覆盖率缺口分析报告
================================================================================


================================================================================
模块: CORE
================================================================================

文件数: 23
可测试项总数: 194

详细文件分析:

  📄 app.py
     可测试项: 8
       - get_version() (行18)
       - get_build_info() (行24)
       - initialize_app() (行40)
       - create_secure_flask_app() (行109)
       - on_order_status_changed() (行98)
       - on_inventory_low() (行103)
       - handle_global_exception() (行142)
       - favicon() (行147)

  📄 circuit_breaker.py
     可测试项: 4
       - CircuitBreaker.state (行25)
       - CircuitBreaker.call (行28)
       - state() (行25)
       - call() (行28)

  📄 common_queries.py
     可测试项: 5
       - find_by_id() (行7)
       - find_by_column() (行17)
       - find_all_by_column() (行27)
       - aggregate() (行43)
       - upsert_select() (行63)

  📄 config.py
     可测试项: 1
       - now() (行31)

  📄 cors_config.py
     可测试项: 1
       - init_cors() (行6)

  📄 db.py
     可测试项: 39
       - ConnectionPool.init (行79)
       - ConnectionPool.get (行97)
       - ConnectionPool.return_connection (行117)
       - ConnectionPool.close_all (行133)
       - PooledConnection.close (行153)
       - PooledConnection.cursor (行156)
       - PooledConnection.commit (行159)
       - PooledConnection.rollback (行162)
       - DB.init (行175)
       - DB.get_connection (行211)
       ... 还有 29 项

  📄 db_compat.py
     可测试项: 9
       - get_conn() (行30)
       - _PooledConnShim.cursor (行49)
       - _PooledConnShim.commit (行53)
       - _PooledConnShim.rollback (行56)
       - _PooledConnShim.close (行59)
       - cursor() (行49)
       - commit() (行53)
       - rollback() (行56)
       - close() (行59)

  📄 error_codes.py
     可测试项: 16
       - ErrorCode.to_dict (行77)
       - StructuredErrorCode.to_dict (行146)
       - get_error() (行724)
       - get_error_by_e_code() (行729)
       - get_errors_by_domain() (行737)
       - get_errors_by_severity_new() (行742)
       - get_all_errors() (行747)
       - get_error_count() (行752)
       - get_errors_summary() (行757)
       - get_error_info() (行1225)
       ... 还有 6 项

  📄 error_codes_structured.py
     可测试项: 0

  📄 error_handler.py
     可测试项: 7
       - recognize_error_code() (行58)
       - handle_error() (行78)
       - show_error_dialog() (行112)
       - log_error_to_db() (行135)
       - safe_error_handle() (行162)
       - get_error_lookup_url() (行183)
       - wrapper() (行172)

  📄 events.py
     可测试项: 13
       - EventType.get_all_events (行77)
       - EventType.is_valid_event (行90)
       - EventType.get_event_category (行108)
       - EventData.get (行142)
       - EventData.set (行146)
       - EventData.to_dict (行150)
       - create_event() (行162)
       - get_all_events() (行77)
       - is_valid_event() (行90)
       - get_event_category() (行108)
       ... 还有 3 项

  📄 event_bus.py
     可测试项: 15
       - EventBus.reset (行33)
       - EventBus.subscribe (行40)
       - EventBus.unsubscribe (行53)
       - EventBus.publish (行66)
       - EventBus.clear (行84)
       - EventBus.get_handlers (行98)
       - on_event() (行130)
       - publish() (行138)
       - reset() (行33)
       - subscribe() (行40)
       ... 还有 5 项

  📄 event_bus_factory.py
     可测试项: 1
       - create_event_bus() (行9)

  📄 event_store.py
     可测试项: 7
       - set_connection_factory() (行20)
       - EventStore.append (行30)
       - EventStore.get_events (行52)
       - EventStore.replay (行72)
       - append() (行30)
       - get_events() (行52)
       - replay() (行72)

  📄 exceptions.py
     可测试项: 9
       - BusinessException.to_dict (行23)
       - safe_cursor_execute() (行106)
       - safe_cursor_insert() (行124)
       - handle_exceptions() (行141)
       - validation_required() (行157)
       - to_dict() (行23)
       - wrapper() (行144)
       - decorator() (行159)
       - wrapper() (行161)

  📄 feature_flags.py
     可测试项: 6
       - FeatureFlags.load (行22)
       - FeatureFlags.is_enabled (行34)
       - FeatureFlags.all (行47)
       - load() (行22)
       - is_enabled() (行34)
       - all() (行47)

  📄 json_safe.py
     可测试项: 2
       - require_json_content_type() (行5)
       - wrapper() (行17)

  📄 logger.py
     可测试项: 18
       - LogManager.get_logger (行75)
       - get_logger() (行86)
       - StructuredLogger.info (行126)
       - StructuredLogger.warning (行129)
       - StructuredLogger.error (行132)
       - StructuredLogger.debug (行135)
       - StructuredLogger.critical (行138)
       - StructuredLogger.exception (行141)
       - get_structured_logger() (行149)
       - get_request_id() (行163)
       ... 还有 8 项

  📄 metrics.py
     可测试项: 13
       - MetricsCollector.increment (行13)
       - MetricsCollector.record_latency (行17)
       - MetricsCollector.get_counters (行23)
       - MetricsCollector.get_p99 (行26)
       - MetricsCollector.get_summary (行34)
       - record_metric() (行43)
       - record_latency() (行46)
       - get_metrics() (行49)
       - increment() (行13)
       - record_latency() (行17)
       ... 还有 3 项

  📄 redis_event_bus.py
     可测试项: 4
       - RedisEventBus.publish (行38)
       - RedisEventBus.subscribe (行53)
       - publish() (行38)
       - subscribe() (行53)

  📄 rule_engine.py
     可测试项: 5
       - RuleEngine.get_process_rules (行35)
       - RuleEngine.get_process (行39)
       - get_rule_engine() (行48)
       - get_process_rules() (行35)
       - get_process() (行39)

  📄 saga.py
     可测试项: 11
       - SagaOrchestrator.run (行27)
       - create_order_fulfillment_saga() (行70)
       - run() (行27)
       - schedule() (行72)
       - unschedule() (行73)
       - produce() (行74)
       - unproduce() (行75)
       - qc_pass() (行76)
       - qc_reject() (行77)
       - ship() (行78)
       ... 还有 1 项

  📄 __init__.py
     可测试项: 0


================================================================================
模块: MODELS
================================================================================

文件数: 23
可测试项总数: 416

详细文件分析:

  📄 alert.py
     可测试项: 9
       - AlertDAO.get_overdue_orders (行13)
       - AlertDAO.get_overdue_processes (行101)
       - AlertDAO.get_low_inventory_alerts (行146)
       - AlertDAO.get_all_alerts (行169)
       - init_alert_table() (行180)
       - get_overdue_orders() (行13)
       - get_overdue_processes() (行101)
       - get_low_inventory_alerts() (行146)
       - get_all_alerts() (行169)

  📄 base_dao.py
     可测试项: 20
       - BaseDAO.get_by_id (行31)
       - BaseDAO.get_all (行45)
       - BaseDAO.create (行80)
       - BaseDAO.update (行111)
       - BaseDAO.delete (行143)
       - BaseDAO.count (行168)
       - BaseDAO.exists (行187)
       - BaseDAO.get_paginated (行200)
       - BaseDAO.bulk_create (行229)
       - BaseDAO.bulk_update (行259)
       ... 还有 10 项

  📄 bom.py
     可测试项: 17
       - BOMDAO.create (行13)
       - BOMDAO.update (行62)
       - BOMDAO.delete (行125)
       - BOMDAO.get_by_id (行136)
       - BOMDAO.get_by_product (行147)
       - BOMDAO.get_all (行167)
       - BOMDAO.get_recent (行190)
       - BOMDAO.calculate_material_requirement (行208)
       - init_bom_table() (行241)
       - create() (行13)
       ... 还有 7 项

  📄 enums.py
     可测试项: 28
       - OrderStatus.values (行21)
       - OrderStatus.from_string (行26)
       - ProductionStatus.values (行48)
       - ProductionStatus.from_string (行53)
       - ProcessStatus.values (行71)
       - ProcessStatus.from_string (行76)
       - QualityResult.values (行94)
       - QualityResult.from_string (行99)
       - InventoryChange.values (行117)
       - InventoryChange.from_string (行122)
       ... 还有 18 项

  📄 inventory.py
     可测试项: 20
       - InventoryDAO.create (行13)
       - InventoryDAO.update (行40)
       - InventoryDAO.stock_in (行68)
       - InventoryDAO.stock_out (行95)
       - InventoryDAO.get_all (行124)
       - InventoryDAO.get_records (行149)
       - InventoryDAO.get_warning_items (行181)
       - InventoryDAO.get_dashboard_overview (行200)
       - InventoryDAO.get_low_inventory_alerts (行216)
       - InventoryDAO.search_by_material (行240)
       ... 还有 10 项

  📄 material_rules.py
     可测试项: 16
       - MaterialRulesDAO.create (行12)
       - MaterialRulesDAO.update (行33)
       - MaterialRulesDAO.delete (行67)
       - MaterialRulesDAO.get_by_id (行81)
       - MaterialRulesDAO.get_by_product_type (行94)
       - MaterialRulesDAO.get_all (行110)
       - MaterialRulesDAO.get_distinct_product_types (行125)
       - MaterialRulesDAO.exists (行140)
       - create() (行12)
       - update() (行33)
       ... 还有 6 项

  📄 material_rules_template.py
     可测试项: 9
       - get_all_templates() (行15)
       - get_template() (行38)
       - save_template() (行60)
       - update_template() (行98)
       - delete_template() (行133)
       - rename_template() (行149)
       - get_template_names() (行169)
       - clean_for_json() (行76)
       - clean_for_json() (行112)

  📄 operation_log.py
     可测试项: 17
       - OperationLogDAO.create (行19)
       - OperationLogDAO.get_by_order_id (行49)
       - OperationLogDAO.get_by_module (行69)
       - OperationLogDAO.get_by_action (行90)
       - OperationLogDAO.get_recent (行111)
       - OperationLogDAO.search (行131)
       - OperationLogDAO.clean_expired_logs (行152)
       - OperationLogDAO.count_by_module (行198)
       - log_operation() (行266)
       - create() (行19)
       ... 还有 7 项

  📄 operator.py
     可测试项: 22
       - OperatorDAO.get_all (行17)
       - OperatorDAO.get_by_id (行33)
       - OperatorDAO.get_by_wechat_userid (行49)
       - OperatorDAO.login (行67)
       - OperatorDAO.add (行118)
       - OperatorDAO.update (行158)
       - OperatorDAO.delete (行198)
       - OperatorDAO.change_password (行213)
       - OperatorLogDAO.add (行261)
       - OperatorLogDAO.get_logs (行276)
       ... 还有 12 项

  📄 order.py
     可测试项: 56
       - OrderDAO.create (行78)
       - OrderDAO.update (行135)
       - OrderDAO.update_status (行225)
       - OrderDAO.delete (行280)
       - OrderDAO.get_unscheduled (行303)
       - OrderDAO.get_by_id (行327)
       - OrderDAO.get_all (行340)
       - OrderDAO.get_recent_for_kanban (行390)
       - OrderDAO.get_recent_for_list (行409)
       - OrderDAO.get_all_paginated (行427)
       ... 还有 46 项

  📄 order_log.py
     可测试项: 15
       - OrderLogDAO.create (行15)
       - OrderLogDAO.get_by_order_id (行44)
       - OrderLogDAO.get_all (行64)
       - OrderLogDAO.get_by_operator (行84)
       - OrderLogDAO.get_by_action (行105)
       - OrderLogDAO.search (行126)
       - OrderLogDAO.count_by_action (行147)
       - log_order_action() (行183)
       - create() (行15)
       - get_by_order_id() (行44)
       ... 还有 5 项

  📄 photo_storage.py
     可测试项: 5
       - safe_filename() (行27)
       - validate_magic() (行34)
       - strip_exif() (行45)
       - save() (行58)
       - delete() (行87)

  📄 process.py
     可测试项: 20
       - ProcessDAO.update_record (行13)
       - ProcessDAO.get_by_order (行135)
       - ProcessDAO.get_by_production (行151)
       - ProcessDAO.get_progress (行166)
       - ProcessDAO.get_worker_stats (行191)
       - ProcessDAO.get_by_id (行218)
       - ProcessDAO.create (行234)
       - ProcessDAO.delete (行258)
       - ProcessDAO.get_today_completed (行272)
       - ProcessDAO.get_today_completed_batch (行288)
       ... 还有 10 项

  📄 process_calc_rule.py
     可测试项: 26
       - ProcessCalcRuleDAO.get_all (行17)
       - ProcessCalcRuleDAO.get_by_process (行56)
       - ProcessCalcRuleDAO.create (行93)
       - ProcessCalcRuleDAO.update (行127)
       - ProcessCalcRuleDAO.delete (行165)
       - ProcessCalcRuleDAO.exists_for_process (行183)
       - ProcessCalcRuleDAO.init_default_rules (行199)
       - ProcessCalcEngine.calculate_planned_qty (行255)
       - ProcessCalcEngine.evaluate_condition (行363)
       - ProcessCalcEngine.should_include_process (行427)
       ... 还有 16 项

  📄 production.py
     可测试项: 18
       - ProductionDAO.create (行16)
       - ProductionDAO.update (行126)
       - ProductionDAO.update_status (行160)
       - ProductionDAO.confirm_schedule (行238)
       - ProductionDAO.get_all_with_order (行291)
       - ProductionDAO.get_by_id (行339)
       - ProductionDAO.get_by_order_id (行359)
       - ProductionDAO.get_by_order_ids (行381)
       - ProductionDAO.get_dashboard_production_list (行412)
       - create() (行16)
       ... 还有 8 项

  📄 production_stats.py
     可测试项: 10
       - ProductionStatsDAO.calculate_order_stats (行16)
       - ProductionStatsDAO.get_order_stats (行224)
       - ProductionStatsDAO.get_process_details (行246)
       - ProductionStatsDAO.calculate_all_orders_stats (行287)
       - ProductionStatsDAO.get_stats_summary (行321)
       - calculate_order_stats() (行16)
       - get_order_stats() (行224)
       - get_process_details() (行246)
       - calculate_all_orders_stats() (行287)
       - get_stats_summary() (行321)

  📄 product_flow_map.py
     可测试项: 2
       - ProductFlowMapDAO.get_flow_type (行24)
       - get_flow_type() (行24)

  📄 product_type.py
     可测试项: 14
       - ProductTypeDAO.create (行12)
       - ProductTypeDAO.get_all (行33)
       - ProductTypeDAO.get_all_names (行45)
       - ProductTypeDAO.exists (行60)
       - ProductTypeDAO.delete (行76)
       - ProductTypeDAO.update (行92)
       - ProductTypeDAO.init_default_types (行111)
       - create() (行12)
       - get_all() (行33)
       - get_all_names() (行45)
       ... 还有 4 项

  📄 quality.py
     可测试项: 28
       - QualityDAO.create (行64)
       - QualityDAO.confirm_order_completion (行135)
       - QualityDAO.update (行186)
       - QualityDAO.get_by_order (行210)
       - QualityDAO.get_all (行225)
       - QualityDAO.get_stats (行262)
       - QualityDAO.delete (行296)
       - QualityDAO.get_order_processes (行307)
       - QualityDAO.get_production_by_order (行325)
       - QualityDAO.get_work_no_map (行343)
       ... 还有 18 项

  📄 quality_rule.py
     可测试项: 24
       - QualityRuleDAO.get_all (行19)
       - QualityRuleDAO.get_by_id (行58)
       - QualityRuleDAO.get_rules_by_process (行95)
       - QualityRuleDAO.create (行107)
       - QualityRuleDAO.update (行147)
       - QualityRuleDAO.delete (行185)
       - QualityRuleDAO.get_rule_items (行205)
       - QualityRuleDAO.save_rule_items (行236)
       - QualityRuleDAO.add_rule_item (行267)
       - QualityRuleDAO.get_matching_rules (行291)
       ... 还有 14 项

  📄 shipment.py
     可测试项: 26
       - ShipmentDAO.create (行14)
       - ShipmentDAO.confirm_ship (行48)
       - ShipmentDAO.get_all (行88)
       - ShipmentDAO.get_all_shipments (行127)
       - ShipmentDAO.get_by_id (行167)
       - ShipmentDAO.get_by_shipment_no (行187)
       - ShipmentDAO.save_tracking (行207)
       - ShipmentDAO.get_tracking_history (行230)
       - ShipmentDAO.get_latest_tracking (行264)
       - ShipmentDAO.get_all_with_latest_tracking (行270)
       ... 还有 16 项

  📄 unit.py
     可测试项: 14
       - UnitDAO.get_all (行13)
       - UnitDAO.get_by_category (行26)
       - UnitDAO.get_by_code (行39)
       - UnitDAO.add (行54)
       - UnitDAO.remove (行88)
       - UnitDAO.update (行113)
       - UnitDAO.get_categories (行147)
       - get_all() (行13)
       - get_by_category() (行26)
       - get_by_code() (行39)
       ... 还有 4 项

  📄 __init__.py
     可测试项: 0


================================================================================
模块: SERVICES
================================================================================

文件数: 9
可测试项总数: 105

详细文件分析:

  📄 audit_service.py
     可测试项: 13
       - AuditService.log (行60)
       - AuditService.get_logs (行125)
       - AuditService.get_entity_history (行188)
       - AuditService.get_operator_logs (行193)
       - AuditService.get_recent_logs (行198)
       - AuditService.clear_old_logs (行204)
       - audit_log() (行226)
       - log() (行60)
       - get_logs() (行125)
       - get_entity_history() (行188)
       ... 还有 3 项

  📄 base_service.py
     可测试项: 2
       - BaseService.transaction (行45)
       - transaction() (行45)

  📄 inventory_notifier.py
     可测试项: 18
       - set_http_factory() (行28)
       - InventoryNotifier.init (行66)
       - InventoryNotifier.notify_material_prepared (行120)
       - InventoryNotifier.notify_order_started (行150)
       - InventoryNotifier.check_connection (行176)
       - InventoryNotifier.wait_for_response (行183)
       - InventoryNotifier.get_response (行219)
       - InventoryNotifier.is_enabled (行235)
       - get_inventory_notifier() (行243)
       - notify_material_prepared() (行252)
       ... 还有 8 项

  📄 inventory_sync.py
     可测试项: 4
       - InventorySyncService.get_unified_stock (行17)
       - InventorySyncService.check_duplicate_databases (行20)
       - get_unified_stock() (行17)
       - check_duplicate_databases() (行20)

  📄 order_service.py
     可测试项: 16
       - OrderService.get_instance (行77)
       - OrderService.create_order (行90)
       - OrderService.update_order (行95)
       - OrderService.change_status (行100)
       - OrderService.delete_order (行105)
       - OrderService.get_order_detail (行110)
       - OrderService.get_order_history (行115)
       - OrderService.search_orders (行120)
       - get_instance() (行77)
       - create_order() (行90)
       ... 还有 6 项

  📄 process_service.py
     可测试项: 28
       - ProcessService.get_records_by_production (行30)
       - ProcessService.get_record_by_id (行41)
       - ProcessService.update_record (行52)
       - ProcessService.insert_record (行64)
       - ProcessService.delete_record (行75)
       - ProcessService.report_progress (行86)
       - ProcessService.reorder_processes (行157)
       - ProcessService.apply_template (行169)
       - ProcessService.update_planned_qty (行189)
       - ProcessService.update_remark (行201)
       ... 还有 18 项

  📄 schedule_dispatch_service.py
     可测试项: 10
       - ScheduleDispatchService.publish_schedule (行51)
       - ScheduleDispatchService.get_dead_letters (行362)
       - ScheduleDispatchService.retry_dead_letter (行387)
       - ScheduleDispatchService.start_queue_recovery (行466)
       - ScheduleDispatchService.handle_schedule_callback (行480)
       - publish_schedule() (行51)
       - get_dead_letters() (行362)
       - retry_dead_letter() (行387)
       - start_queue_recovery() (行466)
       - handle_schedule_callback() (行480)

  📄 wechat_report_service.py
     可测试项: 14
       - WeChatReportService.publish_task_to_operator (行102)
       - WeChatReportService.process_callback (行287)
       - WeChatReportService.sync_report_status (行430)
       - WeChatReportService.batch_update_status (行492)
       - WeChatReportService.update_operator (行529)
       - WeChatReportService.get_dead_tasks (行576)
       - WeChatReportService.retry_dead_task (行599)
       - publish_task_to_operator() (行102)
       - process_callback() (行287)
       - sync_report_status() (行430)
       ... 还有 4 项

  📄 __init__.py
     可测试项: 0


================================================================================
模块: UTILS
================================================================================

文件数: 30
可测试项总数: 354

详细文件分析:

  📄 app_init.py
     可测试项: 6
       - preload_dict_data() (行13)
       - get_material_densities() (行52)
       - archive_old_orders() (行65)
       - cleanup_old_logs() (行114)
       - get_db_stats() (行159)
       - init_app_cache() (行192)

  📄 auto_refresh_mixin.py
     可测试项: 0

  📄 auto_schema.py
     可测试项: 6
       - auto_ensure_schema() (行151)
       - clear_schema_cache() (行239)
       - SafeCursor.execute (行299)
       - SafeCursor.executemany (行313)
       - execute() (行299)
       - executemany() (行313)

  📄 backup_manager.py
     可测试项: 12
       - BackupManager.get_config (行55)
       - BackupManager.update_config (行59)
       - BackupManager.start_backup_service (行67)
       - BackupManager.perform_backup (行102)
       - BackupManager.restore_from_backup (行142)
       - BackupManager.get_backup_files (行156)
       - get_config() (行55)
       - update_config() (行59)
       - start_backup_service() (行67)
       - perform_backup() (行102)
       ... 还有 2 项

  📄 copyable_widgets.py
     可测试项: 10
       - CopyableLabel.config (行126)
       - CopyableLabel.configure (行134)
       - CopyableLabel.set_text (行138)
       - CopyableLabel.get_text (行143)
       - CopyableLabel.text_widget (行148)
       - config() (行126)
       - configure() (行134)
       - set_text() (行138)
       - get_text() (行143)
       - text_widget() (行148)

  📄 custom_types.py
     可测试项: 24
       - get_product_types() (行18)
       - add_product_type() (行35)
       - set_product_flow_type() (行54)
       - sync_product_flow_map() (行64)
       - remove_product_type() (行73)
       - get_materials() (行95)
       - add_material() (行107)
       - remove_material() (行130)
       - get_material_density() (行147)
       - set_material_density() (行161)
       ... 还有 14 项

  📄 dao_patches.py
     可测试项: 15
       - OptimizedOrderDAO.get_all (行18)
       - OptimizedOrderDAO.get_kanban_stats (行76)
       - OptimizedOrderDAO.invalidate_stats (行125)
       - OptimizedProductionDAO.get_by_order_ids (行134)
       - OptimizedQualityDAO.get_all (行179)
       - OptimizedShipmentDAO.get_all (行235)
       - OptimizedProcessDAO.get_by_production (行291)
       - apply_dao_patches() (行327)
       - get_all() (行18)
       - get_kanban_stats() (行76)
       ... 还有 5 项

  📄 data_type_contract.py
     可测试项: 6
       - get_process_names_set() (行50)
       - get_process_code_to_name() (行63)
       - classify_pkg() (行187)
       - classify_payloads() (行280)
       - group_by_card() (行300)
       - get_flow_step_names_set() (行348)

  📄 db_utils.py
     可测试项: 6
       - get_mysql_password() (行15)
       - get_db_config() (行31)
       - create_db_connection() (行48)
       - create_remote_db_connection() (行76)
       - with_db_connection() (行122)
       - wrapper() (行133)

  📄 excel_utils.py
     可测试项: 16
       - ExcelExporter.export_orders (行69)
       - ExcelExporter.export_inventory (行124)
       - ExcelExporter.export_bom (行161)
       - ExcelExporter.export_material_prep (行200)
       - ExcelImporter.import_orders (行243)
       - ExcelImporter.import_inventory (行307)
       - ExcelImporter.import_bom (行370)
       - get_template_path() (行431)
       - create_template() (行438)
       - export_orders() (行69)
       ... 还有 6 项

  📄 expected_zh.py
     可测试项: 4
       - get_expected_status_zh() (行116)
       - get_expected_datatype_zh() (行124)
       - get_expected_priority_zh() (行131)
       - refresh_from_frontend() (行136)

  📄 helpers.py
     可测试项: 9
       - validate_number() (行9)
       - validate_date() (行26)
       - format_date() (行42)
       - days_until() (行53)
       - get_urgency_color() (行64)
       - format_amount() (行77)
       - format_spec() (行84)
       - truncate_text() (行102)
       - get() (行88)

  📄 i18n_zh.py
     可测试项: 2
       - translate() (行221)
       - translate_payload() (行239)

  📄 logistics_companies.py
     可测试项: 4
       - get_all_companies() (行54)
       - add_company() (行60)
       - remove_company() (行79)
       - get_custom_companies() (行93)

  📄 logistics_tracker.py
     可测试项: 68
       - get_company_code() (行51)
       - get_company_name_by_code() (行59)
       - state_text() (行67)
       - TrackingConfig.set_config_file (行85)
       - TrackingConfig.load (行121)
       - TrackingConfig.save (行145)
       - TrackingConfig.platform (行157)
       - TrackingConfig.platform (行161)
       - TrackingConfig.kuaidi100_customer (行165)
       - TrackingConfig.kuaidi100_customer (行169)
       ... 还有 58 项

  📄 log_cleanup.py
     可测试项: 1
       - cleanup_expired_logs() (行15)

  📄 log_scheduler.py
     可测试项: 6
       - LogCleanupScheduler.start (行38)
       - LogCleanupScheduler.stop (行46)
       - start_log_cleanup_scheduler() (行56)
       - stop_log_cleanup_scheduler() (行60)
       - start() (行38)
       - stop() (行46)

  📄 material_calculator.py
     可测试项: 19
       - safe_eval_formula() (行22)
       - tokenize() (行40)
       - evaluate() (行57)
       - MaterialCalculator.calculate_material_types (行104)
       - MaterialCalculator.get_materials_by_category (行261)
       - MaterialCalculator.preview_calculation (行281)
       - MaterialCalculator.get_available_spec_fields (行294)
       - MaterialCalculator.get_available_qty_fields (行315)
       - MaterialCalculator.get_material_params_for_product (行329)
       - MaterialCalculator.format_material_display (行342)
       ... 还有 9 项

  📄 material_templates.py
     可测试项: 6
       - get_all_templates() (行15)
       - get_template() (行36)
       - save_template() (行56)
       - delete_template() (行87)
       - rename_template() (行98)
       - get_template_names() (行111)

  📄 op_logger.py
     可测试项: 7
       - log() (行15)
       - log_step() (行25)
       - log_calc() (行35)
       - log_match() (行43)
       - log_sql() (行54)
       - log_error() (行64)
       - log_ui() (行71)

  📄 order_templates.py
     可测试项: 16
       - get_surface_field() (行70)
       - get_common_fields() (行87)
       - get_remark_fields() (行100)
       - get_template_names() (行120)
       - get_template() (行138)
       - save_template() (行156)
       - rename_template() (行178)
       - delete_template() (行192)
       - get_custom_params() (行208)
       - get_custom_material_params() (行226)
       ... 还有 6 项

  📄 pagination.py
     可测试项: 33
       - CacheItem.is_expired (行19)
       - MemoryCache.get (行29)
       - MemoryCache.set (行40)
       - MemoryCache.delete (行45)
       - MemoryCache.clear (行51)
       - MemoryCache.cleanup_expired (行56)
       - cached() (行69)
       - get_cache() (行89)
       - set_cache() (行93)
       - invalidate_cache() (行97)
       ... 还有 23 项

  📄 password_hasher.py
     可测试项: 4
       - hash_password() (行10)
       - verify_password() (行33)
       - generate_random_password() (行51)
       - is_password_strong() (行70)

  📄 process_templates.py
     可测试项: 5
       - get_all_process_templates() (行14)
       - save_process_templates() (行29)
       - add_process_template() (行52)
       - delete_process_template() (行73)
       - rename_process_template() (行84)

  📄 query_cache.py
     可测试项: 8
       - get_cached_result() (行36)
       - set_cached_result() (行49)
       - clear_cache() (行76)
       - invalidate_cache() (行81)
       - get_cache_stats() (行91)
       - invalidate_on_update() (行102)
       - decorator() (行112)
       - wrapper() (行113)

  📄 settings_manager.py
     可测试项: 20
       - SettingsManager.save_settings (行79)
       - SettingsManager.get_color (行89)
       - SettingsManager.set_color (行93)
       - SettingsManager.get_font_size (行100)
       - SettingsManager.set_font_size (行104)
       - SettingsManager.get_font_family (行111)
       - SettingsManager.set_font_family (行115)
       - SettingsManager.reset_to_default (行120)
       - SettingsManager.get_all_colors (行126)
       - SettingsManager.get_all_fonts (行130)
       ... 还有 10 项

  📄 trace.py
     可测试项: 12
       - get_trace_id() (行56)
       - get_span_id() (行63)
       - set_trace_id() (行70)
       - new_span() (行75)
       - init_trace_middleware() (行83)
       - trace_headers() (行113)
       - traced_request() (行127)
       - TraceFilter.filter (行146)
       - traced_logger() (行152)
       - with_trace() (行206)
       ... 还有 2 项

  📄 validators.py
     可测试项: 24
       - CommonValidators.required (行18)
       - CommonValidators.length (行25)
       - CommonValidators.range (行37)
       - CommonValidators.pattern (行51)
       - CommonValidators.choices (行58)
       - CommonValidators.date_format (行65)
       - OrderValidator.validate_create (行78)
       - OrderValidator.validate_update (行110)
       - ProcessValidator.validate_report (行128)
       - InventoryValidator.validate_adjustment (行160)
       ... 还有 14 项

  📄 window_manager.py
     可测试项: 5
       - get_window_config_path() (行11)
       - load_window_size() (行16)
       - save_window_size() (行29)
       - setup_resizable_window() (行45)
       - on_resize() (行67)

  📄 __init__.py
     可测试项: 0


================================================================================
汇总
================================================================================

core: 194 项

models: 416 项

services: 105 项

utils: 354 项

总计需要测试的项: 1069

现有测试函数: 2653 个


================================================================================
覆盖率提升估算
================================================================================

目标覆盖率: 70%
需要覆盖的项: 748
需要补充的测试: 534 (估算)