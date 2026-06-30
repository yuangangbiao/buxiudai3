-- 表结构备份 2026-05-03 22:46:25
-- 表名: process_calc_rules

CREATE TABLE `process_calc_rules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `process_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `product_types_json` text COLLATE utf8mb4_unicode_ci,
  `condition_expr` text COLLATE utf8mb4_unicode_ci,
  `planned_qty_formula` text COLLATE utf8mb4_unicode_ci,
  `priority` int DEFAULT '5',
  `enabled` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
