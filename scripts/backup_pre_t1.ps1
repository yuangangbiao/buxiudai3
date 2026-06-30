# T1 备份脚本
# 用法：powershell -ExecutionPolicy Bypass -File scripts/backup_pre_t1.ps1
#
# 备份 container_center 库的关键表
# 输出：backups/t1_backup_<时间戳>/ 目录

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$base_dir = Split-Path -Parent $PSScriptRoot
$backup_dir = Join-Path $base_dir "backups\t1_backup_$timestamp"

if (-not (Test-Path $backup_dir)) {
    New-Item -ItemType Directory -Force -Path $backup_dir | Out-Null
}

Write-Host "==== T1 Backup ===="
Write-Host "Dir: $backup_dir"

# 读取 .env
$env_file = Join-Path $base_dir ".env"
if (Test-Path $env_file) {
    Get-Content $env_file | ForEach-Object {
        if ($_ -match "^([A-Z_][A-Z0-9_]*)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
        }
    }
}

$mysql_host = if ($env:MYSQL_HOST) { $env:MYSQL_HOST } else { "localhost" }
$mysql_port = if ($env:MYSQL_PORT) { $env:MYSQL_PORT } else { "3306" }
$mysql_user = if ($env:MYSQL_USER) { $env:MYSQL_USER } else { "root" }
$mysql_pwd  = if ($env:MYSQL_PASSWORD) { $env:MYSQL_PASSWORD } else { "" }
$mysql_db   = if ($env:MYSQL_DATABASE) { $env:MYSQL_DATABASE } else { "container_center" }

Write-Host "Host: $mysql_host  Port: $mysql_port  DB: $mysql_db"

# mysqldump
$dump_path = Join-Path $backup_dir "mysql_dump.sql"
$dump_tool = Get-Command mysqldump -ErrorAction SilentlyContinue
if ($dump_tool) {
    Write-Host "Running mysqldump ..."
    $env:MYSQL_PWD = $mysql_pwd
    $dump_cmd = "mysqldump -h $mysql_host -P $mysql_port -u $mysql_user --single-transaction --routines --triggers $mysql_db"
    cmd /c "$dump_cmd > `"$dump_path`" 2>&1"
    if ($LASTEXITCODE -eq 0) {
        $size = (Get-Item $dump_path).Length
        Write-Host "[OK] $dump_path ($size bytes)"
    } else {
        Write-Host "[FAIL] mysqldump exit $LASTEXITCODE"
        exit 1
    }
} else {
    Write-Host "[WARN] mysqldump not in PATH, skipped"
}

# SQLite
$sqlite_src = Join-Path $base_dir "mobile_api_ai\wechat_container.db"
$sqlite_dst = Join-Path $backup_dir "wechat_container.db"
if (Test-Path $sqlite_src) {
    Copy-Item $sqlite_src $sqlite_dst -Force
    $size = (Get-Item $sqlite_dst).Length
    Write-Host "[OK] SQLite backup ($size bytes)"
}

# Manifest
$manifest = @{
    timestamp = $timestamp
    backup_dir = $backup_dir
    mysql_host = $mysql_host
    mysql_port = $mysql_port
    mysql_db = $mysql_db
    rollback_sql = "DROP TABLE IF EXISTS container_center.work_order_history"
}
$manifest | ConvertTo-Json | Out-File (Join-Path $backup_dir "manifest.json") -Encoding utf8

Write-Host "==== Backup DONE ===="
