param(
    [string]$Start = "",
    [string]$End = "",
    [int]$BatchSize = 365,
    [ValidateSet("day", "month", "year")]
    [string]$BatchUnit = "day",
    [int]$Workers = 3,
    [int]$RetryMax = 10,
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

if ($RetryUnlock) {
    $RetryOnly = $true
    $CheckLock = $true
    $ForceStopLockPid = $true
}

if ($ForceStopLockPid -and (-not $CheckLock)) {
    throw "-ForceStopLockPid requires -CheckLock (or use -RetryUnlock)."
}

function Get-Runner {
    if ($UseEq) {
        if (-not (Get-Command eq -ErrorAction SilentlyContinue)) {
            throw "eq command not found. Remove -UseEq or install eq in current environment."
        }
        return @{
            Exe = "eq"
            Prefix = @()
        }
    }
    return @{
        Exe = "python"
        Prefix = @("-m", "src.pipeline.main")
    }
}

function Invoke-PipelineCommand {
    param(
        [hashtable]$Runner,
        [string[]]$CommandArgs
    )
    $allArgs = @($Runner.Prefix + $CommandArgs)
    $rawOutput = & $Runner.Exe @allArgs
    $exitCode = [int]$LASTEXITCODE
    if ($null -ne $rawOutput) {
        $rawOutput | ForEach-Object { Write-Host $_ }
    }
    return $exitCode
}

function Get-FetchStatus {
    param(
        [hashtable]$Runner
    )
    $allArgs = @($Runner.Prefix + @("fetch-status"))
    $raw = & $Runner.Exe @allArgs
    if ($LASTEXITCODE -ne 0) {
        throw "fetch-status failed with exit code $LASTEXITCODE"
    }
    $jsonLine = ($raw | Select-Object -Last 1)
    if (-not $jsonLine) {
        throw "fetch-status returned empty output."
    }
    return ($jsonLine | ConvertFrom-Json)
}

function Show-StatusSummary {
    param(
        [pscustomobject]$Status
    )
    Write-Host (
        "[fetch-status] status={0} completed={1}/{2} failed={3} range={4}..{5}" -f `
            $Status.status, `
            $Status.completed_batches, `
            $Status.total_batches, `
            $Status.failed_batches, `
            $Status.start_date, `
            $Status.end_date
    )
}

function Show-LockHint {
    param(
        [pscustomobject]$Status
    )
    $lockPids = @(Get-LockPidsFromStatus -Status $Status)
    if ($lockPids.Length -eq 0) {
        return
    }
    Write-Host "[hint] DuckDB file lock detected. Close holder process and retry."
    foreach ($lockPid in $lockPids) {
        Write-Host ("[hint] Possible holder PID={0}" -f $lockPid)
    }
}

function Get-LockPidsFromStatus {
    param(
        [pscustomobject]$Status
    )
    $errorMap = $null
    if (($Status.PSObject.Properties.Name -contains "failed_batch_errors") -and $Status.failed_batch_errors) {
        $errorMap = $Status.failed_batch_errors
    } elseif (($Status.PSObject.Properties.Name -contains "progress_path") -and $Status.progress_path) {
        $progressPath = [string]$Status.progress_path
        if (Test-Path $progressPath) {
            try {
                $progressObj = Get-Content $progressPath -Raw | ConvertFrom-Json
                if (($progressObj.PSObject.Properties.Name -contains "failed_batch_errors") -and $progressObj.failed_batch_errors) {
                    $errorMap = $progressObj.failed_batch_errors
                }
            } catch {
                $errorMap = $null
            }
        }
    }
    if (-not $errorMap) {
        return @()
    }
    $values = @()
    if ($errorMap -is [hashtable]) {
        $values = @($errorMap.Values)
    } elseif ($errorMap -is [pscustomobject]) {
        $values = @($errorMap.PSObject.Properties | ForEach-Object { $_.Value })
    }
    $lockErrors = @($values | Where-Object { $_ -match "File is already open in" })
    if ($lockErrors.Count -eq 0) {
        return @()
    }
    $seenPids = @{}
    foreach ($err in $lockErrors) {
        if ($err -match "PID\s+(\d+)") {
            $pidValue = $matches[1]
            if (-not $seenPids.ContainsKey($pidValue)) {
                $seenPids[$pidValue] = $true
            }
        }
    }
    return @($seenPids.Keys | Sort-Object)
}

function Resolve-LockPids {
    param(
        [string[]]$LockPids,
        [bool]$StopProcess
    )
    $pidList = New-Object System.Collections.Generic.List[string]
    if ($null -ne $LockPids) {
        foreach ($item in @($LockPids)) {
            $pidText = [string]$item
            if (-not [string]::IsNullOrWhiteSpace($pidText)) {
                [void]$pidList.Add($pidText)
            }
        }
    }
    if ($pidList.Count -eq 0) {
        Write-Host "[lock-check] no lock PID found in latest failed errors."
        return
    }
    foreach ($lockPid in $pidList) {
        $targetPid = 0
        if (-not [int]::TryParse($lockPid, [ref]$targetPid)) {
            Write-Host ("[lock-check] skip invalid PID={0}" -f $lockPid)
            continue
        }
        $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
        if (-not $proc) {
            Write-Host ("[lock-check] PID={0} not running (stale lock record)." -f $targetPid)
            continue
        }
        Write-Host ("[lock-check] PID={0} name={1} path={2}" -f $proc.Id, $proc.ProcessName, $proc.Path)
        if ($StopProcess) {
            try {
                Stop-Process -Id $targetPid -Force -ErrorAction Stop
                Write-Host ("[lock-check] stopped PID={0}" -f $targetPid)
            } catch {
                Write-Host ("[lock-check] failed to stop PID={0}: {1}" -f $targetPid, $_.Exception.Message)
            }
        }
    }
}

function Resolve-RunnerLogPaths {
    param(
        [string]$StateDir,
        [string]$RequestedLogFile
    )
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $rawPath = $RequestedLogFile
    if ([string]::IsNullOrWhiteSpace($rawPath)) {
        $rawPath = Join-Path $StateDir ("l1-fetch-{0}.log" -f $timestamp)
    } elseif (-not [System.IO.Path]::IsPathRooted($rawPath)) {
        $rawPath = Join-Path $StateDir $rawPath
    }
    $rawPath = [System.IO.Path]::GetFullPath($rawPath)
    $ext = [System.IO.Path]::GetExtension($rawPath)
    if ($ext -ieq ".log") {
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
        args = $ArgsText
        started_at_local = (Get-Date).ToString("s")
        updated_at_local = (Get-Date).ToString("s")
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $StatePath) -Force | Out-Null
    $payload | ConvertTo-Json -Depth 5 | Set-Content -Path $StatePath -Encoding UTF8
}

function Get-RunnerState {
    param(
        [string]$StatePath
    )
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
    param(
        [pscustomobject]$RunnerState
    )
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
    if ($proc) {
        Write-Host ("[runner-status] process={0}" -f $proc.ProcessName)
    }
}

function Stop-RunnerProcess {
    param(
        [pscustomobject]$RunnerState
    )
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

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
Set-Location $repoRoot
$stateDir = Join-Path $repoRoot "artifacts\spiral-s3a\_state"
$runnerStatePath = Join-Path $stateDir "l1_fetch_runner.json"

$runner = Get-Runner
Write-Host ("[runner] {0} {1}" -f $runner.Exe, ($runner.Prefix -join " "))

if ($RunnerStatus) {
    $runnerState = Get-RunnerState -StatePath $runnerStatePath
    Show-RunnerStatus -RunnerState $runnerState
    exit 0
}

if ($StopRunner) {
    $runnerState = Get-RunnerState -StatePath $runnerStatePath
    Stop-RunnerProcess -RunnerState $runnerState
    exit 0
}

if ($Background -and $StatusOnly) {
    throw "-Background cannot be used with -StatusOnly."
}

if ($Background) {
    $logPaths = Resolve-RunnerLogPaths -StateDir $stateDir -RequestedLogFile $LogFile
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null

    $selfPath = [System.IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)
    $childArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $selfPath)
    if (-not [string]::IsNullOrWhiteSpace($Start)) {
        $childArgs += @("-Start", $Start)
    }
    if (-not [string]::IsNullOrWhiteSpace($End)) {
        $childArgs += @("-End", $End)
    }
    $childArgs += @(
        "-BatchSize", $BatchSize.ToString(),
        "-BatchUnit", $BatchUnit,
        "-Workers", $Workers.ToString(),
        "-RetryMax", $RetryMax.ToString()
    )
    if ($NoProgress) { $childArgs += "-NoProgress" }
    if ($RetryOnly) { $childArgs += "-RetryOnly" }
    if ($CheckLock) { $childArgs += "-CheckLock" }
    if ($ForceStopLockPid) { $childArgs += "-ForceStopLockPid" }
    if ($RetryUnlock) { $childArgs += "-RetryUnlock" }
    if ($UseEq) { $childArgs += "-UseEq" }

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
    Write-Host ("[hint] check process: powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -RunnerStatus")
    Write-Host ("[hint] stop process : powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StopRunner")
    exit 0
}

if ($StatusOnly) {
    $status = Get-FetchStatus -Runner $runner
    Show-StatusSummary -Status $status
    Show-LockHint -Status $status
    exit 0
}

if ((-not $RetryOnly) -and ([string]::IsNullOrWhiteSpace($Start) -or [string]::IsNullOrWhiteSpace($End))) {
    throw "Start/End are required unless -StatusOnly is used. Example: -Start 20200101 -End 20260218"
}

if (-not $RetryOnly) {
    Write-Host (
        "[range] {0} -> {1}  batch_size={2} batch_unit={3} workers={4}" -f `
            $Start, `
            $End, `
            $BatchSize, `
            $BatchUnit, `
            $Workers
    )
}

$batchArgs = @(
    "fetch-batch",
    "--start", $Start,
    "--end", $End,
    "--batch-size", $BatchSize.ToString(),
    "--batch-unit", $BatchUnit,
    "--workers", $Workers.ToString()
)
if ($NoProgress) {
    $batchArgs += "--no-progress"
}

if (-not $RetryOnly) {
    $batchExit = Invoke-PipelineCommand -Runner $runner -CommandArgs $batchArgs
    if ($batchExit -ne 0) {
        Write-Host ("[warn] fetch-batch exit code={0}; continue with status and retries." -f $batchExit)
    }
}

$status = Get-FetchStatus -Runner $runner
Show-StatusSummary -Status $status

if ($CheckLock) {
    $lockPids = Get-LockPidsFromStatus -Status $status
    Resolve-LockPids -LockPids $lockPids -StopProcess:$ForceStopLockPid
}

$retryRound = 0
while ($status.status -ne "completed" -and [int]$status.failed_batches -gt 0 -and $retryRound -lt $RetryMax) {
    $retryRound += 1
    Write-Host ("[retry] round {0}/{1}" -f $retryRound, $RetryMax)
    $retryExit = Invoke-PipelineCommand -Runner $runner -CommandArgs @("fetch-retry")
    if ($retryExit -ne 0) {
        Write-Host ("[warn] fetch-retry exit code={0}" -f $retryExit)
    }
    $status = Get-FetchStatus -Runner $runner
    Show-StatusSummary -Status $status
}

$resumeRound = 0
while ($status.status -ne "completed" -and [int]$status.failed_batches -eq 0 -and $resumeRound -lt $RetryMax) {
    $resumeRound += 1
    Write-Host ("[resume] round {0}/{1} status={2} failed={3}" -f $resumeRound, $RetryMax, $status.status, $status.failed_batches)
    $resumeExit = Invoke-PipelineCommand -Runner $runner -CommandArgs $batchArgs
    if ($resumeExit -ne 0) {
        Write-Host ("[warn] fetch-batch resume exit code={0}" -f $resumeExit)
    }
    $status = Get-FetchStatus -Runner $runner
    Show-StatusSummary -Status $status
}

Show-LockHint -Status $status

if ($status.status -eq "completed") {
    Write-Host "[done] L1 backfill completed."
    exit 0
}

Write-Host "[fail] Failed batches remain; check retry_report_path for details."
if ($status.PSObject.Properties.Name -contains "retry_report_path") {
    Write-Host ("[report] {0}" -f $status.retry_report_path)
}
exit 1
