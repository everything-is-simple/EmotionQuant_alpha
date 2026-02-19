# Check which process has the DuckDB file locked
$filePath = "g:\emotionquant_data\duckdb\emotionquant.duckdb"

Write-Host "Checking for processes using: $filePath"

# Use handle.exe if available, otherwise try alternative methods
$handleExe = "C:\Windows\Sysinternals\handle.exe"

if (Test-Path $handleExe) {
    Write-Host "Using handle.exe..."
    & $handleExe $filePath
} else {
    Write-Host "handle.exe not found, checking open files..."

    # Alternative: use netstat or check for any duckdb processes
    Get-Process python* | Format-Table Id, ProcessName, CPU, WorkingSet -AutoSize

    # Check if file exists and is locked
    try {
        $file = [System.IO.File]::Open($filePath, 'Open', 'Read', 'None')
        $file.Close()
        Write-Host "[OK] File is NOT locked - can be opened"
    } catch {
        Write-Host "[LOCKED] File is locked by another process: $($_.Exception.Message)"
    }
}
