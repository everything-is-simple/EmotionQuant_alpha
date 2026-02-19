# Check DuckDB file lock status
$filePath = "g:\emotionquant_data\duckdb\emotionquant.duckdb"

Write-Host "=== DuckDB File Status ==="
Write-Host "File: $filePath"

# Check if file exists
if (Test-Path $filePath) {
    $fileInfo = Get-Item $filePath
    Write-Host "Size: $([math]::Round($fileInfo.Length / 1MB, 2)) MB"
    Write-Host "Last Modified: $($fileInfo.LastWriteTime)"

    # Try to open file
    try {
        $stream = [System.IO.File]::Open($filePath, 'Open', 'Read', 'None')
        $stream.Close()
        Write-Host "Status: [OK] File is NOT locked"
    } catch {
        Write-Host "Status: [LOCKED] $($_.Exception.Message)"
    }
} else {
    Write-Host "Status: [NOT FOUND] File does not exist"
}

# Check for lock files
$lockFiles = Get-ChildItem -Path (Split-Path $filePath -Parent) -Filter "*.lock" -ErrorAction SilentlyContinue
if ($lockFiles) {
    Write-Host "`n=== Lock Files Found ==="
    $lockFiles | Format-Table Name, LastWriteTime
}

# Check Python processes with high memory (likely running tasks)
Write-Host "`n=== High Memory Python Processes ==="
Get-Process python* | Where-Object { $_.WorkingSet -gt 100MB } | Format-Table Id, ProcessName, @{N='Memory(MB)';E={[math]::Round($_.WorkingSet/1MB,0)}} -AutoSize
