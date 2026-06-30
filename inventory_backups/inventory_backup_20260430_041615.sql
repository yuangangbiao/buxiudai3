-- 库存管理系统数据库备份
-- 数据库: inventory_management_db
-- 备份时间: 20260430_041615
-- 版本: V3.0 MySQL版


-- 表结构: categories
DROP TABLE IF EXISTS `categories`;
categories;

-- 数据: categories (26 rows)
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (1, 'CAT-001', '螺栓螺母', '紧固件', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (2, 'CAT-002', '螺钉', '紧固件', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (3, 'CAT-003', '垫片', '紧固件', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (4, 'CAT-004', '铆钉', '紧固件', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (5, 'CAT-005', '合页铰链', '五金配件', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (6, 'CAT-006', '门锁门吸', '五金配件', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (7, 'CAT-007', '拉手把手', '五金配件', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (8, 'CAT-008', '导轨滑道', '五金配件', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (9, 'CAT-009', '电线电缆', '电气五金', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (10, 'CAT-010', '开关插座', '电气五金', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (11, 'CAT-011', '水管管件', '水暖五金', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (12, 'CAT-012', '阀门', '水暖五金', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (13, 'CAT-013', '钻头刀具', '工具刀具', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (14, 'CAT-014', '手动工具', '工具刀具', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (15, 'CAT-015', '砂轮砂纸', '磨具', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (16, 'CAT-016', '焊接材料', '焊接', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (17, 'CAT-017', '密封胶', '密封防水', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (18, 'CAT-018', '油漆涂料', '表面处理', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (19, 'CAT-019', '钢材型材', '金属材料', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (20, 'CAT-020', '铝材', '金属材料', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (21, 'CAT-021', '气动工具', '工具刀具', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (22, 'CAT-022', '电动工具', '工具刀具', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (23, 'CAT-023', '安全防护', '劳保用品', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (24, 'CAT-024', '搬运工具', '工具刀具', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (25, 'CAT-025', '照明器材', '电气五金', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `categories` (`id`, `code`, `name`, `parent_name`, `remark`, `status`, `created_at`, `updated_at`) VALUES (26, 'CAT-026', '仪表量具', '测量工具', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');


-- 表结构: inventory
DROP TABLE IF EXISTS `inventory`;
inventory;

-- 数据: inventory (8 rows)
INSERT INTO `inventory` (`id`, `product_id`, `warehouse_id`, `initial_qty`, `inbound_qty`, `outbound_qty`, `current_qty`, `safety_stock`, `max_stock`, `unit_price`, `last_inbound_at`, `last_outbound_at`, `remark`, `created_at`, `updated_at`) VALUES (18, 58, 1, '100.00', '20.00', '10.00', '110.00', '10.00', '200.00', '25.00', '2026-04-29 22:40:51', '2026-04-29 22:40:51', NULL, '2026-04-29 22:23:03', '2026-04-29 22:40:51');
INSERT INTO `inventory` (`id`, `product_id`, `warehouse_id`, `initial_qty`, `inbound_qty`, `outbound_qty`, `current_qty`, `safety_stock`, `max_stock`, `unit_price`, `last_inbound_at`, `last_outbound_at`, `remark`, `created_at`, `updated_at`) VALUES (19, 59, 1, '50.00', '0.00', '0.00', '50.00', '10.00', '100.00', '42.00', NULL, NULL, NULL, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `inventory` (`id`, `product_id`, `warehouse_id`, `initial_qty`, `inbound_qty`, `outbound_qty`, `current_qty`, `safety_stock`, `max_stock`, `unit_price`, `last_inbound_at`, `last_outbound_at`, `remark`, `created_at`, `updated_at`) VALUES (20, 60, 1, '200.00', '0.00', '0.00', '200.00', '20.00', '500.00', '12.00', NULL, NULL, NULL, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `inventory` (`id`, `product_id`, `warehouse_id`, `initial_qty`, `inbound_qty`, `outbound_qty`, `current_qty`, `safety_stock`, `max_stock`, `unit_price`, `last_inbound_at`, `last_outbound_at`, `remark`, `created_at`, `updated_at`) VALUES (21, 61, 1, '80.00', '0.00', '0.00', '80.00', '15.00', '300.00', '18.50', NULL, NULL, NULL, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `inventory` (`id`, `product_id`, `warehouse_id`, `initial_qty`, `inbound_qty`, `outbound_qty`, `current_qty`, `safety_stock`, `max_stock`, `unit_price`, `last_inbound_at`, `last_outbound_at`, `remark`, `created_at`, `updated_at`) VALUES (22, 62, 1, '150.00', '0.00', '0.00', '150.00', '20.00', '400.00', '8.50', NULL, NULL, NULL, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `inventory` (`id`, `product_id`, `warehouse_id`, `initial_qty`, `inbound_qty`, `outbound_qty`, `current_qty`, `safety_stock`, `max_stock`, `unit_price`, `last_inbound_at`, `last_outbound_at`, `remark`, `created_at`, `updated_at`) VALUES (23, 63, 1, '100.00', '0.00', '0.00', '100.00', '10.00', '300.00', '15.00', NULL, NULL, NULL, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `inventory` (`id`, `product_id`, `warehouse_id`, `initial_qty`, `inbound_qty`, `outbound_qty`, `current_qty`, `safety_stock`, `max_stock`, `unit_price`, `last_inbound_at`, `last_outbound_at`, `remark`, `created_at`, `updated_at`) VALUES (24, 64, 1, '60.00', '0.00', '0.00', '60.00', '10.00', '150.00', '22.00', NULL, NULL, NULL, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `inventory` (`id`, `product_id`, `warehouse_id`, `initial_qty`, `inbound_qty`, `outbound_qty`, `current_qty`, `safety_stock`, `max_stock`, `unit_price`, `last_inbound_at`, `last_outbound_at`, `remark`, `created_at`, `updated_at`) VALUES (25, 65, 1, '120.00', '0.00', '0.00', '120.00', '15.00', '350.00', '18.00', NULL, NULL, NULL, '2026-04-29 22:23:03', '2026-04-29 22:23:03');


-- 表结构: inventory_transactions
DROP TABLE IF EXISTS `inventory_transactions`;
inventory_transactions;

-- 数据: inventory_transactions (4 rows)
INSERT INTO `inventory_transactions` (`id`, `trans_no`, `trans_type`, `product_id`, `warehouse_id`, `from_warehouse_id`, `to_warehouse_id`, `qty`, `unit_price`, `total_amount`, `supplier_id`, `order_no`, `trans_date`, `operator`, `remark`, `created_at`) VALUES (3, 'IN20260429223912', 'inbound', 58, 1, NULL, NULL, '10.00', '0.00', '0.00', NULL, NULL, '2026-04-29', '测试员', '测试入库', '2026-04-29 22:39:12');
INSERT INTO `inventory_transactions` (`id`, `trans_no`, `trans_type`, `product_id`, `warehouse_id`, `from_warehouse_id`, `to_warehouse_id`, `qty`, `unit_price`, `total_amount`, `supplier_id`, `order_no`, `trans_date`, `operator`, `remark`, `created_at`) VALUES (4, 'OUT20260429223912', 'outbound', 58, 1, NULL, NULL, '5.00', '0.00', '0.00', NULL, NULL, '2026-04-29', '测试员', '测试出库', '2026-04-29 22:39:12');
INSERT INTO `inventory_transactions` (`id`, `trans_no`, `trans_type`, `product_id`, `warehouse_id`, `from_warehouse_id`, `to_warehouse_id`, `qty`, `unit_price`, `total_amount`, `supplier_id`, `order_no`, `trans_date`, `operator`, `remark`, `created_at`) VALUES (6, 'IN20260429224051', 'inbound', 58, 1, NULL, NULL, '10.00', '0.00', '0.00', NULL, NULL, '2026-04-29', '测试员', '测试入库', '2026-04-29 22:40:51');
INSERT INTO `inventory_transactions` (`id`, `trans_no`, `trans_type`, `product_id`, `warehouse_id`, `from_warehouse_id`, `to_warehouse_id`, `qty`, `unit_price`, `total_amount`, `supplier_id`, `order_no`, `trans_date`, `operator`, `remark`, `created_at`) VALUES (7, 'OUT20260429224051', 'outbound', 58, 1, NULL, NULL, '5.00', '0.00', '0.00', NULL, NULL, '2026-04-29', '测试员', '测试出库', '2026-04-29 22:40:51');


-- 表结构: print_templates
DROP TABLE IF EXISTS `print_templates`;
print_templates;



-- 表结构: products
DROP TABLE IF EXISTS `products`;
products;

-- 数据: products (8 rows)
INSERT INTO `products` (`id`, `sku`, `name`, `spec`, `unit`, `category_id`, `price`, `remark`, `status`, `created_at`, `updated_at`) VALUES (58, 'SKU-0001', 'M8×50镀锌六角螺栓', 'M8×50', '包(100个)', 1, '25.00', NULL, 1, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `products` (`id`, `sku`, `name`, `spec`, `unit`, `category_id`, `price`, `remark`, `status`, `created_at`, `updated_at`) VALUES (59, 'SKU-0002', 'M10×60不锈钢螺栓', 'M10×60', '包(50个)', 1, '42.00', NULL, 1, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `products` (`id`, `sku`, `name`, `spec`, `unit`, `category_id`, `price`, `remark`, `status`, `created_at`, `updated_at`) VALUES (60, 'SKU-0003', 'M6平垫片镀锌', 'M6', '袋(200个)', 3, '12.00', NULL, 1, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `products` (`id`, `sku`, `name`, `spec`, `unit`, `category_id`, `price`, `remark`, `status`, `created_at`, `updated_at`) VALUES (61, 'SKU-0004', '304不锈钢弹垫M8', 'M8', '袋(100个)', 3, '18.50', NULL, 1, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `products` (`id`, `sku`, `name`, `spec`, `unit`, `category_id`, `price`, `remark`, `status`, `created_at`, `updated_at`) VALUES (62, 'SKU-0005', 'M5×20十字沉头螺钉', 'M5×20', '袋(200个)', 2, '8.50', NULL, 1, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `products` (`id`, `sku`, `name`, `spec`, `unit`, `category_id`, `price`, `remark`, `status`, `created_at`, `updated_at`) VALUES (63, 'SKU-0006', '4×20自攻螺钉镀锌', '4×20', '盒(500个)', 2, '15.00', NULL, 1, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `products` (`id`, `sku`, `name`, `spec`, `unit`, `category_id`, `price`, `remark`, `status`, `created_at`, `updated_at`) VALUES (64, 'SKU-0007', 'M6×16内六角螺栓', 'M6×16', '包(100个)', 1, '22.00', NULL, 1, '2026-04-29 22:23:03', '2026-04-29 22:23:03');
INSERT INTO `products` (`id`, `sku`, `name`, `spec`, `unit`, `category_id`, `price`, `remark`, `status`, `created_at`, `updated_at`) VALUES (65, 'SKU-0008', '4.8×19拉铆钉铝制', '4.8×19', '盒(500个)', 4, '18.00', NULL, 1, '2026-04-29 22:23:03', '2026-04-29 22:23:03');


-- 表结构: suppliers
DROP TABLE IF EXISTS `suppliers`;
suppliers;

-- 数据: suppliers (5 rows)
INSERT INTO `suppliers` (`id`, `code`, `name`, `contact`, `phone`, `address`, `main_products`, `payment_days`, `grade`, `remark`, `status`, `created_at`, `updated_at`) VALUES (1, 'SUP-001', '华南五金制品有限公司', '张经理', '13800138001', '广东省佛山市南海区', '螺栓螺母、垫片', 30, 'A', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `suppliers` (`id`, `code`, `name`, `contact`, `phone`, `address`, `main_products`, `payment_days`, `grade`, `remark`, `status`, `created_at`, `updated_at`) VALUES (2, 'SUP-002', '北京精诚五金批发', '李总', '13900139002', '北京市丰台区', '工具刀具、电气', 15, 'B', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `suppliers` (`id`, `code`, `name`, `contact`, `phone`, `address`, `main_products`, `payment_days`, `grade`, `remark`, `status`, `created_at`, `updated_at`) VALUES (3, 'SUP-003', '上海泰达管件有限公司', '王工', '13700137003', '上海市闵行区', '水管管件、阀门', 30, 'A', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `suppliers` (`id`, `code`, `name`, `contact`, `phone`, `address`, `main_products`, `payment_days`, `grade`, `remark`, `status`, `created_at`, `updated_at`) VALUES (4, 'SUP-004', '浙江新兴紧固件', '陈老板', '13600136004', '浙江省温州市', '螺钉铆钉', 45, 'A+', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `suppliers` (`id`, `code`, `name`, `contact`, `phone`, `address`, `main_products`, `payment_days`, `grade`, `remark`, `status`, `created_at`, `updated_at`) VALUES (5, 'SUP-005', '广州市百利钢材行', '刘总', '13500135005', '广州市越秀区', '钢材型材铝材', 60, 'B', NULL, 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');


-- 表结构: warehouses
DROP TABLE IF EXISTS `warehouses`;
warehouses;

-- 数据: warehouses (4 rows)
INSERT INTO `warehouses` (`id`, `code`, `name`, `location`, `remark`, `status`, `created_at`, `updated_at`) VALUES (1, 'WH-001', '1号仓', '主仓库A区', '', 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `warehouses` (`id`, `code`, `name`, `location`, `remark`, `status`, `created_at`, `updated_at`) VALUES (2, 'WH-002', '2号仓', '主仓库B区', '', 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `warehouses` (`id`, `code`, `name`, `location`, `remark`, `status`, `created_at`, `updated_at`) VALUES (3, 'WH-003', '3号仓', '原材料仓库', '', 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');
INSERT INTO `warehouses` (`id`, `code`, `name`, `location`, `remark`, `status`, `created_at`, `updated_at`) VALUES (4, 'WH-004', '4号仓', '成品仓库', '', 1, '2026-04-29 21:03:44', '2026-04-29 21:03:44');

