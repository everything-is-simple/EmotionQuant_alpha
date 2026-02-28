# S3 Requirements（6A A1/A2）

**Spiral**: S3  
**状态**: completed  
**最后更新**: 2026-02-22

## 1. A1 Align

- 主目标: 打通 S3 回测最小闭环，并显式消费 S3a 采集增强产物。
- In Scope:
  - 实现 `eq backtest --engine {engine} --start {start} --end {end}`
  - 支持多交易日回放（交易日历驱动）
  - 执行层覆盖 T+1/涨跌停最小细节（`signal_date -> execute_date`、涨停买入拒绝、跌停卖出阻断）
  - 在回测前强制校验 `fetch_progress` 完成状态与覆盖范围
  - 校验 `integrated_recommendation` 与 `validation_weight_plan` 桥接链路
  - 输出最小回测产物：`backtest_results/backtest_trade_records/ab_metric_summary`
  - 生成 `consumption.md` 记录 S3a->S3 消费结论
- Out Scope:
  - S4 纸上交易执行链路
  - S3b 收益归因三分解
  - Qlib 深度策略优化与多策略并行

## 2. A2 Architect

- CP Slice: `CP-10 + CP-06 + CP-09`（1-3 Slice）
- 跨模块契约:
  - 输入:
    - `artifacts/spiral-s3a/*/fetch_progress.json`
    - `integrated_recommendation`
    - `quality_gate_report`
    - `validation_weight_plan`
  - 输出:
    - `backtest_results.parquet`
    - `backtest_trade_records.parquet`
    - `ab_metric_summary.md`
    - `consumption.md`
    - `gate_report.md`
  - 命名/边界约束:
    - `contract_version = "nc-v1"`
    - `risk_reward_ratio >= 1.0`
    - 桥接链路：`weight_plan_id -> validation_weight_plan.plan_id`
- 失败策略:
  - S3a 未完成或覆盖窗口不足：默认 `P0` 阻断；若本地 `raw_trade_cal + raw_daily` 已覆盖窗口则降级 `WARN`（`fetch_progress_*_but_local_l1_covered`）
  - 质量门为 `FAIL`：`P0` 阻断
  - 桥接链路缺失/基线权重：`P0` 阻断

## 3. 本圈最小证据定义

- run:
  - `eq backtest --engine qlib --start {start} --end {end}`
- test:
  - `python -m pytest tests/unit/backtest/test_backtest_contract.py -q`
  - `python -m pytest tests/unit/backtest/test_validation_integration_bridge.py -q`
  - `python -m pytest tests/unit/backtest/test_backtest_reproducibility.py -q`
  - `python -m pytest tests/unit/backtest/test_backtest_t1_limit_rules.py -q`
  - `python -m pytest tests/unit/backtest/test_backtest_board_limit_thresholds.py -q`
  - `python -m pytest tests/unit/backtest/test_backtest_cost_model_contract.py -q`
  - `python -m pytest tests/unit/pipeline/test_cli_entrypoint.py::test_main_backtest_runs_with_s3a_consumption -q`
  - `python -m scripts.quality.local_quality_check --contracts --governance`
- artifact:
  - `artifacts/spiral-s3/{trade_date}/backtest_results.parquet`
  - `artifacts/spiral-s3/{trade_date}/backtest_trade_records.parquet`
  - `artifacts/spiral-s3/{trade_date}/ab_metric_summary.md`
  - `artifacts/spiral-s3/{trade_date}/consumption.md`
  - `artifacts/spiral-s3/{trade_date}/gate_report.md`
- review/final:
  - `Governance/specs/spiral-s3/review.md`
  - `Governance/specs/spiral-s3/final.md`
