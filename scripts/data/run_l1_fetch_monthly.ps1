param(
    [Parameter(Mandatory = $true)]
    [string]$Start,
    [Parameter(Mandatory = $true)]
    [string]$End,
    [int]$Workers = 3,
    [int]$RetryMax = 3,
    [double]$MaxMonthMinutes = 20,
    [int]$StatusPollSeconds = 10,
    [switch]$NoProgress,
    [switch]$UseEq,
    [string]$PythonExe = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Parse-TradeDate {
    param([string]$Value)
    return [datetime]::ParseExact($Value, "yyyyMMdd", [System.Globalization.CultureInfo]::InvariantCulture)
}

function Get-MonthEnd {
    param([datetime]$Value)
    return (Get-Date -Year $Value.Year -Month $Value.Month -Day 1).AddMonths(1).AddDays(-1)
}

function Get-Runner {
    $resolvedPythonExe = $PythonExe
    if ($UseEq) {
        if (-not (Get-Command eq -ErrorAction SilentlyContinue)) {
            throw "eq command not found. Remove -UseEq or install eq in current environment."
        }
        return @{ Exe = "eq"; Prefix = @() }
    }
    if (-not $resolvedPythonExe) {
        $venvPython = Join-Path (Get-Location).Path ".venv\Scripts\python.exe"
        if (Test-Path $venvPython) {
            $resolvedPythonExe = $venvPython
        } else {
            $resolvedPythonExe = "python"
        }
    }
    return @{ Exe = $resolvedPythonExe; Prefix = @("-m", "src.pipeline.main") }
}

function Get-ActiveFetchPipelineProcesses {
    return @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "^python(\.exe)?$" -and
        $_.CommandLine -match "src\.pipeline\.main\s+fetch-(batch|retry)"
    })
}

function Assert-NoConcurrentFetchPipelineProcess {
    $active = Get-ActiveFetchPipelineProcesses
    if ($active.Count -le 0) {
        return
    }
    $lines = @()
    foreach ($proc in $active) {
        $cmd = [string]$proc.CommandLine
        if ($cmd.Length -gt 200) {
            $cmd = $cmd.Substring(0, 200) + "..."
        }
        $lines += ("pid={0} name={1} cmd={2}" -f $proc.ProcessId, $proc.Name, $cmd)
    }
    throw ("concurrent_fetch_process_detected`n{0}" -f ($lines -join "`n"))
}

function Invoke-Runner {
    param(
        [hashtable]$Runner,
        [string[]]$CommandArgs
    )
    if ($Runner.Exe -eq "python") {
        $allArgs = @()
        $allArgs += @($Runner.Prefix)
        $allArgs += @($CommandArgs)
        $raw = & $Runner.Exe @allArgs
    } else {
        $raw = & $Runner.Exe @CommandArgs
    }
    $code = [int]$LASTEXITCODE
    if ($null -ne $raw) {
        $raw | ForEach-Object { Write-Host $_ }
    }
    return @{ ExitCode = $code; Output = $raw }
}

function Read-Status {
    param([hashtable]$Runner)
    $result = Invoke-Runner -Runner $Runner -CommandArgs @("fetch-status")
    if ($result.ExitCode -ne 0) {
        throw "fetch-status failed with exit code $($result.ExitCode)"
    }
    $jsonLine = ($result.Output | Select-Object -Last 1)
    if (-not $jsonLine) {
        throw "fetch-status returned empty output."
    }
    return ($jsonLine | ConvertFrom-Json)
}

function Test-FatalRuntimeSignal {
    param(
        [string]$StdoutLog,
        [string]$StderrLog
    )

    $patterns = @(
        "Fatal Python error",
        "PyEval_SaveThread",
        "Python runtime state:"
    )
    foreach ($path in @($StdoutLog, $StderrLog)) {
        if (-not (Test-Path $path)) {
            continue
        }
        $content = Get-Content -Path $path -Raw -ErrorAction SilentlyContinue
        if (-not $content) {
            continue
        }
        foreach ($pattern in $patterns) {
            if ($content -like ("*" + $pattern + "*")) {
                return $true
            }
        }
    }
    return $false
}

function Invoke-FetchBatchProcess {
    param(
        [hashtable]$Runner,
        [string[]]$FetchArgs,
        [string]$MonthStartText,
        [string]$MonthEndText,
        [double]$MaxMonthMinutes,
        [int]$StatusPollSeconds,
        [int]$AttemptIndex
    )

    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $timeoutSeconds = [int][math]::Ceiling($MaxMonthMinutes * 60)
    if ($timeoutSeconds -le 0) {
        throw "MaxMonthMinutes must be > 0."
    }

    $stateDir = Join-Path "artifacts/spiral-s3a" "_state"
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
    $suffix = ""
    if ($AttemptIndex -gt 0) {
        $suffix = ".attempt$AttemptIndex"
    }
    $stdoutLog = Join-Path $stateDir ("monthly-{0}-{1}{2}.stdout.log" -f $MonthStartText, $MonthEndText, $suffix)
    $stderrLog = Join-Path $stateDir ("monthly-{0}-{1}{2}.stderr.log" -f $MonthStartText, $MonthEndText, $suffix)

    if ($Runner.Exe -eq "python") {
        $processArgs = @()
        $processArgs += @($Runner.Prefix)
        $processArgs += @($FetchArgs)
    } else {
        $processArgs = @($FetchArgs)
    }

    $proc = Start-Process `
        -FilePath $Runner.Exe `
        -ArgumentList $processArgs `
        -WorkingDirectory (Get-Location).Path `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru

    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    $nextPoll = (Get-Date).AddSeconds($StatusPollSeconds)
    while (-not $proc.HasExited) {
        Start-Sleep -Seconds 1
        if ((Get-Date) -ge $deadline) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            throw ("month {0}->{1} exceeded hard timeout {2} minutes; process killed." -f $MonthStartText, $MonthEndText, $MaxMonthMinutes)
        }
        if ((Get-Date) -ge $nextPoll) {
            try {
                $heartbeat = Read-Status -Runner $Runner
                $tradeDateText = "-"
                if ($heartbeat.PSObject.Properties.Name -contains "current_trade_date" -and $heartbeat.current_trade_date) {
                    $tradeDateText = [string]$heartbeat.current_trade_date
                }
                $tradeIndex = 0
                if ($heartbeat.PSObject.Properties.Name -contains "current_trade_index" -and $null -ne $heartbeat.current_trade_index) {
                    $tradeIndex = [int]$heartbeat.current_trade_index
                }
                $tradeTotal = 0
                if ($heartbeat.PSObject.Properties.Name -contains "current_trade_total" -and $null -ne $heartbeat.current_trade_total) {
                    $tradeTotal = [int]$heartbeat.current_trade_total
                }
                Write-Host (
                    "[heartbeat] status={0} batch={1}/{2} trade={3} {4}/{5}" -f `
                        $heartbeat.status, `
                        $heartbeat.completed_batches, `
                        $heartbeat.total_batches, `
                        $tradeDateText, `
                        $tradeIndex, `
                        $tradeTotal
                )
            } catch {
                Write-Host ("[heartbeat] fetch-status unavailable: {0}" -f $_.Exception.Message)
            }
            $nextPoll = (Get-Date).AddSeconds($StatusPollSeconds)
        }
    }

    $fetchExitCode = [int]$proc.ExitCode
    $watch.Stop()
    if (Test-Path $stdoutLog) {
        Get-Content $stdoutLog | ForEach-Object { Write-Host $_ }
    }
    if (Test-Path $stderrLog) {
        Get-Content $stderrLog | ForEach-Object { Write-Host $_ }
    }

    $elapsedMinutes = [math]::Round($watch.Elapsed.TotalMinutes, 2)
    Write-Host ("[month-run] elapsed_minutes={0} exit_code={1}" -f $elapsedMinutes, $fetchExitCode)

    $fatalDetected = Test-FatalRuntimeSignal -StdoutLog $stdoutLog -StderrLog $stderrLog
    if ($fatalDetected) {
        Write-Host ("[warn] fatal runtime signature detected in logs: {0} | {1}" -f $stdoutLog, $stderrLog)
    }

    return @{
        ExitCode = $fetchExitCode
        ElapsedMinutes = $elapsedMinutes
        StdoutLog = $stdoutLog
        StderrLog = $stderrLog
        FatalDetected = $fatalDetected
    }
}

$startDate = Parse-TradeDate -Value $Start
$endDate = Parse-TradeDate -Value $End
if ($endDate -lt $startDate) {
    throw "End must be >= Start"
}
if ($StatusPollSeconds -le 0) {
    throw "StatusPollSeconds must be > 0."
}

$runner = Get-Runner
Write-Host ("[runner] exe={0}" -f $runner.Exe)
$cursor = $startDate

while ($cursor -le $endDate) {
    $monthEnd = Get-MonthEnd -Value $cursor
    if ($monthEnd -gt $endDate) {
        $monthEnd = $endDate
    }

    $monthStartText = $cursor.ToString("yyyyMMdd")
    $monthEndText = $monthEnd.ToString("yyyyMMdd")

    Write-Host ("[month] {0} -> {1}" -f $monthStartText, $monthEndText)
    Assert-NoConcurrentFetchPipelineProcess

    $fetchArgs = @(
        "fetch-batch",
        "--start", $monthStartText,
        "--end", $monthEndText,
        "--batch-size", "1",
        "--batch-unit", "month",
        "--workers", $Workers.ToString()
    )
    if ($NoProgress) {
        $fetchArgs += "--no-progress"
    }

    $status = $null
    $runResult = $null
    $fetchAttempt = 0
    $maxFetchAttempts = [Math]::Max(1, $RetryMax + 1)
    while ($fetchAttempt -lt $maxFetchAttempts) {
        if ($fetchAttempt -gt 0) {
            Write-Host ("[resume] month={0}->{1} rerun fetch-batch attempt={2}/{3}" -f $monthStartText, $monthEndText, ($fetchAttempt + 1), $maxFetchAttempts)
        }

        $runResult = Invoke-FetchBatchProcess `
            -Runner $runner `
            -FetchArgs $fetchArgs `
            -MonthStartText $monthStartText `
            -MonthEndText $monthEndText `
            -MaxMonthMinutes $MaxMonthMinutes `
            -StatusPollSeconds $StatusPollSeconds `
            -AttemptIndex $fetchAttempt

        if ([int]$runResult.ExitCode -ne 0) {
            Write-Host "[warn] fetch-batch failed, try fetch-retry rounds"
        }

        $status = Read-Status -Runner $runner
        $retryRound = 0
        while ($status.status -ne "completed" -and [int]$status.failed_batches -gt 0 -and $retryRound -lt $RetryMax) {
            $retryRound += 1
            Write-Host ("[retry] month={0}->{1} round={2}/{3}" -f $monthStartText, $monthEndText, $retryRound, $RetryMax)
            $retryResult = Invoke-Runner -Runner $runner -CommandArgs @("fetch-retry")
            if ($retryResult.ExitCode -ne 0) {
                Write-Host ("[warn] fetch-retry exit code={0}" -f $retryResult.ExitCode)
            }
            $status = Read-Status -Runner $runner
        }

        if ($status.status -eq "completed") {
            break
        }

        if ([int]$status.failed_batches -eq 0) {
            if ($runResult.FatalDetected) {
                Write-Host "[warn] status still not completed after fatal runtime; will resume from checkpoint."
            } else {
                Write-Host "[warn] status is not completed but failed_batches=0; will resume from checkpoint."
            }
            $fetchAttempt += 1
            continue
        }

        break
    }

    if ($status.status -ne "completed") {
        throw ("month {0}->{1} not completed: status={2}, failed_batches={3}, fetch_exit={4}, fatal_detected={5}" -f $monthStartText, $monthEndText, $status.status, $status.failed_batches, $runResult.ExitCode, $runResult.FatalDetected)
    }

    Write-Host ("[month-ok] {0}->{1} completed={2}/{3}" -f $monthStartText, $monthEndText, $status.completed_batches, $status.total_batches)
    $cursor = $monthEnd.AddDays(1)
}

Write-Host "[done] monthly fetch completed."
