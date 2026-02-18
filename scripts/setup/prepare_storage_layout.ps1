param(
    [string]$DataRoot = "",
    [switch]$GrantCurrentUserModify
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($DataRoot)) {
    $DataRoot = $env:DATA_PATH
}
if ([string]::IsNullOrWhiteSpace($DataRoot)) {
    throw "DataRoot is empty. Pass -DataRoot or set DATA_PATH in environment."
}

$resolvedDataRoot = [System.IO.Path]::GetFullPath($DataRoot)
$subDirs = @("duckdb", "parquet", "cache", "logs")
$currentUser = "$env:USERDOMAIN\$env:USERNAME"

Write-Host "[storage] target data root: $resolvedDataRoot"
New-Item -ItemType Directory -Force -Path $resolvedDataRoot | Out-Null

if ($GrantCurrentUserModify) {
    Write-Host "[storage] grant modify to current user: $currentUser"
    icacls $resolvedDataRoot /grant "${currentUser}:(OI)(CI)M" /T /C | Out-Null
}

foreach ($dir in $subDirs) {
    $path = Join-Path $resolvedDataRoot $dir
    New-Item -ItemType Directory -Force -Path $path | Out-Null

    $probe = Join-Path $path ".write_probe.tmp"
    Set-Content -Path $probe -Value "ok" -Encoding utf8
    Remove-Item -Path $probe -Force
    Write-Host "[storage] writable: $path"
}

$dbPath = Join-Path $resolvedDataRoot "duckdb\emotionquant.duckdb"
@"
import duckdb
from pathlib import Path

db_path = Path(r"$dbPath")
db_path.parent.mkdir(parents=True, exist_ok=True)
with duckdb.connect(str(db_path)) as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS _storage_probe (marker VARCHAR)")
    conn.execute("INSERT INTO _storage_probe VALUES ('ok')")
    count = conn.execute("SELECT COUNT(*) FROM _storage_probe").fetchone()[0]
print(f"[storage] duckdb probe rows={count} path={db_path}")
"@ | python -

Write-Host "[storage] prepare_storage_layout completed"
