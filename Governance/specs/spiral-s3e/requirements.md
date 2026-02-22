# S3e Requirements（6A A1/A2）

**Spiral**: S3e  
**状态**: completed  
**最后更新**: 2026-02-22

## A1 Align

- 主目标: Validation 生产口径（future_returns + 双窗口 WFA）收口。
- In Scope:
  - `eq validation --trade-date {trade_date} --threshold-mode regime --wfa dual-window`（已实现）
  - `eq validation --trade-date {trade_date} --export-run-manifest`（已实现）
- Out Scope:
  - 极端防御执行（S4b 负责）。

## A2 Architect

- 关联执行卡: `Governance/SpiralRoadmap/S3E-EXECUTION-CARD.md`
- 目标测试:
  - `tests/unit/algorithms/validation/test_factor_future_returns_alignment_contract.py`（已新增并通过）
  - `tests/unit/algorithms/validation/test_weight_validation_dual_window_contract.py`（已新增并通过）
  - `tests/unit/algorithms/validation/test_validation_oos_metrics_contract.py`（已新增并通过）
