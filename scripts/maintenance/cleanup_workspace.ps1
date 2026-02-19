param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$targets = @(
    ".pytest_cache",
    ".tmp",
    "tests_tmp",
    "gcm-diagnose.log"
)

Write-Host "[cleanup] workspace root: $PWD"
Write-Host "[cleanup] dry_run=$DryRun"

foreach ($target in $targets) {
    if (Test-Path $target) {
        if ($DryRun) {
            Write-Host "[dry-run] remove $target"
        } else {
            Remove-Item $target -Recurse -Force
            Write-Host "[ok] removed $target"
        }
    } else {
        Write-Host "[skip] missing $target"
    }
}

$pycacheDirs = Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -Force
if ($pycacheDirs.Count -eq 0) {
    Write-Host "[skip] no __pycache__ directories"
} else {
    foreach ($dir in $pycacheDirs) {
        if ($DryRun) {
            Write-Host "[dry-run] remove $($dir.FullName)"
        } else {
            Remove-Item $dir.FullName -Recurse -Force
            Write-Host "[ok] removed $($dir.FullName)"
        }
    }
}

Write-Host "[cleanup] done"

