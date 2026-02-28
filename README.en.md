# EmotionQuant

EmotionQuant is a sentiment-driven quantitative system for China A-shares, executed with a micro-spiral closed-loop model (R0-R9 Rebuild roadmap).

## Alignment Status (2026-02-28)

- Core design SoT: `docs/design/**` + `docs/system-overview.md`
- Roadmap SoT: `docs/roadmap.md` (R0-R9)
- R0-R9 execution cards: `docs/cards/`
- Spiral-era action cards archived: `Governance/archive/archive-spiral-roadmap-v5-20260228/execution-cards/`
- Debt registry: `Governance/record/debts.md`

## Core Execution Principles

1. Sentiment-first; technical indicators must not independently trigger trading.
2. Local-data first; remote is supplemental and must land locally before main flow consumption.
3. Paths/secrets must come from `Config.from_env()` or environment variables.
4. A-share rules are mandatory (T+1, price limits, trading sessions, SW industry taxonomy).
5. Every spiral must close with `run/test/artifact/review/sync` evidence.

## Authoritative Entry Points

- System overview: `docs/system-overview.md`
- Module index: `docs/module-index.md`
- Master plan: `docs/design/enhancements/eq-improvement-plan-core-frozen.md`
- Naming conventions: `docs/naming-conventions.md`
- Naming contracts schema: `docs/naming-contracts.schema.json`
- Governance rules: `Governance/steering/`
- Execution-card index: `docs/cards/README.md`

## Data Download (Fast Historical Backfill)

Current L1 backfill primary tool: `scripts/data/bulk_download.py`

```bash
# Direct run (recommended)
python scripts/data/bulk_download.py --start 20080101 --end 20260225 --skip-existing

# PowerShell wrapper (background/status/retry)
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -Start 20080101 -End 20260225 -Background -SkipExisting
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StatusOnly
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -RunnerStatus
powershell -ExecutionPolicy Bypass -File scripts/data/run_l1_fetch.ps1 -StopRunner

# Dual-token health check / channel-window benchmark
python scripts/data/check_tushare_dual_tokens.py --env-file .env --channels both
python scripts/data/benchmark_tushare_l1_channels_window.py --env-file .env --start 20250101 --end 20250131 --channels both
```

## Setup And Quality Gates

```bash
# Runtime
pip install -r requirements.txt

# Development deps
pip install -r requirements-dev.txt

# Tests
pytest -v

# Contract/governance consistency gate
python -m scripts.quality.local_quality_check --contracts --governance
```

## Directory Map

- `src/`: implementation code
- `tests/`: automated tests
- `docs/`: design and specs
- `Governance/`: roadmap, execution cards, governance, records
- `scripts/`: engineering scripts (data download, quality checks, tooling bootstrap)

## Repository Remotes

- `origin`: `${REPO_REMOTE_URL}` (see `.env.example`)
- `backup`: `${REPO_BACKUP_REMOTE_URL}` (see `.env.example`)

## License

MIT (authoritative text in `LICENSE`)
