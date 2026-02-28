# AGENTS.en.md

This file provides minimal, executable repository rules for automated agents. Content is equivalent to `AGENTS.md`, `CLAUDE.md`, `CLAUDE.en.md`, `WARP.md`, and `WARP.en.md`, targeting generic agent runtimes.

---

## 1. Document positioning

- Purpose: minimal, executable repository rules for automated agents.
- Single execution baseline: `docs/design/enhancements/eq-improvement-plan-core-frozen.md` (`docs/design/enhancements/enhancement-selection-analysis_claude-opus-max_20260210.md` serves only as selection rationale input).
- Authoritative architecture entry: `docs/system-overview.md`
- Authoritative capability-status entry: `docs/roadmap.md` (R0-R9 roadmap)
- Authoritative governance entry: `Governance/steering/`
- Authoritative execution-card entry: `docs/cards/` (R0-R9 execution cards)

---

## 2. System positioning

EmotionQuant is a sentiment-driven quantitative system for China A-shares.

- Solo developer project
- Execution model: **micro-spiral closed-loop** (formerly Spiral, upgraded to R0-R9 Rebuild roadmap as of 2026-02-28)
- Default cadence: 7 days per spiral; each must produce `run/test/artifact/review/sync`
- Docs serve implementation — no "docs perfection" pursuit

---

## 3. Non-negotiables (7 iron rules, zero tolerance)

| # | Rule | Core requirement |
|---|------|-----------------|
| 1 | Sentiment-first | Signal logic must center on sentiment factors |
| 2 | No single-indicator decisions | Technical indicators may be contrast/auxiliary features, but must be jointly validated with sentiment factors; must not independently trigger trades |
| 3 | Local-data first | Main pipeline reads local data; remote is for supplementation only; gaps must land in DB before entering main pipeline |
| 4 | No hardcoded paths/secrets | Must use `Config.from_env()` or env vars |
| 5 | A-share rules enforced | T+1, price limits (main board 10% / ChiNext & STAR 20% / ST 5%), trading sessions, SW industry classification |
| 6 | Micro-spiral closure mandatory | Each spiral must have all five closure artifacts; no closure without all five |
| 7 | Docs serve implementation | No doc bloat blocking development; minimal sync first |

**Technical indicator boundary**: the historical archive's "absolute zero technical indicator ban" is NOT the current calibration. MA/RSI/MACD etc. may be used for contrast experiments or feature engineering, but must not serve as independent buy/sell signals.

**Authoritative detail**: `Governance/steering/系统铁律.md`

---

## 4. 6A workflow (micro-spiral closed-loop)

### 4.1 Six-step definition

| Stage | Name | Core action |
|-------|------|-------------|
| A1 | Align | Define primary objective and In/Out Scope |
| A2 | Architect | Pick 1-3 CP Slices, define cross-module contracts |
| A3 | Act | Minimal implementation + at least 1 automated test |
| A4 | Assert | run/test/artifact all reproducibly verified |
| A5 | Archive | Produce review.md + final.md, organize evidence chain |
| A6 | Advance | Minimal sync of 5 items, advance roadmap status |

### 4.2 Execution constraints

1. Only **1 primary objective** per spiral
2. Only **1-3 CP Slices** per spiral
3. Any single task exceeding 1 day must be further decomposed
4. Default flow: `Scope → Build → Verify → Sync`
5. Escalate to Strict 6A for: trading path changes, risk control changes, data contract breaking changes, critical new external dependencies

### 4.3 Exit conditions

The spiral must NOT close if any of the following is missing:
- No runnable command / no automated test / no artifact / no review record / no sync record

### 4.4 Branch strategy

- Default merge target: `main`
- Dev branch naming: `rebuild/r{N}-{module}`
- If `develop` branch is later adopted: `feature → develop → main (milestone release)`

### 4.5 Per-spiral minimal sync (4 items)

1. `Governance/record/development-status.md`
2. `Governance/record/debts.md`
3. `docs/roadmap.md` — corresponding stage status
4. `docs/cards/` — corresponding card checklist

**Authoritative workflow**: `Governance/steering/6A-WORKFLOW.md`

---

## 5. Naming conventions

**Mandatory**: code in English; comments/docs/UI in Chinese.

### 5.1 Sentiment cycle (MssCycle enum)

| English | Chinese | Temperature condition |
|---------|---------|---------------------|
| emergence | 萌芽期 | <30°C + up |
| fermentation | 发酵期 | 30-45°C + up |
| acceleration | 加速期 | 45-60°C + up |
| divergence | 分歧期 | 60-75°C + up/sideways |
| climax | 高潮期 | ≥75°C |
| diffusion | 扩散期 | 60-75°C + down |
| recession | 退潮期 | <60°C + down/sideways |
| unknown | 异常兜底 | abnormal input or indeterminate |

### 5.2 Trend direction (Trend enum)

`up` / `down` / `sideways` (do NOT use `flat`)

### 5.3 PAS direction (PasDirection enum)

`bullish` / `bearish` / `neutral`

### 5.4 Rotation status (RotationStatus enum)

`IN` / `OUT` / `HOLD`

### 5.5 Recommendation grade

`STRONG_BUY`(≥75) / `BUY`(≥70) / `HOLD`(50-69) / `SELL`(30-49) / `AVOID`(<30)

### 5.6 Field conventions

- Uniform `snake_case`
- Internal stock code: `stock_code` (6-digit, e.g. `000001`)
- External stock code: `ts_code` (TuShare format, e.g. `000001.SZ`)
- Use `risk_reward_ratio` (not `rr_ratio`)
- Cross-module contract version field: `contract_version` (current `nc-v1`)

**Authoritative naming spec**: `docs/naming-conventions.md`
**Machine-readable naming schema**: `docs/naming-contracts.schema.json`
**Glossary / change template**: `docs/naming-contracts-glossary.md` / `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md`

---

## 6. Data architecture

### 6.1 Storage strategy

Parquet + DuckDB single-DB preferred (`DUCKDB_DIR/emotionquant.duckdb`). Sharding only enabled after performance threshold is hit.

### 6.2 Four-layer architecture

| Layer | Content |
|-------|---------|
| L1 | Raw data (raw_*), externally collected, no computation |
| L2 | Features & snapshots (market_snapshot / industry_snapshot / stock_gene_cache) |
| L3 | Algorithm output + Validation output (validation_gate_decision / validation_weight_plan) |
| L4 | Analysis artifacts (reports/metrics) |

**Dependency rule**: L2 reads only L1; L3 reads only L1/L2; L4 reads only L1/L2/L3. Reverse dependencies forbidden.

### 6.3 Path management

```python
# ✅ Required
from utils.config import Config
config = Config.from_env()
db_path = config.database_path

# ❌ Forbidden
db_path = "data/emotionquant.db"
cache_dir = "G:/EmotionQuant_data/"
```

---

## 7. Architecture (eight layers)

| Layer | Responsibility |
|-------|---------------|
| Data Layer | Raw data collection & cleaning |
| Signal Layer | MSS/IRS/PAS computation |
| Validation Layer | Factor validation + weight validation (independent module) |
| Integration Layer | Signal integration & recommendation generation |
| Backtest Layer | Reproducible backtesting |
| Trading Layer | Paper trading / risk control execution |
| Analysis Layer | Performance attribution & daily reports |
| GUI Layer | Visualization (Streamlit + Plotly) |

---

## 8. Governance structure

### 8.1 Directory positioning

| Directory | Role |
|-----------|------|
| `docs/design/` | Design baseline (three tiers: core algorithms / core infrastructure / enhancements) |
| `docs/design/core-algorithms/` | Core algorithm design (MSS/IRS/PAS/Validation/Integration) |
| `docs/design/core-infrastructure/` | Core infrastructure design (Data/Backtest/Trading/GUI/Analysis) |
| `docs/design/enhancements/` | Improvement action plans unified entry |
| `Governance/steering/` | Iron rules, principles, workflow |
| `docs/roadmap.md` | R0-R9 roadmap |
| `docs/cards/` | R0-R9 execution cards |
| `Governance/record/` | Status, debts, reusable assets |
| `.reports/` | Reports (filenames include date-time) |
| `.reports/archive-*/` | Historical archives (read-only) |

### 8.2 Single source of truth (SoT)

| Scenario | Authoritative file |
|----------|-------------------|
| Capability status (roadmap) | `docs/roadmap.md` |
| Execution cards | `docs/cards/README.md` |
| 6A workflow | `Governance/steering/6A-WORKFLOW.md` |
| Iron rules | `Governance/steering/系统铁律.md` |
| Core principles | `Governance/steering/CORE-PRINCIPLES.md` |
| Improvement action plan | `docs/design/enhancements/eq-improvement-plan-core-frozen.md` |
| Design-alignment action card | `Governance/archive/archive-spiral-roadmap-v5-20260228/execution-cards/DESIGN-ALIGNMENT-ACTION-CARD.md` (archived) |
| Naming conventions | `docs/naming-conventions.md` |
| Naming contracts schema | `docs/naming-contracts.schema.json` |
| Naming contracts glossary/template | `docs/naming-contracts-glossary.md` / `Governance/steering/NAMING-CONTRACT-CHANGE-TEMPLATE.md` |
| System overview | `docs/system-overview.md` |
| Module index | `docs/module-index.md` |

### 8.3 Archiving rules

- Roadmap model generational changes must be archived: `archive-{model}-{version}-{date}`
- Archive directories are read-only, no further iteration
- Spiral roadmap model has been archived to `Governance/archive/archive-spiral-roadmap-v5-20260228/`

---

## 9. Quality gates

### 9.1 Mandatory gates

- Command runnable, tests reproducible, artifacts inspectable
- Hardcoded-path check, A-share rule check, local-data check
- Contracts/governance consistency check: `python -m scripts.quality.local_quality_check --contracts --governance`

### 9.2 Pre-merge cleanup

- TODO/HACK/FIXME: allowed during development, must be cleaned or logged to `Governance/record/debts.md` before merge

### 9.3 Principles

- Effective tests over coverage numbers
- Closure over expansion

---

## 10. Core algorithm constraints

- MSS / IRS / PAS operate as **co-equal peers**; Integration Layer must not bias toward or hard-veto based on a single algorithm
- All three algorithms share sentiment factors as common input, maintaining consistent sentiment calibration
- Validation Layer is an independent module responsible for factor validity verification and weight plan verification, outputting Gate decisions (PASS/WARN/FAIL)
- Integration Layer consumes Gate decisions for signal integration, outputs `integrated_recommendation`

---

## 11. Tech stack

- Python `>=3.10`
- Data: Parquet + DuckDB (single-DB preferred)
- GUI: Streamlit + Plotly
- Backtest primary: Qlib (research & experiments); execution baseline: local vectorized backtester; compatibility adapter: backtrader (optional, not mainline)

Details: `pyproject.toml`, `docs/design/core-infrastructure/backtest/backtest-engine-selection.md`

---

## 12. Repository remote

- `origin`: `${REPO_REMOTE_URL}` (defined in `.env.example`)

---

## 13. Historical note

- Legacy linear docs archived at: `Governance/archive/archive-legacy-linear-v4-20260207/`
- Legacy workflow files have been merged into `Governance/steering/6A-WORKFLOW.md` (no separate archive directory is retained).
- This file no longer maintains linear Stage narratives.
- Spiral roadmap (`Governance/SpiralRoadmap/`) has been archived to `Governance/archive/archive-spiral-roadmap-v5-20260228/`; new roadmap at `docs/roadmap.md`.

---

## 14. Design Alignment And Debt Cards

> Spiral-era design-alignment and debt cards have been archived to `Governance/archive/archive-spiral-roadmap-v5-20260228/execution-cards/`.
> R0-R9 execution cards are at `docs/cards/`; status syncs with `docs/roadmap.md` and `Governance/record/debts.md`.

## 15. Tooling Note

- `.claude/` is retained as historical tooling assets; do not treat `.claude` commands as canonical workflow requirements.
- Reusable governance rules have been migrated to `Governance/steering/`.
- `Governance/Capability/` has been retired and archived to `Governance/archive/archive-capability-v8-20260223/`.

## 16. Git Auth Baseline

- TLS backend baseline: prefer `openssl` (`git config --global http.sslbackend openssl`; repo-local override allowed).
- In sandbox-restricted sessions, authenticated `git push` should run outside sandbox/escalated mode to ensure credential prompt/storage paths are accessible.

## 17. MCP Baseline

Recommended MCP servers for this repo:
- `context` (Context7 docs/context retrieval)
- `fetch` (HTTP content retrieval)
- `filesystem` (cross-workspace file operations)
- `sequential-thinking` (explicit multi-step reasoning)
- `mcp-playwright` (browser automation)

Skill vs MCP boundary:
- Skills are workflow instructions/templates.
- MCP servers are runtime tools.
- Skills do **not** replace MCP tools.

Usage triggers (default policy):
- Use `context` when API/framework docs or version-sensitive references are needed.
- Use `fetch` for direct URL content extraction where browser rendering is unnecessary.
- Use `filesystem` for non-trivial file discovery/read-write across allowed roots.
- Use `sequential-thinking` for complex decomposition, debugging trees, and decision branching.
- Use `mcp-playwright` for UI flows, JS-rendered pages, screenshots, and interaction replay.

Bootstrap:
- One-shot bootstrap: `powershell -ExecutionPolicy Bypass -File scripts/setup/bootstrap_dev_tooling.ps1`
- MCP only: `powershell -ExecutionPolicy Bypass -File scripts/setup/configure_mcp.ps1 -ContextApiKey <your_key>`
- Optional MCP target path: `-CodexHome <path>` (default: project-local `.tmp/codex-home`)
- Hooks only: `powershell -ExecutionPolicy Bypass -File scripts/setup/configure_git_hooks.ps1`
- Skills check only: `powershell -ExecutionPolicy Bypass -File scripts/setup/check_skills.ps1`
