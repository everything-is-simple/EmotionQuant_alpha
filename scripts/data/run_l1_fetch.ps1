param(
    [string]$Start = "",
    [string]$End = "",
    [int]$BatchSize = 10,
    [ValidateSet("day", "month", "year")]
    [string]$BatchUnit = "day",
    [int]$Workers = 1,
    [int]$RetryMax = 3,
    [string]$Tables = "",
    [switch]$SkipExisting,
    [string]$EnvFile = ".env",
    [string]$PythonExe = "",
    [string]$LogFile = "",
    [switch]$NoProgress,
    [switch]$Background,
    [switch]$StatusOnly,
    [switch]$RunnerStatus,
    [switch]$StopRunner,
    [switch]$RetryOnly,
    [switch]$CheckLock,
    [switch]$ForceStopLockPid,
    [switch]$RetryUnlock,
    [switch]$UseEq
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# 兼容旧参数语义：重试场景默认启用断点续传。
if ($RetryUnlock) {
    $RetryOnly = $true
    $SkipExisting = $true
}
if ($RetryOnly) {
    $SkipExisting = $true
}

if ($ForceStopLockPid -and (-not $CheckLock)) {
    throw "-ForceStopLockPid requires -CheckLock (or use -RetryUnlock)."
}

# 说明旧参数兼容情况，避免调用方静默误解。
if ($BatchUnit -ne "day") {
    Write-Host "[warn] -BatchUnit is deprecated for bulk_download and will be ignored." -ForegroundColor Yellow
}
if ($Workers -ne 1) {
    Write-Host "[warn] -Workers is deprecated for bulk_download and will be ignored." -ForegroundColor Yellow
}
if ($NoProgress) {
    Write-Host "[warn] -NoProgress is deprecated for bulk_download and will be ignored." -ForegroundColor Yellow
}
if ($UseEq) {
    Write-Host "[warn] -UseEq is deprecated for bulk_download and will be ignored." -ForegroundColor Yellow
}
if ($CheckLock -or $ForceStopLockPid) {
    Write-Host "[warn] lock-check flags are deprecated for bulk_download and will be ignored." -ForegroundColor Yellow
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
Set-Location $repoRoot
$stateDir = Join-Path $repoRoot "artifacts\spiral-s3a\_state"
$runnerStatePath = Join-Path $stateDir "l1_fetch_runner.json"
$progressPath = Join-Path $repoRoot "artifacts\bulk_download_progress.json"

function Resolve-PythonExecutable {
    param([string]$Preferred)

    if (-not [string]::IsNullOrWhiteSpace($Preferred)) {
        return $Preferred
    }

    $venvPython = Join-Path (Get-Location).Path ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    return "python"
}

function Resolve-RunnerLogPaths {
    param(
        [string]$StateDir,
        [string]$RequestedLogFile
    )

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $rawPath = $RequestedLogFile
    if ([string]::IsNullOrWhiteSpace($rawPath)) {
        $rawPath = Join-Path $StateDir ("l1-bulk-{0}.log" -f $timestamp)
    } elseif (-not [System.IO.Path]::IsPathRooted($rawPath)) {
        $rawPath = Join-Path $StateDir $rawPath
    }

    $rawPath = [System.IO.Path]::GetFullPath($rawPath)
    if ([System.IO.Path]::GetExtension($rawPath) -ieq ".log") {
        return @{
            StdOut = $rawPath
            StdErr = ($rawPath -replace "\.log$", ".err.log")
        }
    }

    return @{
        StdOut = ("{0}.out.log" -f $rawPath)
        StdErr = ("{0}.err.log" -f $rawPath)
    }
}

function Save-RunnerState {
    param(
        [string]$StatePath,
        [int]$RunnerPid,
        [string]$StdOutPath,
        [string]$StdErrPath,
        [string]$StartDate,
        [string]$EndDate,
        [string]$ArgsText
    )

    $payload = [ordered]@{
        runner_pid = $RunnerPid
        status_hint = "running"
        start_date = $StartDate
        end_date = $EndDate
        stdout_log_path = $StdOutPath
        stderr_log_path = $StdErrPath
        progress_path = $progressPath
        args = $ArgsText
        started_at_local = (Get-Date).ToString("s")
        updated_at_local = (Get-Date).ToString("s")
    }

    New-Item -ItemType Directory -Path (Split-Path -Parent $StatePath) -Force | Out-Null
    $payload | ConvertTo-Json -Depth 5 | Set-Content -Path $StatePath -Encoding UTF8
}

function Get-RunnerState {
    param([string]$StatePath)

    if (-not (Test-Path $StatePath)) {
        return $null
    }

    try {
        return (Get-Content $StatePath -Raw | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Show-RunnerStatus {
    param([pscustomobject]$RunnerState)

    if (-not $RunnerState) {
        Write-Host "[runner-status] no background runner record found."
        return
    }

    $pidValue = 0
    [void][int]::TryParse([string]$RunnerState.runner_pid, [ref]$pidValue)
    $proc = $null
    if ($pidValue -gt 0) {
        $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    }

    $runtimeStatus = if ($proc) { "running" } else { "stopped" }
    Write-Host ("[runner-status] pid={0} runtime={1} range={2}..{3}" -f $pidValue, $runtimeStatus, $RunnerState.start_date, $RunnerState.end_date)
    Write-Host ("[runner-status] stdout_log={0}" -f $RunnerState.stdout_log_path)
    Write-Host ("[runner-status] stderr_log={0}" -f $RunnerState.stderr_log_path)
    Write-Host ("[runner-status] progress={0}" -f $progressPath)
}

function Stop-RunnerProcess {
    param([pscustomobject]$RunnerState)

    if (-not $RunnerState) {
        Write-Host "[runner-stop] no background runner record found."
        return
    }

    $pidValue = 0
    if (-not [int]::TryParse([string]$RunnerState.runner_pid, [ref]$pidValue)) {
        Write-Host ("[runner-stop] invalid pid in runner state: {0}" -f $RunnerState.runner_pid)
        return
    }

    $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if (-not $proc) {
        Write-Host ("[runner-stop] pid={0} already stopped." -f $pidValue)
        return
    }

    Stop-Process -Id $pidValue -Force -ErrorAction Stop
    Write-Host ("[runner-stop] stopped pid={0}" -f $pidValue)
}

function Show-BulkProgress {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        Write-Host "[bulk-progress] progress file not found."
        return
    }

    try {
        $payload = Get-Content -Path $Path -Raw | ConvertFrom-Json
    } catch {
        Write-Host ("[bulk-progress] failed to parse progress file: {0}" -f $_.Exception.Message)
        return
    }

    Write-Host (
        "[bulk-progress] range={0}..{1} done={2}/{3} skipped={4} failed={5} rows={6} elapsed={7}s" -f `
            $payload.start_date, `
            $payload.end_date, `
            $payload.completed_days, `
            $payload.total_open_days, `
            $payload.skipped_days, `
            $payload.failed_days, `
            $payload.total_rows, `
            $payload.elapsed_seconds
    )
}

function Build-BulkArgs {
    param(
        [string]$StartDate,
        [string]$EndDate,
        [int]$FlushDays,
        [bool]$EnableSkipExisting,
        [string]$TablesFilter,
        [string]$EnvFilePath
    )

    $args = @(
        "scripts/data/bulk_download.py",
        "--start", $StartDate,
        "--end", $EndDate,
        "--batch-size", $FlushDays.ToString()
    )

    if ($EnableSkipExisting) {
        $args += "--skip-existing"
    }
    if (-not [string]::IsNullOrWhiteSpace($TablesFilter)) {
        $args += @("--tables", $TablesFilter)
    }
    if (-not [string]::IsNullOrWhiteSpace($EnvFilePath)) {
        $args += @("--env-file", $EnvFilePath)
    }

    return @($args)
}

function Invoke-BulkDownloadOnce {
    param(
        [string]$PythonPath,
        [string[]]$BulkArgs
    )

    $output = & $PythonPath @BulkArgs
    $exitCode = [int]$LASTEXITCODE
    if ($null -ne $output) {
        $output | ForEach-Object { Write-Host $_ }
    }
    return $exitCode
}

$pythonPath = Resolve-PythonExecutable -Preferred $PythonExe
Write-Host ("[runner] python={0}" -f $pythonPath)

if ($RunnerStatus) {
    $runnerState = Get-RunnerState -StatePath $runnerStatePath
    Show-RunnerStatus -RunnerState $runnerState
    Show-BulkProgress -Path $progressPath
    exit 0
}

if ($StopRunner) {
    $runnerState = Get-RunnerState -StatePath $runnerStatePath
    Stop-RunnerProcess -RunnerState $runnerState
    exit 0
}

if ($StatusOnly) {
    Show-BulkProgress -Path $progressPath
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Start) -or [string]::IsNullOrWhiteSpace($End)) {
    throw "Start/End are required unless -StatusOnly, -RunnerStatus, or -StopRunner is used."
}

if ($Background) {
    $logPaths = Resolve-RunnerLogPaths -StateDir $stateDir -RequestedLogFile $LogFile
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null

    $selfPath = [System.IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)
    $childArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $selfPath)
    $childArgs += @("-Start", $Start, "-End", $End, "-BatchSize", $BatchSize.ToString(), "-RetryMax", $RetryMax.ToString())

    if (-not [string]::IsNullOrWhiteSpace($Tables)) { $childArgs += @("-Tables", $Tables) }
    if (-not [string]::IsNullOrWhiteSpace($EnvFile)) { $childArgs += @("-EnvFile", $EnvFile) }
    if (-not [string]::IsNullOrWhiteSpace($PythonExe)) { $childArgs += @("-PythonExe", $PythonExe) }
    if ($SkipExisting) { $childArgs += "-SkipExisting" }
    if ($RetryOnly) { $childArgs += "-RetryOnly" }

    $powershellExe = (Get-Command powershell -ErrorAction SilentlyContinue).Source
    if (-not $powershellExe) {
        $powershellExe = Join-Path $PSHOME "powershell.exe"
    }

    $child = Start-Process `
        -FilePath $powershellExe `
        -ArgumentList $childArgs `
        -WorkingDirectory $repoRoot `
        -RedirectStandardOutput $logPaths.StdOut `
        -RedirectStandardError $logPaths.StdErr `
        -PassThru

    Save-RunnerState `
        -StatePath $runnerStatePath `
        -RunnerPid $child.Id `
        -StdOutPath $logPaths.StdOut `
        -StdErrPath $logPaths.StdErr `
        -StartDate $Start `
        -EndDate $End `
        -ArgsText ($childArgs -join " ")

    Write-Host ("[runner] started background pid={0}" -f $child.Id)
    Write-Host ("[runner] stdout log: {0}" -f $logPaths.StdOut)
    Write-Host ("[runner] stderr log: {0}" -f $logPaths.StdErr)
    Write-Host "[hint] check progress: powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StatusOnly"
    Write-Host "[hint] check runner : powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -RunnerStatus"
    Write-Host "[hint] stop runner  : powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StopRunner"
    exit 0
}

$maxAttempts = [Math]::Max(1, $RetryMax + 1)
$finalExitCode = 1

for ($attempt = 0; $attempt -lt $maxAttempts; $attempt++) {
    $resumeMode = $SkipExisting -or ($attempt -gt 0)
    if ($attempt -gt 0) {
        Write-Host ("[retry] rerun bulk_download attempt {0}/{1} (resume=true)" -f ($attempt + 1), $maxAttempts)
    }

    $bulkArgs = Build-BulkArgs `
        -StartDate $Start `
        -EndDate $End `
        -FlushDays $BatchSize `
        -EnableSkipExisting:$resumeMode `
        -TablesFilter $Tables `
        -EnvFilePath $EnvFile

    Write-Host ("[run] {0} {1}" -f $pythonPath, ($bulkArgs -join " "))
    $finalExitCode = Invoke-BulkDownloadOnce -PythonPath $pythonPath -BulkArgs $bulkArgs
    Show-BulkProgress -Path $progressPath

    if ($finalExitCode -eq 0) {
        Write-Host "[done] bulk download completed."
        break
    }

    Write-Host ("[warn] bulk_download exit code={0}" -f $finalExitCode) -ForegroundColor Yellow
}

if ($finalExitCode -ne 0) {
    Write-Host "[fail] bulk download failed after retries." -ForegroundColor Red
}

exit $finalExitCode

