# Check environment variables related to safe_rm
Write-Host "=== Environment Variables ==="
$vars = @("SAFE_RM_USE_TRASH", "SAFE_RM_ALLOWED_PATH", "SAFE_RM_DENIED_PATH", "SAFE_RM_PROTECTION_FLAG", "SAFE_RM_AUTO_ADD_TEMP")
foreach ($v in $vars) {
    $val = [Environment]::GetEnvironmentVariable($v, "User")
    $val2 = [Environment]::GetEnvironmentVariable($v, "Machine")
    if ($val) { Write-Host "User  $v = $val" }
    if ($val2) { Write-Host "Machine $v = $val2" }
}
if (-not ($val -or $val2)) { Write-Host "No SAFE_RM environment variables found at user/machine level" }

Write-Host ""
Write-Host "=== PSModulePath ==="
$paths = [Environment]::GetEnvironmentVariable("PSModulePath", "Machine") -split ';'
foreach ($p in $paths) {
    if ($p -match 'trae|safe_rm|Trac|TRae') { Write-Host ">>> Found: $p" }
}

Write-Host ""
Write-Host "=== Recycle Bin Current Contents ==="
try {
    $shell = New-Object -ComObject Shell.Application
    $recycle = $shell.NameSpace(0xa)
    $items = $recycle.Items()
    $count = 0
    foreach ($item in $items) {
        $count++
        $name = $item.Name
        $path = $item.Path
        $date = $item.ModifyDate
        Write-Host "  [$count] $name | From: $path | Date: $date"
    }
    if ($count -eq 0) { Write-Host "  (Recycle bin is empty)" }
    else { Write-Host "Total: $count items" }
} catch {
    Write-Host "  Cannot access recycle bin: $_"
}

Write-Host ""
Write-Host "=== Del command check ==="
$comspec = (Get-Command del).Source
Write-Host "del command source: $comspec"

Write-Host ""
Write-Host "=== Python os.remove check ==="
try {
    $r = & python -c "import os; print(os.__name__)" 2>&1
    Write-Host "Python OK: $r"
} catch {
    Write-Host "Python check skipped"
}
