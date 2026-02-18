param(
    [string]$ContextApiKey = "",
    [string]$ProjectRoot = "",
    [string]$DataRoot = "",
    [string]$CodexHome = "",
    [switch]$KeepExtra,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
# Avoid treating native stderr warnings as terminating errors.
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
$BaseServers = @("fetch", "filesystem", "sequential-thinking", "mcp-playwright")
$script:CodexBinary = "codex"
$PruneExtra = -not $KeepExtra

function Ensure-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "required_command_missing: $Name"
    }
}

function Resolve-CodexBinary() {
    if (Get-Command "codex.cmd" -ErrorAction SilentlyContinue) {
        return "codex.cmd"
    }
    if (Get-Command "codex" -ErrorAction SilentlyContinue) {
        return "codex"
    }
    throw "required_command_missing: codex"
}

function Invoke-Codex([string[]]$CommandArgs) {
    $cmdPreview = "$script:CodexBinary " + ($CommandArgs -join " ")
    if ($DryRun) {
        Write-Host "[dry-run] $cmdPreview"
        return ""
    }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $script:CodexBinary @CommandArgs 2>$null
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($LASTEXITCODE -ne 0) {
        throw "codex_command_failed: $cmdPreview"
    }
    if ($null -eq $output) {
        return ""
    }
    return ($output | Out-String).Trim()
}

function Remove-McpServer([string]$Name) {
    if ($DryRun) {
        Write-Host "[dry-run] $script:CodexBinary mcp remove $Name"
        return
    }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $script:CodexBinary mcp remove $Name *> $null
    } finally {
        $ErrorActionPreference = $previous
    }
}

function Upsert-McpServer([string]$Name, [string[]]$AddArgs) {
    Remove-McpServer -Name $Name
    [void](Invoke-Codex -CommandArgs $AddArgs)
}

function Resolve-ServerNames([object]$Payload) {
    $names = @()
    if ($null -eq $Payload) {
        return $names
    }

    if ($Payload -is [System.Collections.IEnumerable] -and -not ($Payload -is [string])) {
        foreach ($item in $Payload) {
            $names += Resolve-ServerNames -Payload $item
        }
        return $names | Where-Object { $_ } | Select-Object -Unique
    }

    if ($Payload.PSObject.Properties.Name -contains "name" -and $Payload.name) {
        $names += [string]$Payload.name
    }

    foreach ($key in @("servers", "mcpServers", "items", "data")) {
        if ($Payload.PSObject.Properties.Name -contains $key -and $Payload.$key) {
            $names += Resolve-ServerNames -Payload $Payload.$key
        }
    }

    return $names | Where-Object { $_ } | Select-Object -Unique
}

function Set-TomlSectionKey(
    [System.Collections.Generic.List[string]]$Lines,
    [string]$Section,
    [string]$Key,
    [string]$Value
) {
    $header = "[$Section]"
    $sectionStart = -1
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].Trim() -eq $header) {
            $sectionStart = $i
            break
        }
    }

    if ($sectionStart -lt 0) {
        if ($Lines.Count -gt 0 -and $Lines[$Lines.Count - 1].Trim() -ne "") {
            [void]$Lines.Add("")
        }
        [void]$Lines.Add($header)
        [void]$Lines.Add("$Key = $Value")
        return
    }

    $sectionEnd = $Lines.Count
    for ($i = $sectionStart + 1; $i -lt $Lines.Count; $i++) {
        $trim = $Lines[$i].Trim()
        if ($trim.StartsWith("[") -and $trim.EndsWith("]")) {
            $sectionEnd = $i
            break
        }
    }

    $keyPattern = '^\s*' + [regex]::Escape($Key) + '\s*='
    for ($i = $sectionStart + 1; $i -lt $sectionEnd; $i++) {
        if ($Lines[$i] -match $keyPattern) {
            $Lines[$i] = "$Key = $Value"
            return
        }
    }

    $Lines.Insert($sectionEnd, "$Key = $Value")
}

function Remove-TomlSectionKey(
    [System.Collections.Generic.List[string]]$Lines,
    [string]$Section,
    [string]$Key
) {
    $header = "[$Section]"
    $sectionStart = -1
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].Trim() -eq $header) {
            $sectionStart = $i
            break
        }
    }
    if ($sectionStart -lt 0) {
        return
    }

    $sectionEnd = $Lines.Count
    for ($i = $sectionStart + 1; $i -lt $Lines.Count; $i++) {
        $trim = $Lines[$i].Trim()
        if ($trim.StartsWith("[") -and $trim.EndsWith("]")) {
            $sectionEnd = $i
            break
        }
    }

    $keyPattern = '^\s*' + [regex]::Escape($Key) + '\s*='
    for ($i = $sectionEnd - 1; $i -gt $sectionStart; $i--) {
        if ($Lines[$i] -match $keyPattern) {
            $Lines.RemoveAt($i)
        }
    }
}

function Ensure-CodexConfigDefaults([string]$ConfigPath) {
    if (-not (Test-Path $ConfigPath)) {
        return
    }

    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in (Get-Content -Path $ConfigPath)) {
        [void]$lines.Add([string]$line)
    }

    Set-TomlSectionKey -Lines $lines -Section "features" -Key "multi_agent" -Value "true"
    Remove-TomlSectionKey -Lines $lines -Section "features" -Key "collab"
    Set-TomlSectionKey -Lines $lines -Section "mcp_servers.sequential-thinking" -Key "startup_timeout_sec" -Value "60"
    Set-TomlSectionKey -Lines $lines -Section "mcp_servers.mcp-playwright" -Key "startup_timeout_sec" -Value "60"

    $newContent = ($lines -join [Environment]::NewLine).TrimEnd() + [Environment]::NewLine
    Set-Content -Path $ConfigPath -Value $newContent -Encoding utf8
}

if (-not $DryRun) {
    $script:CodexBinary = Resolve-CodexBinary
    Ensure-Command -Name "npx"
    Ensure-Command -Name "uvx"
} else {
    $script:CodexBinary = "codex"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

if (-not $ProjectRoot) {
    $ProjectRoot = $repoRoot
}
if (-not (Test-Path $ProjectRoot)) {
    throw "project_root_not_found: $ProjectRoot"
}
$ProjectRoot = (Resolve-Path $ProjectRoot).Path

if (-not $DataRoot) {
    if ($env:EMOTIONQUANT_DATA_ROOT) {
        $DataRoot = $env:EMOTIONQUANT_DATA_ROOT
    } else {
        $repoParent = Split-Path -Parent $repoRoot
        $DataRoot = Join-Path $repoParent "EmotionQuant_data"
    }
}
if (-not (Test-Path $DataRoot)) {
    New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null
}
$DataRoot = (Resolve-Path $DataRoot).Path

$npmCache = Join-Path $repoRoot ".tmp\npm-cache"
$uvCache = Join-Path $repoRoot ".tmp\uv-cache"
$uvTools = Join-Path $repoRoot ".tmp\uv-tools"

if (-not $CodexHome) {
    if ($env:CODEX_HOME) {
        $CodexHome = $env:CODEX_HOME
    } else {
        $CodexHome = Join-Path $repoRoot ".tmp\codex-home"
    }
}
$fallbackCodexHome = Join-Path $repoRoot ".tmp\codex-home"
try {
    New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null
} catch {
    if ($CodexHome -ne $fallbackCodexHome) {
        Write-Host "[warn] unable to access CODEX_HOME '$CodexHome'; fallback to '$fallbackCodexHome'."
        New-Item -ItemType Directory -Force -Path $fallbackCodexHome | Out-Null
        $CodexHome = $fallbackCodexHome
    } else {
        throw
    }
}
$CodexHome = (Resolve-Path $CodexHome).Path
$env:CODEX_HOME = $CodexHome

New-Item -ItemType Directory -Force -Path $npmCache | Out-Null
New-Item -ItemType Directory -Force -Path $uvCache | Out-Null
New-Item -ItemType Directory -Force -Path $uvTools | Out-Null

if ($ContextApiKey) {
    try {
        [Environment]::SetEnvironmentVariable("CONTEXT7_API_KEY", $ContextApiKey, "User")
    } catch {
        Write-Host "[warn] unable to persist CONTEXT7_API_KEY at user scope; using process scope."
    }
    $env:CONTEXT7_API_KEY = $ContextApiKey
}

$hasContextApiKey = [bool]$ContextApiKey -or [bool]$env:CONTEXT7_API_KEY
$DesiredServers = @($BaseServers)
if ($hasContextApiKey) {
    $DesiredServers = @("context") + $BaseServers
    Upsert-McpServer -Name "context" -AddArgs @(
        "mcp", "add", "context",
        "--url", "https://mcp.context7.com/mcp",
        "--bearer-token-env-var", "CONTEXT7_API_KEY"
    )
} else {
    Write-Host "[warn] CONTEXT7_API_KEY not set; context MCP skipped."
}

Upsert-McpServer -Name "fetch" -AddArgs @(
    "mcp", "add", "fetch",
    "--env", "UV_CACHE_DIR=$uvCache",
    "--env", "UV_TOOL_DIR=$uvTools",
    "--",
    "uvx", "mcp-server-fetch"
)

Upsert-McpServer -Name "filesystem" -AddArgs @(
    "mcp", "add", "filesystem",
    "--env", "npm_config_cache=$npmCache",
    "--",
    "npx", "-y", "@modelcontextprotocol/server-filesystem",
    $ProjectRoot, $DataRoot
)

Upsert-McpServer -Name "sequential-thinking" -AddArgs @(
    "mcp", "add", "sequential-thinking",
    "--env", "npm_config_cache=$npmCache",
    "--",
    "npx", "-y", "@modelcontextprotocol/server-sequential-thinking"
)

Upsert-McpServer -Name "mcp-playwright" -AddArgs @(
    "mcp", "add", "mcp-playwright",
    "--env", "npm_config_cache=$npmCache",
    "--",
    "npx", "-y", "@playwright/mcp@latest"
)

if (-not $DryRun) {
    $configPath = Join-Path $CodexHome "config.toml"
    Ensure-CodexConfigDefaults -ConfigPath $configPath
}

if ($PruneExtra) {
    if ($DryRun) {
        Write-Host "[dry-run] prune extra MCP servers not in: $($DesiredServers -join ', ')"
    } else {
        $listText = Invoke-Codex -CommandArgs @("mcp", "list", "--json")
        if ($listText) {
            $parsed = $listText | ConvertFrom-Json
            $existingNames = Resolve-ServerNames -Payload $parsed
            foreach ($name in $existingNames) {
                if ($DesiredServers -notcontains $name) {
                    Write-Host "[prune] removing extra MCP server: $name"
                    Remove-McpServer -Name $name
                }
            }
        }
    }
}

$finalList = Invoke-Codex -CommandArgs @("mcp", "list", "--json")
if ($DryRun) {
    Write-Host "[dry-run] target MCP servers: $($DesiredServers -join ', ')"
    return
}

$finalParsed = $null
if ($finalList) {
    $finalParsed = $finalList | ConvertFrom-Json
}
$finalNames = Resolve-ServerNames -Payload $finalParsed

$missing = @()
foreach ($name in $DesiredServers) {
    if ($finalNames -notcontains $name) {
        $missing += $name
    }
}

if ($missing.Count -gt 0) {
    throw "mcp_setup_incomplete_missing: $($missing -join ', ')"
}

Write-Host "[ok] MCP configured: $($DesiredServers -join ', ')"
Write-Output $finalList
