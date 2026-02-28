# S3c Requirements（6A A1/A2）

**Spiral**: S3c  
**状态**: completed  
**最后更新**: 2026-02-22

## A1 Align

- 主目标: 完成 SW31 行业语义校准与 IRS 全覆盖门禁。
- In Scope:
  - `eq run --date {trade_date} --to-l2 --strict-sw31`
  - `eq irs --date {trade_date} --require-sw31`
  - 固化 `industry_snapshot=31` 且无 `ALL`。
- Out Scope:
  - MSS adaptive 与 Validation 生产口径（S3d/S3e 负责）。

## A2 Architect

- 关联执行卡: `Governance/SpiralRoadmap/execution-cards/S3C-EXECUTION-CARD.md`
- 目标测试:
  - `tests/unit/data/test_industry_snapshot_sw31_contract.py`
  - `tests/unit/algorithms/irs/test_irs_sw31_coverage_contract.py`
