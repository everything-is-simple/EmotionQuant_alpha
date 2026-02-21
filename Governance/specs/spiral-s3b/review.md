# Spiral S3b Review

## 状态
- in_progress

## 当前进展
- 已落地 S3b 最小执行入口：`eq analysis`（A/B/C 对照、实盘-回测偏差、归因摘要）。
- 已补齐并通过 S3b 目标测试：
  - `pytest tests/unit/analysis/test_ab_benchmark_contract.py -q`
  - `pytest tests/unit/analysis/test_live_backtest_deviation_contract.py -q`
  - `pytest tests/unit/analysis/test_attribution_summary_contract.py -q`
- 已形成可复核窗口证据（20260218-20260219）：
  - `artifacts/spiral-s3b/20260219/ab_benchmark_report.md`
  - `artifacts/spiral-s3b/20260219/live_backtest_deviation_report.md`
  - `artifacts/spiral-s3b/20260219/attribution_summary.json`
  - `artifacts/spiral-s3b/20260219/consumption.md`
  - `artifacts/spiral-s3b/20260219/gate_report.md`
- 关键结论（20260219）：
  - `quality_status=WARN`、`go_nogo=GO`
  - A/B/C 结论为 `A_dominant`
  - 偏差主导项为 `signal`

## 关键风险
- 固定窗口 `20260210-20260213` 已从阻断改为可审计降级：`S3 backtest` 输出 `no_long_entry_signal_in_window`（WARN/GO），`S3b` 在无成交样本场景输出 N/A 警告（WARN/GO）。
- 20260219 归因样本量仍偏小（`attribution_small_sample_fallback`），需在下一窗口继续扩样复核。
- `recommend` 在 bridge 样例侧仍可能出现 `mss_factor_intermediate_source_missing` 误报（不影响 integrated 输出，但会使命令返回 failed）。

## 复盘点
- A/B/C 对照是否齐备且口径一致。
- `signal/execution/cost` 三分解是否完整且可追溯。
- 结论是否可直接映射为 S4b 防御参数输入。
- `consumption.md` 与 `gate_report.md` 是否给出可执行的 go/no-go 结论。
