# Spiral S3b Requirements

## 主目标
- 完成 A/B/C 对照与实盘-回测偏差三分解（`signal/execution/cost`）。
- 形成“收益来源结论”（信号主导或执行主导），为 S4b 参数校准提供可审计输入。

## In Scope
- 基于统一入口执行 S3b 命令：
  - `eq analysis --start {start} --end {end} --ab-benchmark`
  - `eq analysis --date {trade_date} --deviation live-backtest`
  - `eq analysis --date {trade_date} --attribution-summary`
- 消费 S3/S4 可审计产物，生成 S3b 归因证据链。
- 输出 S3b 标准产物：`ab_benchmark_report.md`、`live_backtest_deviation_report.md`、`attribution_summary.json`、`consumption.md`、`gate_report.md`、`error_manifest*.json`。

## Out Scope
- S4b 极端防御策略实现（`eq stress` 相关功能）。
- S5/S6/S7a 展示、稳定化、自动调度能力。

## 验收门禁
1. run：S3b 三条 `eq analysis` 命令可重复执行且参数可追溯。
2. test：通过
   - `pytest tests/unit/analysis/test_ab_benchmark_contract.py -q`
   - `pytest tests/unit/analysis/test_live_backtest_deviation_contract.py -q`
   - `pytest tests/unit/analysis/test_attribution_summary_contract.py -q`
3. artifact：产物落盘到 `artifacts/spiral-s3b/{trade_date}/`，且内容可复核。
4. governance：`python -m scripts.quality.local_quality_check --contracts --governance` 通过。
