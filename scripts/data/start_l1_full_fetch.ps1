param(
    [string]$Start = "20100101",
    [string]$End = (Get-Date -Format "yyyyMMdd"),
    [int]$BatchSize = 365,
    [int]$Workers = 3,
    [int]$RetryMax = 10,
    [switch]$Foreground,
    [switch]$NoProgress,
    [switch]$StatusOnly,
    [switch]$RunnerStatus,
    [switch]$StopRunner,
    [switch]$RetryOnly,
    [switch]$RetryUnlock,
    [switch]$UseEq
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runScriptPath = Join-Path $scriptDir "run_l1_fetch.ps1"
if (-not (Test-Path $runScriptPath)) {
    throw "run_l1_fetch.ps1 not found: $runScriptPath"
}

$invokeArgs = @("-ExecutionPolicy", "Bypass", "-File", $runScriptPath)

if ($StatusOnly) {
    $invokeArgs += "-StatusOnly"
} elseif ($RunnerStatus) {
    $invokeArgs += "-RunnerStatus"
} elseif ($StopRunner) {
    $invokeArgs += "-StopRunner"
} elseif ($RetryOnly) {
    $invokeArgs += @("-RetryOnly", "-RetryMax", $RetryMax.ToString())
} elseif ($RetryUnlock) {
    $invokeArgs += @("-RetryUnlock", "-RetryMax", $RetryMax.ToString())
} else {
    $invokeArgs += @(
        "-Start", $Start,
        "-End", $End,
        "-BatchSize", $BatchSize.ToString(),
        "-Workers", $Workers.ToString(),
        "-RetryMax", $RetryMax.ToString()
    )
    if (-not $Foreground) {
        $invokeArgs += "-Background"
    }
}

if ($NoProgress) {
    $invokeArgs += "-NoProgress"
}
if ($UseEq) {
    $invokeArgs += "-UseEq"
}

Write-Host ("[l1-full-fetch] powershell {0}" -f ($invokeArgs -join " "))
& powershell @invokeArgs
exit $LASTEXITCODE

