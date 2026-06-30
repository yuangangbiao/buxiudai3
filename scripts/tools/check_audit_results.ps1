# Read security audit log for delete events in data directory
Write-Host "=== Security Log: Delete events in data/ directory ==="
Write-Host ""

try {
    $events = Get-WinEvent -FilterHashtable @{LogName='Security';Id=4663} -MaxEvents 1000 -ErrorAction Stop
    $found = $false
    foreach ($event in $events) {
        $xml = [xml]$event.ToXml()
        $file = ""
        $process = ""
        $access = ""
        foreach ($data in $xml.Event.EventData.Data) {
            if ($data.Name -eq "ObjectName") { $file = $data.'#text' }
            if ($data.Name -eq "ProcessName") { $process = $data.'#text' }
            if ($data.Name -eq "AccessMask") { $access = $data.'#text' }
        }
        if ($file -match '\\\\data\\\\') {
            $found = $true
            Write-Host "Time : $($event.TimeCreated)"
            Write-Host "Process: $process"
            Write-Host "File  : $file"
            Write-Host "Access: $access"
            if ($access -eq "0x10000") { Write-Host "Action: DELETE" }
            elseif ($access -eq "0x10040") { Write-Host "Action: DELETE + READ_CONTROL" }
            elseif ($access -eq "0x10080") { Write-Host "Action: DELETE + READ_CONTROL + WRITE_DAC" }
            Write-Host "---"
        }
    }
    if (-not $found) {
        Write-Host "No delete events found in data/ directory"
        Write-Host "Possible reasons:"
        Write-Host "  1. SACL not configured (run setup_audit.ps1 as admin)"
        Write-Host "  2. No file deletions occurred yet"
        Write-Host "  3. Files moved via MoveFile, not deleted"
    }
} catch {
    Write-Host "Cannot read security log: $_"
    Write-Host "Try running as administrator"
}

Write-Host ""
Write-Host "=== Search for 4656 (Handle to object) events ==="
try {
    $events2 = Get-WinEvent -FilterHashtable @{LogName='Security';Id=4656} -MaxEvents 200 -ErrorAction Stop
    $found2 = $false
    foreach ($event in $events2) {
        $xml = [xml]$event.ToXml()
        $file = ""
        foreach ($data in $xml.Event.EventData.Data) {
            if ($data.Name -eq "ObjectName") { $file = $data.'#text' }
        }
        if ($file -match '\\\\data\\\\' -and $file -match '\.db-wal|\.db-shm') {
            $found2 = $true
            Write-Host "Time : $($event.TimeCreated)"
            Write-Host "File  : $file"
            Write-Host "---"
        }
    }
    if (-not $found2) { Write-Host "No .db-wal/.db-shm access events in data/" }
} catch {
    Write-Host "Cannot read security log: $_"
}

Write-Host ""
try { auditpol /get /subcategory:"File System" 2>&1 } catch { }
