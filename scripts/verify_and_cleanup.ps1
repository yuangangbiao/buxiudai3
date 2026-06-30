# verify_and_cleanup.ps1

$ErrorActionPreference = 'Continue'

# --- Section 1: Check container_center.orders_local ---
Write-Host "=== 1. container_center.orders_local ===" -ForegroundColor Cyan

$connStr1 = "Server=192.168.0.107;Port=3306;Uid=root;Pwd=123456;Database=container_center;CharSet=utf8mb4"
$conn1 = New-Object MySql.Data.MySqlClient.MySqlConnection($connStr1)
try {
    $conn1.Open()
    $cmd1 = $conn1.CreateCommand()
    $cmd1.CommandText = "SHOW TABLES LIKE 'orders_local'"
    $reader1 = $cmd1.ExecuteReader()
    $t1 = $reader1.Read()
    $reader1.Close()
    Write-Host "orders_local exists: $t1"
    if ($t1) {
        $cmd2 = $conn1.CreateCommand()
        $cmd2.CommandText = "SELECT * FROM orders_local ORDER BY id DESC LIMIT 30"
        $reader2 = $cmd2.ExecuteReader()
        while ($reader2.Read()) {
            $id = $reader2["id"]
            $orderNo = $reader2["order_no"]
            $status = $reader2["status"]
            $product = $reader2["product_name"]
            $step = $reader2["current_step"]
            $synced = $reader2["_synced_at"]
            Write-Host "  [$id] order_no=$orderNo | status=$status | product=$product | step=$step | synced=$synced"
        }
        $reader2.Close()
    }
} catch {
    Write-Host "  ERROR: $_" -ForegroundColor Red
} finally {
    $conn1.Close()
}

# --- Section 2: Check steel_belt.sync_outbox ---
Write-Host ""
Write-Host "=== 2. steel_belt.sync_outbox ===" -ForegroundColor Cyan

$connStr2 = "Server=192.168.0.107;Port=3306;Uid=root;Pwd=123456;Database=steel_belt;CharSet=utf8mb4"
$conn2 = New-Object MySql.Data.MySqlClient.MySqlConnection($connStr2)
try {
    $conn2.Open()
    $cmd3 = $conn2.CreateCommand()
    $cmd3.CommandText = "SHOW TABLES LIKE 'sync_outbox'"
    $reader3 = $cmd3.ExecuteReader()
    $t2 = $reader3.Read()
    $reader3.Close()
    Write-Host "sync_outbox exists: $t2"
    if ($t2) {
        $cmd4 = $conn2.CreateCommand()
        $cmd4.CommandText = "SELECT * FROM sync_outbox ORDER BY created_at DESC LIMIT 15"
        $reader4 = $cmd4.ExecuteReader()
        while ($reader4.Read()) {
            $id = $reader4["id"]
            $eventId = $reader4["event_id"]
            $action = $reader4["action"]
            $status = $reader4["status"]
            $retry = $reader4["retry_count"]
            $created = $reader4["created_at"]
            Write-Host "  id=$id event_id=$eventId action=$action status=$status retry=$retry created=$created"
        }
        $reader4.Close()
    }
} catch {
    Write-Host "  ERROR: $_" -ForegroundColor Red
} finally {
    $conn2.Close()
}

# --- Section 3: Cleanup test data ---
Write-Host ""
Write-Host "=== 3. Cleanup test data ===" -ForegroundColor Cyan

# 3a. Delete from container_center.orders_local
Write-Host ""
Write-Host "--- orders_local cleanup ---" -ForegroundColor Yellow
$conn3 = New-Object MySql.Data.MySqlClient.MySqlConnection($connStr1)
try {
    $conn3.Open()
    $cmd5 = $conn3.CreateCommand()
    $cmd5.CommandText = "DELETE FROM orders_local WHERE order_no LIKE 'TEST-%' OR order_no LIKE 'CONFIRM-%' OR order_no LIKE 'FINAL-%' OR order_no LIKE 'STAGE-%'"
    $rows5 = $cmd5.ExecuteNonQuery()
    Write-Host "  Deleted $rows5 rows from container_center.orders_local" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: $_" -ForegroundColor Red
} finally {
    $conn3.Close()
}

# 3b. Delete from steel_belt.orders
Write-Host ""
Write-Host "--- steel_belt.orders cleanup ---" -ForegroundColor Yellow
$conn4 = New-Object MySql.Data.MySqlClient.MySqlConnection($connStr2)
try {
    $conn4.Open()
    $cmd6 = $conn4.CreateCommand()
    $cmd6.CommandText = "DELETE FROM orders WHERE order_no LIKE 'TEST-%' OR order_no LIKE 'CONFIRM-%' OR order_no LIKE 'FINAL-%' OR order_no LIKE 'STAGE-%'"
    $rows6 = $cmd6.ExecuteNonQuery()
    Write-Host "  Deleted $rows6 rows from steel_belt.orders" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: $_" -ForegroundColor Red
} finally {
    $conn4.Close()
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
