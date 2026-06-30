# Check scheduled tasks
Write-Host "=== Enabled Scheduled Tasks ==="
try {
    $tasks = Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' }
    foreach ($t in $tasks) {
        $actions = $t.Actions | ForEach-Object { $_.Execute }
        $actionsStr = ($actions -join "; ")
        Write-Host "Task: $($t.TaskName) | State: $($t.State) | Path: $($t.TaskPath) | Actions: $actionsStr"
    }
} catch {
    Write-Host "Error: $_"
}
Write-Host ""
Write-Host "=== AllUserProfile ==="
try {
    $p = [System.Environment]::GetFolderPath('ApplicationData') + '\Microsoft\Windows\PowerShell\PowerShell_startup.ps1'
    if (Test-Path $p) { Write-Host "Found: $p"; Get-Content $p }
    else { Write-Host "No PowerShell startup script" }
} catch { Write-Host "Error: $_" }

try {
    $p2 = $env:ProgramFiles + '\PowerShell\7\profile.ps1'
    if (Test-Path $p2) { Write-Host "Found: $p2"; Get-Content $p2 }
} catch { Write-Host "Error: $_" }

Write-Host ""
Write-Host "=== Check safe_rm_aliases global registration ==="
$paths = @(
    "$env:USERPROFILE\Documents\WindowsPowerShell\profile.ps1",
    "$env:USERPROFILE\Documents\PowerShell\profile.ps1",
    "$env:ProgramFiles\PowerShell\7\profile.ps1"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "Found profile: $p"
        $content = Get-Content $p -Raw
        if ($content -match 'safe_rm_aliases') {
            Write-Host "  >>> CONTAINS safe_rm_aliases reference!"
        }
    }
}
Write-Host "Done checking"
