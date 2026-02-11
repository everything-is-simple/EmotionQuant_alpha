# EmotionQuant

EmotionQuant is a sentiment-driven quantitative system for China A-shares.
The project now follows a **Spiral closed-loop model** instead of a linear Stage pipeline.

## Current status (Truth First)

- Repository status: `Skeleton + documentation baseline`.
- Design, roadmap, and governance are aligned to Spiral execution.
- Production-grade business loops are not finished yet; implementation starts from `S0`.

## Core principles

1. Sentiment-first; a single technical indicator must not independently trigger trading.
2. Local data is the default source; remote APIs are supplemental.
3. No hardcoded paths/secrets; use config/env injection.
4. Enforce A-share rules (T+1, limit-up/down, trading sessions).
5. Every spiral must close with command, test, artifact, review, and sync.

## Architecture (implementation baseline)

- Data Layer
- Signal Layer (MSS / IRS / PAS)
- Validation Layer (factor + weight validation gates)
- Integration Layer
- Backtest Layer (interface-first, replaceable engine)
- Trading Layer
- Analysis Layer
- GUI Layer

Primary references:

- `docs/system-overview.md`
- `docs/module-index.md`
- `docs/design/` (`core-algorithms/` + `core-infrastructure/` + `enhancements/`)
- `Governance/Capability/SPIRAL-CP-OVERVIEW.md`
- `Governance/SpiralRoadmap/draft/` (candidate drafts; the single execution baseline is `docs/design/enhancements/eq-improvement-plan-core-frozen.md`)

## Development model (Spiral)

- Default: 7 days per spiral, one primary objective per spiral.
- Scope: 1-3 capability slices per spiral.
- Terminology: use **Capability Pack (CP)**; `CP-*.md` is the formal naming.
- Closure gates are mandatory:
  - runnable command
  - automated test
  - inspectable artifact
  - synced docs/records

Workflow references:

- `Governance/steering/6A-WORKFLOW.md`
- `Governance/Capability/SPIRAL-TASK-TEMPLATE.md`

## Quick setup

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

Optional extras:

```bash
pip install -e ".[backtest]"
pip install -e ".[visualization]"
```

Basic check:

```bash
pytest -v
```

## Directory navigation

- `docs/`: system design and specifications
- `Governance/Capability/`: spiral roadmap and capability packs
- `Governance/SpiralRoadmap/`: implementation roadmap candidate drafts
- `Governance/steering/`: iron rules, principles, workflow
- `Governance/record/`: development status, tech debts, reusable assets
- `.reports/`: critique reports and review records

## Key document entries

- `docs/system-overview.md`
- `docs/module-index.md`
- `docs/naming-conventions.md`
- `Governance/steering/系统铁律.md`
- `Governance/steering/CORE-PRINCIPLES.md`

## Repository

- `origin`: `https://github.com/everything-is-simple/EmotionQuant-gpt`

## License

MIT (see the `LICENSE` file for the authoritative text).



