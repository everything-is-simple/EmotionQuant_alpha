param(
    [string]$Start = "",
    [string]$End = "",
    [int]$BatchSize = 365,
    [int]$Workers = 3,
    [int]$RetryMax = 10,
    [switch]$NoProgress,
    [switch]$StatusOnly,
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
    $lockErrors = @($errorMap.PSObject.Properties.Value | Where-Object {
            $_ -match "File is already open in"
        })
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
    if ($LockPids.Count -eq 0) {
        Write-Host "[lock-check] no lock PID found in latest failed errors."
        return
    }
    foreach ($lockPid in $LockPids) {
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

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
Set-Location $repoRoot

$runner = Get-Runner
Write-Host ("[runner] {0} {1}" -f $runner.Exe, ($runner.Prefix -join " "))

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
    Write-Host ("[range] {0} -> {1}  batch_size={2} workers={3}" -f $Start, $End, $BatchSize, $Workers)
}

$batchArgs = @(
    "fetch-batch",
    "--start", $Start,
    "--end", $End,
    "--batch-size", $BatchSize.ToString(),
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
