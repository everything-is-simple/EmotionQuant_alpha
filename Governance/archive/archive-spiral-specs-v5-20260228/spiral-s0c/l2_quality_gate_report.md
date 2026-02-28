# L2 Quality Gate Report

- trade_date: 20260215
- status: ready
- is_ready: true
- coverage_ratio: 1.0000
- max_stale_days: 0
- cross_day_consistent: true

## Issues
- none

## Warnings
- none

## Checks
- l2_market_snapshot_count: status=PASS expected=>0 actual=1 action=continue
- l2_industry_snapshot_count: status=PASS expected=>0 actual=31 action=continue
- l2_sw31_strict_gate: status=PASS expected=industry_count=31 & no_ALL actual=industry_count=31, uses_sw31=true action=continue
- l2_readiness_gate: status=PASS expected=ready/degraded actual=ready action=continue
