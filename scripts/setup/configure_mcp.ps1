param(
    [string]$ContextApiKey = ""
)

$ErrorActionPreference = "Stop"

function Ensure-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "required_command_missing: $Name"
    }
}

function Upsert-McpServer([string]$Name, [string[]]$AddArgs) {
    & codex mcp remove $Name *> $null
    & codex @AddArgs
}

Ensure-Command -Name "codex"
Ensure-Command -Name "npx"
Ensure-Command -Name "uvx"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$npmCache = Join-Path $repoRoot ".tmp\npm-cache"
$uvCache = Join-Path $repoRoot ".tmp\uv-cache"
$uvTools = Join-Path $repoRoot ".tmp\uv-tools"

New-Item -ItemType Directory -Force -Path $npmCache | Out-Null
New-Item -ItemType Directory -Force -Path $uvCache | Out-Null
New-Item -ItemType Directory -Force -Path $uvTools | Out-Null

if ($ContextApiKey) {
    [Environment]::SetEnvironmentVariable("CONTEXT7_API_KEY", $ContextApiKey, "User")
}

Upsert-McpServer -Name "context" -AddArgs @(
    "mcp", "add", "context",
    "--url", "https://mcp.context7.com/mcp",
    "--bearer-token-env-var", "CONTEXT7_API_KEY"
)

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
    "G:\EmotionQuant-alpha", "G:\EmotionQuant_data"
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

& codex mcp list --json
