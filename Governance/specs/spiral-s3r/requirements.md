# S3r Requirements（6A A1/A2）

**Spiral**: S3r  
**状态**: planned  
**最后更新**: 2026-02-21

## A1 Align

- 主目标: S3 回测 FAIL 时执行“只修不扩”修复闭环。
- In Scope:
  - `eq backtest --engine {engine} --start {start} --end {end} --repair s3r`
  - 产出 `s3r_patch_note.md` 与 `s3r_delta_report.md`
- Out Scope:
  - 新增策略能力。

## A2 Architect

- 关联执行卡: `Governance/SpiralRoadmap/execution-cards/S3R-EXECUTION-CARD.md`
- 目标测试:
  - `tests/unit/backtest/test_backtest_contract.py`
  - `tests/unit/backtest/test_backtest_reproducibility.py`
