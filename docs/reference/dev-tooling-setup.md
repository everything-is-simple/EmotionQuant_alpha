# 开发工具链基线（MCP / Skills / Hooks）

本文件定义仓库推荐的最小开发工具链配置，并提供可执行命令。

## 1. MCP（5 个基线）

目标服务器：
- `filesystem`
- `sequential-thinking`
- `context`
- `fetch`
- `mcp-playwright`

执行命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup/configure_mcp.ps1
```

说明：
- 默认会清理非基线 MCP，保留项目必需 5 项。
- 如需保留额外 MCP：追加 `-KeepExtra`。
- 默认写入项目级 `CODEX_HOME`：`<repo>/.tmp/codex-home`（避免权限与全局污染）。
- 如需写入其它位置：追加 `-CodexHome <path>`。
- `context` 需要 `CONTEXT7_API_KEY`（可通过 `-ContextApiKey` 传入）。

## 2. Skills（6 个高频）

目标技能：
- `doc`
- `spreadsheet`
- `jupyter-notebook`
- `playwright`
- `pdf`
- `skill-creator`

检查命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup/check_skills.ps1
```

## 3. Git Hooks（3 个门禁）

启用命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup/configure_git_hooks.ps1
```

启用后生效的 hook：
- `pre-commit`：硬编码路径/密钥扫描、TODO/HACK/FIXME 与 debt 记录联动、必要时触发 contracts/governance 检查
- `commit-msg`：提交信息必须包含 `spiral-sN` 或 `CP-xx`
- `pre-push`：执行 `python -m scripts.quality.local_quality_check --contracts --governance` 与 `pytest`

## 4. 一键启动（推荐）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup/bootstrap_dev_tooling.ps1
```
