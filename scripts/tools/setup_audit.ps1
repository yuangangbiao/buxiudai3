# Step 1: Enable file system audit policy
Write-Host "Step 1: Enabling file system audit policy..."
try {
    $result = auditpol /set /subcategory:"File System" /success:enable /failure:enable 2>&1
    Write-Host "    Result: $result"
} catch {
    Write-Host "   Need admin rights: $_"
}

# Step 2: Configure SACL on data directory
Write-Host "`nStep 2: Configuring SACL on data directory..."
$path = "D:\yuan\不锈钢网带跟单3.0\data"
try {
    $acl = Get-Acl -Path $path -Audit
    $rule = New-Object System.Security.AccessControl.FileSystemAuditRule(
        "Everyone",
        "Delete,DeleteSubdirectoriesAndFiles",
        "ContainerInherit,ObjectInherit",
        "None",
        "Success"
    )
    $acl.AddAuditRule($rule)
    Set-Acl -Path $path -AclObject $acl
    Write-Host "   SACL configured successfully"
} catch {
    Write-Host "   SACL config failed: $_"
    Write-Host "   May need admin rights"
}

# Step 3: Verify
Write-Host "`nStep 3: Verification..."
try {
    $current = auditpol /get /subcategory:"File System" 2>&1
    Write-Host "   $current"
} catch {
    Write-Host "   Cannot read policy: $_"
}

Write-Host "`nDONE! Now start the server, then run check_audit_results.ps1"
