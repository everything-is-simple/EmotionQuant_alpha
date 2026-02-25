param(
    [Parameter(Mandatory = $true)]
    [string]$Start,
    [Parameter(Mandatory = $true)]
    [string]$End,
    [int]$BatchSize = 10,
    [int]$RetryMax = 2,
    [double]$MaxMonthMinutes = 20,
    [int]$StatusPollSeconds = 10,
    [string]$Tables = "",
    [string]$EnvFile = ".env",
    [string]$PythonExe = "",
    [switch]$SkipExisting,
    [switch]$NoProgress,
    [switch]$UseEq,
    [bool]$KillConcurrentFetchProcesses = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($StatusPollSeconds -le 0) {
    throw "StatusPollSeconds must be > 0."
}
if ($MaxMonthMinutes -le 0) {
    throw "MaxMonthMinutes must be > 0."
}
if ($UseEq) {
    Write-Host "[warn] -UseEq is deprecated for bulk_download and will be ignored." -ForegroundColor Yellow
}
if ($NoProgress) {
    Write-Host "[warn] -NoProgress is deprecated for bulk_download and will be ignored." -ForegroundColor Yellow
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
Set-Location $repoRoot
$runScriptPath = Join-Path $scriptDir "run_l1_fetch.ps1"
$stateDir = Join-Path $repoRoot "artifacts\spiral-s3a\_state"
$progressPath = Join-Path $repoRoot "artifacts\bulk_download_progress.json"

if (-not (Test-Path $runScriptPath)) {
    throw "run_l1_fetch.ps1 not found: $runScriptPath"
}

function Parse-TradeDate {
    param([string]$Value)
    return [datetime]::ParseExact($Value, "yyyyMMdd", [System.Globalization.CultureInfo]::InvariantCulture)
}

function Get-MonthEnd {
    param([datetime]$Value)
    return (Get-Date -Year $Value.Year -Month $Value.Month -Day 1).AddMonths(1).AddDays(-1)
}

function Get-ActiveBulkDownloadProcesses {
    return @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^python(\.exe)?$" -and
        $_.CommandLine -match "scripts[\\/]data[\\/]bulk_download\.py"
    })
}

function Assert-NoConcurrentBulkDownloadProcess {
    $active = @(Get-ActiveBulkDownloadProcesses)
    if ($active.Count -le 0) {
        return
    }

    if ($KillConcurrentFetchProcesses) {
        Write-Host ("[cleanup] detected {0} concurrent bulk_download process(es), stopping..." -f $active.Count) -ForegroundColor Yellow
        foreach ($proc in $active) {
            try {
                Write-Host ("[cleanup] stop pid={0}" -f $proc.ProcessId) -ForegroundColor Yellow
                Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
            } catch {
            }
        }
        Start-Sleep -Seconds 2
        $active = @(Get-ActiveBulkDownloadProcesses)
        if ($active.Count -le 0) {
            Write-Host "[cleanup] concurrent bulk_download processes cleared." -ForegroundColor Green
            return
        }
    }

    $lines = @()
    foreach ($proc in $active) {
        $cmd = [string]$proc.CommandLine
        if ($cmd.Length -gt 200) {
            $cmd = $cmd.Substring(0, 200) + "..."
        }
        $lines += ("pid={0} name={1} cmd={2}" -f $proc.ProcessId, $proc.Name, $cmd)
    }
    throw ("concurrent_bulk_download_process_detected`n{0}" -f ($lines -join "`n"))
}

function Read-BulkProgress {
    if (-not (Test-Path $progressPath)) {
        return $null
    }

    try {
        return (Get-Content -Path $progressPath -Raw | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Invoke-MonthRun {
    param(
        [string]$MonthStartText,
        [string]$MonthEndText,
        [int]$AttemptIndex
    )

    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null

    $suffix = if ($AttemptIndex -gt 0) { ".attempt$AttemptIndex" } else { "" }
    $stdoutLog = Join-Path $stateDir ("monthly-bulk-{0}-{1}{2}.stdout.log" -f $MonthStartText, $MonthEndText, $suffix)
    $stderrLog = Join-Path $stateDir ("monthly-bulk-{0}-{1}{2}.stderr.log" -f $MonthStartText, $MonthEndText, $suffix)

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $runScriptPath,
        "-Start", $MonthStartText,
        "-End", $MonthEndText,
        "-BatchSize", $BatchSize.ToString(),
        "-RetryMax", "0",
        "-SkipExisting"
    )

    if (-not [string]::IsNullOrWhiteSpace($Tables)) {
        $args += @("-Tables", $Tables)
    }
    if (-not [string]::IsNullOrWhiteSpace($EnvFile)) {
        $args += @("-EnvFile", $EnvFile)
    }
    if (-not [string]::IsNullOrWhiteSpace($PythonExe)) {
        $args += @("-PythonExe", $PythonExe)
    }

    # 月度脚本统一启用断点续传，降低中断重跑成本。
    if ($SkipExisting) {
        $args += "-SkipExisting"
    }

    $powershellExe = (Get-Command powershell -ErrorAction SilentlyContinue).Source
    if (-not $powershellExe) {
        $powershellExe = Join-Path $PSHOME "powershell.exe"
    }

    $proc = Start-Process `
        -FilePath $powershellExe `
        -ArgumentList $args `
        -WorkingDirectory $repoRoot `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru

    $timeoutSeconds = [int][math]::Ceiling($MaxMonthMinutes * 60)
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    $nextPoll = (Get-Date).AddSeconds($StatusPollSeconds)

    while (-not $proc.HasExited) {
        Start-Sleep -Seconds 1

        if ((Get-Date) -ge $deadline) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            return @{
                ExitCode = 124
                TimedOut = $true
                StdOutLog = $stdoutLog
                StdErrLog = $stderrLog
            }
        }

        if ((Get-Date) -ge $nextPoll) {
            $progress = Read-BulkProgress
            if ($progress) {
                Write-Host (
                    "[heartbeat] month={0}->{1} done={2}/{3} failed={4} rows={5} elapsed={6}s" -f `
                        $MonthStartText, `
                        $MonthEndText, `
                        $progress.completed_days, `
                        $progress.total_open_days, `
                        $progress.failed_days, `
                        $progress.total_rows, `
                        $progress.elapsed_seconds
                )
            } else {
                Write-Host "[heartbeat] progress file not ready yet."
            }
            $nextPoll = (Get-Date).AddSeconds($StatusPollSeconds)
        }
    }

    if (Test-Path $stdoutLog) {
        Get-Content $stdoutLog | ForEach-Object { Write-Host $_ }
    }
    if (Test-Path $stderrLog) {
        Get-Content $stderrLog | ForEach-Object { Write-Host $_ }
    }

    return @{
        ExitCode = [int]$proc.ExitCode
        TimedOut = $false
        StdOutLog = $stdoutLog
        StdErrLog = $stderrLog
    }
}

$startDate = Parse-TradeDate -Value $Start
$endDate = Parse-TradeDate -Value $End
if ($endDate -lt $startDate) {
    throw "End must be >= Start"
}

$cursor = $startDate
while ($cursor -le $endDate) {
    $monthEnd = Get-MonthEnd -Value $cursor
    if ($monthEnd -gt $endDate) {
        $monthEnd = $endDate
    }

    $monthStartText = $cursor.ToString("yyyyMMdd")
    $monthEndText = $monthEnd.ToString("yyyyMMdd")

    Write-Host ("[month] {0} -> {1}" -f $monthStartText, $monthEndText)
    Assert-NoConcurrentBulkDownloadProcess

    $maxAttempts = [Math]::Max(1, $RetryMax + 1)
    $ok = $false

    for ($attempt = 0; $attempt -lt $maxAttempts; $attempt++) {
        if ($attempt -gt 0) {
            Write-Host ("[retry] month={0}->{1} attempt={2}/{3}" -f $monthStartText, $monthEndText, ($attempt + 1), $maxAttempts)
        }

        $result = Invoke-MonthRun `
            -MonthStartText $monthStartText `
            -MonthEndText $monthEndText `
            -AttemptIndex $attempt

        if ([int]$result.ExitCode -eq 0) {
            $ok = $true
            break
        }

        if ($result.TimedOut) {
            Write-Host ("[warn] month timeout: {0}->{1}, max={2} minutes" -f $monthStartText, $monthEndText, $MaxMonthMinutes) -ForegroundColor Yellow
        } else {
            Write-Host ("[warn] month failed exit_code={0}" -f $result.ExitCode) -ForegroundColor Yellow
        }
    }

    if (-not $ok) {
        throw ("month {0}->{1} failed after {2} attempts" -f $monthStartText, $monthEndText, $maxAttempts)
    }

    Write-Host ("[month-ok] {0}->{1} completed." -f $monthStartText, $monthEndText)
    $cursor = $monthEnd.AddDays(1)
}

Write-Host "[done] monthly bulk download completed."

