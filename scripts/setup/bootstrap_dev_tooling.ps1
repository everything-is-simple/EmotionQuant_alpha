param(
    [string]$ContextApiKey = "",
    [string]$ProjectRoot = "",
    [string]$DataRoot = "",
    [string]$CodexHome = "",
    [switch]$KeepExtraMcp,
    [switch]$SkipMcp,
    [switch]$SkipHooks,
    [switch]$SkipSkills,
    [switch]$FailOnMissingSkills
)

$ErrorActionPreference = "Stop"
$originalCodexHome = $env:CODEX_HOME

if (-not $SkipMcp) {
    & (Join-Path $PSScriptRoot "configure_mcp.ps1") `
        -ContextApiKey $ContextApiKey `
        -ProjectRoot $ProjectRoot `
        -DataRoot $DataRoot `
        -CodexHome $CodexHome `
        -KeepExtra:$KeepExtraMcp
}

if (-not $SkipHooks) {
    & (Join-Path $PSScriptRoot "configure_git_hooks.ps1")
}

if (-not $SkipSkills) {
    if ($null -ne $originalCodexHome) {
        $env:CODEX_HOME = $originalCodexHome
    } else {
        Remove-Item Env:CODEX_HOME -ErrorAction SilentlyContinue
    }
    & (Join-Path $PSScriptRoot "check_skills.ps1") -FailOnMissing:$FailOnMissingSkills
}

Write-Host "[ok] developer tooling bootstrap completed."
