param(
    [switch]$Disable
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

Set-Location $repoRoot

if ($Disable) {
    & git config --local --unset core.hooksPath *> $null
    Write-Host "[ok] git hooks disabled (core.hooksPath unset)."
    exit 0
}

$requiredHooks = @(
    ".githooks/pre-commit",
    ".githooks/commit-msg",
    ".githooks/pre-push"
)

foreach ($hook in $requiredHooks) {
    if (-not (Test-Path $hook)) {
        throw "required_hook_missing: $hook"
    }
}

& git config --local core.hooksPath ".githooks"
$activePath = (& git config --local --get core.hooksPath).Trim()
if ($activePath -ne ".githooks") {
    throw "set_hooks_path_failed"
}

Write-Host "[ok] git hooks enabled via core.hooksPath=.githooks"
