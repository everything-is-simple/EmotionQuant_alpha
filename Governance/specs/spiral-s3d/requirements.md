# S3d Requirements（6A A1/A2）

**Spiral**: S3d  
**状态**: in_progress  
**最后更新**: 2026-02-21

## A1 Align

- 主目标: MSS adaptive 阈值与真实收益 probe 口径收口。
- In Scope:
  - `eq mss --date {trade_date} --threshold-mode adaptive`（已实现）
  - `eq mss-probe --start {start} --end {end} --return-series-source future_returns`（已实现）
- Out Scope:
  - Validation 生产校准（S3e 负责）。

## A2 Architect

- 关联执行卡: `Governance/SpiralRoadmap/S3D-EXECUTION-CARD.md`
- 目标测试:
  - `tests/unit/algorithms/mss/test_mss_adaptive_threshold_contract.py`（已新增并通过）
  - `tests/unit/algorithms/mss/test_mss_probe_return_series_contract.py`（已新增并通过）
