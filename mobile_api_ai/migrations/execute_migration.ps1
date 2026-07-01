# Database Migration Execution Script (PowerShell direct connect MySQL)
# Replaces Python script (Python subprocess crashes in sandbox)

param(
    [switch]$DryRun = $false,
    [switch]$Rollback = $false
)

$ErrorActionPreference = 'Stop'

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

if (-not $env:MYSQL_HOST) { $env:MYSQL_HOST = "localhost" }
if (-not $env:MYSQL_PORT) { $env:MYSQL_PORT = "3306" }
if (-not $env:MYSQL_USER) { $env:MYSQL_USER = "root" }
if (-not $env:MYSQL_DATABASE) { $env:MYSQL_DATABASE = "container_center" }

Write-Host "=" -NoNewline -ForegroundColor Cyan; Write-Host ("=" * 78)
Write-Host "Database Migration v3.6.1 - Prevent Task Duplicates" -ForegroundColor Cyan
if ($DryRun) { Write-Host "[Mode] DRY-RUN (check only)" -ForegroundColor Yellow }
elseif ($Rollback) { Write-Host "[Mode] ROLLBACK" -ForegroundColor Red }
else { Write-Host "[Mode] EXECUTE" -ForegroundColor Green }
Write-Host "=" -NoNewline -ForegroundColor Cyan; Write-Host ("=" * 78)
Write-Host "Connect: $($env:MYSQL_USER)@$($env:MYSQL_HOST):$($env:MYSQL_PORT)/$($env:MYSQL_DATABASE)"
Write-Host ""

# ═══════════════════════════════════════════════════════════════════════════════
# Load MySQL .NET library
# ═══════════════════════════════════════════════════════════════════════════════

# Search for MySql.Data.dll
$myDll = $null
$searchPaths = @(
    "C:\Program Files\MySQL\MySQL Server*\bin",
    "C:\Program Files (x86)\MySQL\MySQL Server*\bin",
    "D:\MySQL\*\bin",
    "D:\Program Files\MySQL\*\bin",
    "$env:USERPROFILE\.nuget\packages\mysql.data\**\lib\net*\MySql.Data.dll"
)
foreach ($path in $searchPaths) {
    $found = Get-ChildItem $path -Filter "MySql.Data.dll" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $myDll = $found.FullName; break }
}

# Try to load from project directory
if (-not $myDll) {
    $candidates = @(
        "$PSScriptRoot\..\storage\mysql_storage.py",
        "$PSScriptRoot\..\venv\Lib\site-packages\pymysql"
    )
}

if ($myDll) {
    Write-Host "[INFO] Loading MySql.Data.dll from: $myDll"
    Add-Type -Path $myDll
} else {
    # Try default (if .NET Framework has it)
    try {
        Add-Type -AssemblyName MySql.Data -ErrorAction Stop
        Write-Host "[INFO] Loaded MySql.Data from GAC"
    } catch {
        Write-Host "[ERROR] MySql.Data.dll not found!" -ForegroundColor Red
        Write-Host "Please install MySQL Connector/NET: https://dev.mysql.com/downloads/connector/net/"
        Write-Host "Or use the Python script: python migrations/0620_prevent_task_duplicates.py"
        exit 1
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# Connect to MySQL
# ═══════════════════════════════════════════════════════════════════════════════

$connStr = "Server=$($env:MYSQL_HOST);Port=$($env:MYSQL_PORT);User Id=$($env:MYSQL_USER);Password=$($env:MYSQL_PASSWORD);Database=$($env:MYSQL_DATABASE);SslMode=None;Pooling=false;"

try {
    $conn = New-Object System.Data.MySqlClient.MySqlConnection($connStr)
    $conn.Open()
    Write-Host "[OK] MySQL connected" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] MySQL connection failed: $_" -ForegroundColor Red
    exit 1
}

function Exec-Sql {
    param([string]$Sql)
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $Sql
    return $cmd.ExecuteNonQuery()
}

function Query-Scalar {
    param([string]$Sql)
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = $Sql
    return $cmd.ExecuteScalar()
}

function Test-Table {
    param([string]$TableName)
    $sql = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='$TableName'"
    return ([int](Query-Scalar $sql)) -gt 0
}

function Test-Index {
    param([string]$TableName, [string]$IndexName)
    $sql = "SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='$TableName' AND index_name='$IndexName'"
    return ([int](Query-Scalar $sql)) -gt 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# Migration Operations
# ═══════════════════════════════════════════════════════════════════════════════

$tables_config = @(
    @{ Name = "process_sub_steps"; KeyFields = @("order_no", "step_name"); IndexName = "uk_active_task"; TimeField = "created_at"; ActiveStatuses = @("pending", "in_progress", "distributed") },
    @{ Name = "quality_records";   KeyFields = @("order_no", "process_name"); IndexName = "uk_active_quality"; TimeField = "record_date"; ActiveStatuses = @("pending", "in_progress") },
    @{ Name = "material_records";  KeyFields = @("order_no", "material_name"); IndexName = "uk_active_material"; TimeField = "created_at"; ActiveStatuses = @("pending", "in_progress") },
    @{ Name = "outsource_records"; KeyFields = @("order_no", "title"); IndexName = "uk_active_outsource"; TimeField = "created_at"; ActiveStatuses = @("pending", "in_progress") }
)

if ($Rollback) {
    Write-Host ""
    Write-Host "Rolling back unique indexes..." -ForegroundColor Red
    foreach ($tc in $tables_config) {
        if (-not (Test-Table $tc.Name)) { continue }
        if (-not (Test-Index $tc.Name $tc.IndexName)) {
            Write-Host "  $($tc.Name).$($tc.IndexName) not exists, skipping"
            continue
        }
        if (-not $DryRun) {
            Exec-Sql "ALTER TABLE $($tc.Name) DROP INDEX $($tc.IndexName)"
        }
        Write-Host "  [OK] $($tc.Name).$($tc.IndexName) dropped" -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "[OK] Rollback complete" -ForegroundColor Green
} else {
    $stepNum = 0
    foreach ($tc in $tables_config) {
        $stepNum++
        Write-Host ""
        Write-Host "[Step $stepNum] $($tc.Name) dedup constraint" -ForegroundColor Cyan

        if (-not (Test-Table $tc.Name)) {
            Write-Host "  [WARN] Table $($tc.Name) not exists, skipping" -ForegroundColor Yellow
            continue
        }

        $joinFields = ($tc.KeyFields | ForEach-Object { "p1.$_ = p2.$_" }) -join " AND "
        $statusList = "'" + ($tc.ActiveStatuses -join "','") + "'"

        # Clean duplicates
        $deleteSql = @"
DELETE p1 FROM $($tc.Name) p1
INNER JOIN $($tc.Name) p2
WHERE $joinFields
  AND p1.status IN ($statusList)
  AND p2.status IN ($statusList)
  AND p1.$($tc.TimeField) > p2.$($tc.TimeField)
"@

        if (-not $DryRun) {
            $deleted = Exec-Sql $deleteSql
            Write-Host "  Cleaned duplicates: $deleted rows"
        } else {
            $countSql = @"
SELECT COUNT(*) FROM $($tc.Name) p1
INNER JOIN $($tc.Name) p2
WHERE $joinFields
  AND p1.status IN ($statusList)
  AND p2.status IN ($statusList)
  AND p1.$($tc.TimeField) > p2.$($tc.TimeField)
"@
            $willDelete = [int](Query-Scalar $countSql)
            Write-Host "  [DRY-RUN] Will clean: $willDelete duplicate rows"
        }

        # Add index
        if (Test-Index $tc.Name $tc.IndexName) {
            Write-Host "  Index $($tc.IndexName) already exists, skipping"
        } else {
            $idxFields = ($tc.KeyFields + "status") -join ", "
            if ($DryRun) {
                Write-Host "  [DRY-RUN] Will create index $($tc.IndexName)"
            } else {
                Exec-Sql "ALTER TABLE $($tc.Name) ADD UNIQUE INDEX $($tc.IndexName) ($idxFields)"
                Write-Host "  [OK] Index $($tc.IndexName) created" -ForegroundColor Green
            }
        }
    }

    # Verification
    Write-Host ""
    Write-Host "[Verify] Migration result" -ForegroundColor Cyan
    foreach ($tc in $tables_config) {
        if (-not (Test-Table $tc.Name)) { continue }
        if (Test-Index $tc.Name $tc.IndexName) {
            Write-Host "  [OK] $($tc.Name).$($tc.IndexName) active" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] $($tc.Name).$($tc.IndexName) missing" -ForegroundColor Yellow
        }
    }

    Write-Host ""
    Write-Host "=" -NoNewline -ForegroundColor Cyan; Write-Host ("=" * 78)
    if ($DryRun) {
        Write-Host "[DRY-RUN] Complete (no changes)" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] v3.6.1 anti-duplicate constraints added" -ForegroundColor Green
    }
    Write-Host "=" -NoNewline -ForegroundColor Cyan; Write-Host ("=" * 78)
}

$conn.Close()