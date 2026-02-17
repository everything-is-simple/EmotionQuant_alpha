param(
    [string]$CodexHome = "",
    [switch]$FailOnMissing
)

$ErrorActionPreference = "Stop"

if (-not $CodexHome) {
    if ($env:CODEX_HOME) {
        $CodexHome = $env:CODEX_HOME
    } elseif ($env:USERPROFILE) {
        $CodexHome = Join-Path $env:USERPROFILE ".codex"
    } else {
        throw "codex_home_not_found"
    }
}

$skillsRoot = Join-Path $CodexHome "skills"

$requiredSkills = @(
    [pscustomobject]@{ Name = "doc"; Candidates = @("doc/SKILL.md") },
    [pscustomobject]@{ Name = "spreadsheet"; Candidates = @("spreadsheet/SKILL.md") },
    [pscustomobject]@{ Name = "jupyter-notebook"; Candidates = @("jupyter-notebook/SKILL.md") },
    [pscustomobject]@{ Name = "playwright"; Candidates = @("playwright/SKILL.md") },
    [pscustomobject]@{ Name = "pdf"; Candidates = @("pdf/SKILL.md") },
    [pscustomobject]@{ Name = "skill-creator"; Candidates = @(".system/skill-creator/SKILL.md", "skill-creator/SKILL.md") }
)

$rows = @()
$missing = @()

foreach ($skill in $requiredSkills) {
    $foundPath = $null
    foreach ($candidate in $skill.Candidates) {
        $candidatePath = Join-Path $skillsRoot $candidate
        if (Test-Path $candidatePath) {
            $foundPath = $candidatePath
            break
        }
    }

    if ($foundPath) {
        $rows += [pscustomobject]@{
            skill = $skill.Name
            status = "installed"
            path = $foundPath
        }
    } else {
        $missing += $skill.Name
        $rows += [pscustomobject]@{
            skill = $skill.Name
            status = "missing"
            path = "-"
        }
    }
}

Write-Host "[skills] CODEX_HOME=$CodexHome"
$rows | Format-Table -AutoSize

if ($missing.Count -gt 0) {
    Write-Host "[warn] missing skills: $($missing -join ', ')"
    Write-Host "[hint] use skill-installer to install missing skills."
    if ($FailOnMissing) {
        exit 1
    }
} else {
    Write-Host "[ok] required skills are installed."
}
