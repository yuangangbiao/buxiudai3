-- Fix production_orders unique index problem
-- Run this in MySQL command line

USE steel_belt;

-- Step 1: Check current state
SHOW INDEX FROM production_orders WHERE COLUMN_NAME = 'order_id';

-- Step 2: Create new non-unique index first
CREATE INDEX idx_prod_orders_oid ON production_orders(order_id);

-- Step 3: Drop the old unique index (this might take time if table is large)
DROP INDEX idx_production_orders_order_id ON production_orders;

-- Step 4: Rename the new index to original name
ALTER TABLE production_orders RENAME INDEX idx_prod_orders_oid TO idx_production_orders_order_id;

-- Step 5: Verify
SHOW INDEX FROM production_orders WHERE COLUMN_NAME = 'order_id';
